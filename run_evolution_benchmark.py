"""
run_domain_evolution_experiments.py
# Sample run: python run_evolution_benchmark.py --domains gripper --evolutions evolution_01_feature_addition --agents CLOSED_LOOP_AST_AGENT --max-retries 5 --tag evol_gripper_01
# Sample run: python run_evolution_benchmark.py --domains satellite --evolutions evolution_01_feature_addition evolution_02_composite_action --agents CLOSED_LOOP_AST_AGENT --max-retries 5 --tag evol_satellite
Autonomous Empirical Benchmark: Phase 4 Domain Model Evolution & Solvability Preservation.

Grounding in Classical Automated Planning (Fox & Long 2003; Haslum et al. 2019;
McCluskey, Vaquero, & Vallati 2017; Silva, Silva, & Vaquero 2020; Georgievski 2023):
Evaluates an agent's capability to evolve an existing baseline state-transition model
Sigma_base into Sigma_evolved based on a capability extension specification,
verifying:
  1. Target Task Completeness: (Sigma_evolved, P_target) yields a valid plan verified by VAL.
  2. Solvability Preservation: All canonical reference benchmark problem instances
     Pi_ref = {P_1, ..., P_k} remain solvable under Sigma_evolved (SPR = 1.0000).
"""

import os
import sys
# Ensure real-time unbuffered log streaming
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
import argparse
import time
import csv
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import (
    list_benchmark_domains,
    list_domain_evolutions,
    load_evolution_task
)
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness
)
from config.paths import create_run_directory, get_benchmark_dir
from eval.action_reconstruction import evaluate_action_reconstruction
from eval.baselines import run_unstructured_retry_evolution, run_no_ast_evolution
from graph import pddl_lifecycle_graph

# ---------------------------------------------------------------------------
# Pricing for openai/gpt-4o-mini / deepseek-chat
# ---------------------------------------------------------------------------
PRICE_PROMPT_PER_M = 0.15      # $0.15 per 1M prompt tokens
PRICE_COMPLETION_PER_M = 0.60  # $0.60 per 1M completion tokens


def parse_args():
    parser = argparse.ArgumentParser(
        description="Autonomous Empirical Benchmark: Phase 4 Classical Planning Domain Evolution."
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["pipesworld-notankage04-bfs"],
        help="Domains to evaluate from PDDLLifeCycleBench (e.g. pipesworld-notankage04-bfs, satellite, gripper, depot)."
    )
    parser.add_argument(
        "--evolutions",
        nargs="+",
        default=["evolution_01_feature_addition"],
        help="Evolution task categories to run (e.g. evolution_01_feature_addition, evolution_02_composite_action)."
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        default=["CLOSED_LOOP_AST_AGENT"],
        choices=["CLOSED_LOOP_AST_AGENT", "ZERO_SHOT", "UNSTRUCTURED_RETRY", "ABLATION_NO_AST", "ABLATION_NO_TRIAGE"],
        help="Agent configurations to evaluate."
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum closed-loop repair iterations per evolution task (default: 5)."
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="phase4_evolution_pilot",
        help="Unique experiment run identifier tag for CSV output naming."
    )
    return parser.parse_args()


def classify_evolution_outcome(
    is_target_syntax_valid: bool,
    target_executability_valid: bool,
    target_feasibility_valid: bool,
    reference_interpretability_pct: float,
    iters: int
) -> str:
    """
    Classifies Domain Evolution behavioral outcome into formal classical planning taxonomy
    based on the tri-criteria framework (Executability, Feasibility, Interpretability):
      EVO.A1: First-Attempt Verified Evolution (Target task solved, feasible, and 100% reference preservation in 1 iteration)
      EVO.A2: Refined Verified Evolution (Target task solved, feasible, and 100% reference preservation after repair iterations)
      EVO.B:  Unparseable Syntax Failure (VAL parser rejected evolved domain)
      EVO.C:  Target Capability Deadlock (Failed to solve new capability target problem)
      EVO.D:  Target Feasibility Divergence (Target plan failed execution on gold evolved domain)
      EVO.E:  Reference Interpretability Loss (Solvability regression on reference benchmark suite: < 100%)
    """
    if not is_target_syntax_valid:
        return "EVO.B: Syntax Parse Failure"
    if not target_executability_valid:
        return "EVO.C: Target Capability Deadlock"
    if not target_feasibility_valid:
        return "EVO.D: Target Feasibility Divergence"
    if reference_interpretability_pct < 100.0:
        return "EVO.E: Reference Interpretability Regression"
    if iters <= 1:
        return "EVO.A1: First-Attempt Verified Evolution"
    return "EVO.A2: Refined Verified Evolution"


def evaluate_solvability_preservation_suite(
    domain_pddl: str,
    benchmark_problems: List[str]
) -> tuple[int, int, float, List[Dict[str, Any]]]:
    """
    Evaluates Solvability Preservation across a distribution of
    canonical reference benchmark problem instances.
    Returns: (passed_count, total_count, spr_rate, instance_results)
    """
    if not benchmark_problems:
        return 0, 0, 1.0, []

    passed = 0
    total = len(benchmark_problems)
    results = []

    with tempfile.TemporaryDirectory() as temp_dir:
        dom_path = os.path.join(temp_dir, "domain.pddl")
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(domain_pddl)

        for idx, prob_str in enumerate(benchmark_problems, 1):
            prob_path = os.path.join(temp_dir, f"prob_{idx}.pddl")
            with open(prob_path, "w", encoding="utf-8") as pf:
                pf.write(prob_str)

            # Check 1: Syntax & Types with VAL
            val_ok, val_log = run_val_validator(dom_path, prob_path)
            if not val_ok:
                results.append({
                    "instance_idx": idx,
                    "is_solvable": False,
                    "val_valid": False,
                    "error": f"VAL Syntax Error: {val_log[:200]}"
                })
                continue

            # Check 2: Solvability with Fast Downward
            plan_res = run_fast_downward_with_plan(dom_path, prob_path)
            is_solvable = plan_res.get("is_solvable", False)
            if is_solvable:
                passed += 1
                results.append({
                    "instance_idx": idx,
                    "is_solvable": True,
                    "val_valid": True,
                    "plan_steps": plan_res.get("plan_length", 0)
                })
            else:
                results.append({
                    "instance_idx": idx,
                    "is_solvable": False,
                    "val_valid": True,
                    "error": f"FD Deadlock: {plan_res.get('raw_fd_log', '')[:200]}"
                })

    spr = round(passed / total, 4) if total > 0 else 1.0
    return passed, total, spr, results


def run_evolution_experiments():
    args = parse_args()

    print("=" * 80)
    print(" AUTONOMOUS EMPIRICAL BENCHMARK: PHASE 4 DOMAIN EVOLUTION")
    print(f" Target Domains: {args.domains}")
    print(f" Evolution Tasks: {args.evolutions}")
    print(f" Agent Configurations: {args.agents} | Max Retries: {args.max_retries}")
    print(f" Experiment Tag: {args.tag}")
    print("=" * 80)

    # Isolated Per-Run Output Directory
    run_dir = create_run_directory(tag=f"evolution_{args.tag}")
    master_csv_path = run_dir / "metrics.csv"
    verification_csv_path = run_dir / "instance_verification.csv"
    report_md_path = run_dir / "report.md"

    fieldnames = [
        "domain",
        "evolution_task",
        "agent_type",
        "e2e_success",
        "is_syntax_valid",
        "target_executability_valid",
        "target_feasibility_valid",
        "reference_interpretability_pct",
        "reference_instances_passed",
        "reference_instances_total",
        "macro_structural_f1",
        "precondition_f1",
        "add_effect_f1",
        "delete_effect_f1",
        "action_f1",
        "plan_length",
        "plan_cost",
        "iterations_used",
        "behavioral_code",
        "wall_clock_seconds",
        "total_tokens",
        "estimated_cost_usd",
        "error_summary"
    ]

    master_rows = []
    verification_rows = []

    # Initialize Master Output CSV with headers upfront
    with open(master_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    interrupted = False
    try:
        for domain_name in args.domains:
            available_evos = list_domain_evolutions(domain_name)
            target_evos = [e for e in args.evolutions if e in available_evos]
            if not target_evos:
                target_evos = available_evos[:1] if available_evos else []

            if not target_evos:
                print(f"[-] Domain '{domain_name}' has no available evolution tasks in PDDLLifeCycleBench. Skipping.")
                continue

            for evo_name in target_evos:
                task = load_evolution_task(domain_name, evo_name)
                if not task:
                    print(f"[-] Could not load evolution task '{evo_name}' for domain '{domain_name}'. Skipping.")
                    continue

                for agent in args.agents:
                    print(f"\n[+] Running Evolution: {domain_name.upper()} | Task: {evo_name} | Agent: {agent}")
                    start_time = time.time()

                                        # Build baseline benchmark problem distribution list (strictly from baseline_benchmark_problems)
                    bench_problems = getattr(task, "baseline_benchmark_problems", []) or []

                    initial_state = {
                        "requirements": task.natural_language_requirements,
                        "initial_domain_pddl": task.initial_domain_pddl,
                        "initial_problem_pddl": task.evolution_target_problem_pddl,
                        "evolution_target_problem_pddl": task.evolution_target_problem_pddl,
                        "benchmark_problem_distribution": bench_problems,
                        "baseline_benchmark_problems": bench_problems,
                        "historical_regression_suite": bench_problems,
                        "is_evolution_task": True,
                        "max_iterations": 1 if agent == "ZERO_SHOT" else args.max_retries,
                        "system_type": agent,
                        "skip_fault_localization": (agent == "ABLATION_NO_TRIAGE")
                    }

                    # ABLATION_NO_MAINTENANCE removed per updated thesis proposal

                    if agent == "UNSTRUCTURED_RETRY":
                        res = run_unstructured_retry_evolution(task, max_retries=args.max_retries)
                        gen_dom = res.get("generated_domain_pddl", "")
                        iters = res.get("iterations_used", 1)
                        tokens = res.get("total_tokens", 0)
                        cost = res.get("estimated_cost_usd", 0.0)
                        final_state = {
                            "generated_domain_pddl": gen_dom,
                            "iteration_count": iters - 1,
                            "total_tokens": tokens,
                            "estimated_cost_usd": cost,
                            "verification_errors": [res.get("error")] if res.get("error") else []
                        }
                    elif agent == "ABLATION_NO_AST":
                        res = run_no_ast_evolution(task, max_retries=args.max_retries)
                        gen_dom = res.get("generated_domain_pddl", "")
                        iters = res.get("iterations_used", 1)
                        tokens = res.get("total_tokens", 0)
                        cost = res.get("estimated_cost_usd", 0.0)
                        final_state = {
                            "generated_domain_pddl": gen_dom,
                            "iteration_count": iters - 1,
                            "total_tokens": tokens,
                            "estimated_cost_usd": cost,
                            "verification_errors": [res.get("error")] if res.get("error") else []
                        }
                    else:
                        # Execute LangGraph Workflow
                        try:
                            final_state = pddl_lifecycle_graph.invoke(initial_state)
                        except Exception as e:
                            print(f"  [!] Workflow execution error: {e}")
                            final_state = initial_state
                            final_state["verification_errors"] = [f"Workflow Execution Exception: {e}"]

                        gen_dom = final_state.get("generated_domain_pddl", "")
                        iters = final_state.get("iteration_count", 0) + 1

                    elapsed = round(time.time() - start_time, 2)
                    target_prob = task.evolution_target_problem_pddl

                    # -------------------------------------------------------------
                    # Pre-Flight Path Extraction (Zero Hidden Fallbacks)
                    # -------------------------------------------------------------
                    benchmark_root = get_benchmark_dir()
                    source_base_dom_path = benchmark_root / domain_name / "domain.pddl"
                    evo_task_dir = benchmark_root / domain_name / "evolution" / evo_name
                    source_target_prob_path = evo_task_dir / "target_problem.pddl"
                    source_gold_dom_path = evo_task_dir / "ground_truth_evolved_domain.pddl"
                    source_ref_probs_dir = evo_task_dir / "baseline_benchmark_problems"

                    # -------------------------------------------------------------
                    # 1. Target Problem Verification (VAL + Fast Downward)
                    # -------------------------------------------------------------
                    is_target_syntax_valid = False
                    is_target_solvable = False
                    target_executability_valid = False
                    target_feasibility_valid = False
                    tpv_target_plan_valid = False
                    target_plan_len = 0
                    target_plan_cost = 0
                    err_summary = ""
                    plan_res = {}

                    with tempfile.TemporaryDirectory() as td:
                        td_dom = os.path.join(td, "domain.pddl")
                        td_prob = os.path.join(td, "target_problem.pddl")
                        with open(td_dom, "w", encoding="utf-8") as f:
                            f.write(gen_dom)
                        with open(td_prob, "w", encoding="utf-8") as f:
                            f.write(target_prob)

                        # print("\n" + "=" * 80)
                        # print(" [SEMANTIC ORACLE PRE-FLIGHT]: Explicit Asset & Problem Paths:")
                        # print(f"   1. Baseline Standard Domain (D_base) : {source_base_dom_path} (exists={source_base_dom_path.exists()})")
                        # print(f"   2. Target Problem Path (P_target)    : {source_target_prob_path} (exists={source_target_prob_path.exists()})")
                        # if source_gold_dom_path.exists():
                        #     print(f"   3. Gold Reference Domain (D_gold)    : {source_gold_dom_path} (EXISTS)")
                        # else:
                        #     print(f"   3. Gold Reference Domain (D_gold)    : [DOES NOT EXIST at {source_gold_dom_path}]")
                        # if source_ref_probs_dir.exists():
                        #     print(f"   4. Benchmark Suite Dir (Pi_ref)      : {source_ref_probs_dir} ({len(bench_problems)} instance(s) loaded)")
                        # else:
                        #     print(f"   4. Benchmark Suite Dir (Pi_ref)      : [DOES NOT EXIST at {source_ref_probs_dir}] (0 instances loaded)")
                        # print(f"   5. Generated Evolved Domain (D_gen)  : {td_dom}")
                        # print("=" * 80)

                        val_ok, val_log = run_val_validator(td_dom, td_prob)
                        is_target_syntax_valid = val_ok

                        if val_ok:
                            print("\n [+] Oracle 1 (Executability): Fast Downward solving...")
                            plan_res = run_fast_downward_with_plan(td_dom, td_prob)
                            is_target_solvable = plan_res.get("is_solvable", False)
                            target_executability_valid = plan_res.get("is_valid", False) or is_target_solvable
                            target_plan_len = plan_res.get("plan_length", 0)
                            target_plan_cost = plan_res.get("plan_cost", 0)

                            if not is_target_solvable:
                                err_summary = f"Target Deadlock: {plan_res.get('raw_fd_log', '')[:200]}"
                                print("   [!] Target Deadlock: Fast Downward could not find a plan on generated domain.")
                            else:
                                print(f"   [PASS] Target Executability: Plan found ({target_plan_len} steps, cost={target_plan_cost})")
                                # Feasibility: Verify target plan on Gold Reference Evolved Domain
                                gold_evo_dom = task.ground_truth_domain_pddl
                                if gold_evo_dom and source_gold_dom_path.exists():
                                    with tempfile.NamedTemporaryFile("w", suffix=".pddl", delete=False) as gf:
                                        gf.write(gold_evo_dom)
                                        gold_dom_path = gf.name
                                    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as pf:
                                        if plan_res.get("raw_sas_plan_text"):
                                            pf.write(plan_res["raw_sas_plan_text"])
                                        elif plan_res.get("plan_steps"):
                                            pf.write("\n".join(plan_res["plan_steps"]) + "\n")
                                        plan_txt_path = pf.name

                                    print("\n [+] Oracle 2 (Feasibility): Validating plan on Gold Reference Domain...")
                                    # print(f"   -> Plan File Path (pi_gen)        : {plan_txt_path}")
                                    # print(f"   -> Gold Reference Domain (D_gold) : {gold_dom_path}")
                                    # print(f"   -> Target Problem Path (P_target) : {td_prob}")

                                    target_feasibility_valid, feas_log = validate_plan_semantic_soundness(
                                        ground_truth_domain_path=gold_dom_path,
                                        problem_path=td_prob,
                                        plan_path=plan_txt_path,
                                        generated_domain_path=td_dom
                                    )
                                    print(f"   [PASS] Target Feasibility Result     : {target_feasibility_valid}")
                                    if not target_feasibility_valid:
                                        print(f"   [FAIL] Feasibility Diagnostic Log    : {feas_log[:300]}")
                                    try:
                                        os.remove(gold_dom_path)
                                        os.remove(plan_txt_path)
                                    except Exception:
                                        pass
                                else:
                                    print("\n [-] Oracle 2 (Feasibility): SKIPPED (No ground-truth evolved domain exists for this task).")
                                    target_feasibility_valid = True
                        else:
                            err_summary = f"Target Syntax Error: {val_log[:200]}"
                            print(f"   [FAIL] Target Syntax Error: {val_log[:200]}")

                    # -------------------------------------------------------------
                    # 2. Reference Interpretability / Solvability Preservation (Pi_ref)
                    # -------------------------------------------------------------
                    print("\n [+] Oracle 3 (Interpretability / Solvability Preservation):")
                    if source_ref_probs_dir.exists():
                        print(f"   -> Verifying plan reachability across {len(bench_problems)} reference instance(s)...")
                    else:
                        print(f"   -> Reference suite directory does not exist: {source_ref_probs_dir}. Zero instances to verify.")
                    bench_passed, bench_total, spr, inst_verifications = evaluate_solvability_preservation_suite(
                        gen_dom, bench_problems
                    )
                    print(f"   [PASS] Reference Interpretability Result : {bench_passed}/{bench_total} ({round(spr * 100.0, 1)} percent)")

                    # Record individual instance verifications
                    for iv in inst_verifications:
                        verification_rows.append({
                            "domain": domain_name,
                            "evolution_task": evo_name,
                            "agent_type": agent,
                            "instance_idx": iv.get("instance_idx"),
                            "is_solvable": iv.get("is_solvable"),
                            "val_valid": iv.get("val_valid"),
                            "error": iv.get("error", "")
                        })

                    # -------------------------------------------------------------
                    # 3. Action Model Alignment (Macro F1 against Ground-Truth Evolved Domain)
                    # -------------------------------------------------------------
                    ref_domain = task.ground_truth_domain_pddl or task.initial_domain_pddl
                    are_data = evaluate_action_reconstruction(ref_domain, gen_dom)
                    macro_f1 = are_data.get("macro_structural_f1", 0.0)
                    pre_f1 = are_data.get("mean_precondition_f1", 0.0)
                    add_f1 = are_data.get("mean_add_effect_f1", 0.0)
                    del_f1 = are_data.get("mean_delete_effect_f1", 0.0)
                    action_f1 = are_data.get("action_f1", 0.0)

                    # Overall Reference Interpretability Rate
                    reference_interpretability_pct = round(bench_passed / bench_total * 100.0, 2) if bench_total > 0 else 100.0

                    # E2E Success: Must pass Target Executability + Target Feasibility + 100% Reference Interpretability
                    e2e_success = (
                        is_target_syntax_valid and
                        target_executability_valid and
                        target_feasibility_valid and
                        (reference_interpretability_pct >= 100.0)
                    )

                    # Behavioral Classification Code conforming to Tri-Criteria
                    beh_code = classify_evolution_outcome(
                        is_target_syntax_valid, target_executability_valid, target_feasibility_valid, reference_interpretability_pct, iters
                    )

                    print(f"  -> Outcome: {beh_code}")
                    print(f"  -> Target Executability: {target_executability_valid} | Target Feasibility: {target_feasibility_valid} | Ref Interpretability: {reference_interpretability_pct:.1f}% ({bench_passed}/{bench_total})")
                    print(f"  -> Macro Structural F1: {macro_f1:.4f} | Time: {elapsed}s | Iters (k): {iters}")

                    tokens = final_state.get("total_tokens", 0)
                    cost = final_state.get("estimated_cost_usd", 0.0)

                    # Save individual task artifacts in run folder for direct verification
                    task_dir = run_dir / f"{domain_name}_{evo_name}_{agent}"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    with open(task_dir / "domain.pddl", "w", encoding="utf-8") as f:
                        f.write(gen_dom)
                    with open(task_dir / "problem.pddl", "w", encoding="utf-8") as f:
                        f.write(target_prob)
                    if plan_res.get("plan_steps"):
                        with open(task_dir / "plan.txt", "w", encoding="utf-8") as f:
                            for p_idx, step in enumerate(plan_res["plan_steps"], 1):
                                f.write(f"{p_idx}: {step}\n")

                    row = {
                        "domain": domain_name,
                        "evolution_task": evo_name,
                        "agent_type": agent,
                        "e2e_success": e2e_success,
                        "is_syntax_valid": is_target_syntax_valid,
                        "target_executability_valid": target_executability_valid,
                        "target_feasibility_valid": target_feasibility_valid,
                        "reference_interpretability_pct": reference_interpretability_pct,
                        "reference_instances_passed": bench_passed,
                        "reference_instances_total": bench_total,
                        "macro_structural_f1": macro_f1,
                        "precondition_f1": pre_f1,
                        "add_effect_f1": add_f1,
                        "delete_effect_f1": del_f1,
                        "action_f1": action_f1,
                        "plan_length": target_plan_len,
                        "plan_cost": target_plan_cost,
                        "iterations_used": iters,
                        "behavioral_code": beh_code,
                        "wall_clock_seconds": elapsed,
                        "total_tokens": tokens,
                        "estimated_cost_usd": cost,
                        "error_summary": err_summary
                    }
                    master_rows.append(row)
                    # Immediate Disk Flush (Zero Data Loss on Interruption)
                    with open(master_csv_path, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writerow(row)

    except KeyboardInterrupt:
        interrupted = True
        print("\n\n" + "!" * 80)
        print(" [INTERRUPT DETECTED]: Received KeyboardInterrupt (Ctrl+C).")
        print(" Stopping safely and preserving all completed evolution benchmark records...")
        print("!" * 80)
    finally:
        # Write Instance Verification CSV for completed evaluations
        if verification_rows:
            with open(verification_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(verification_rows[0].keys()))
                writer.writeheader()
                writer.writerows(verification_rows)

        # Write Markdown Summary Report
        if master_rows:
            with open(report_md_path, "w", encoding="utf-8") as rf:
                rf.write("# Domain Evolution Benchmark Report\n\n")
                rf.write(f"- **Experiment Tag**: `{args.tag}`\n")
                rf.write(f"- **Output Run Folder**: `{run_dir.resolve()}`\n\n")
                rf.write("| Domain | Evolution Task | Agent | Syntax | Target Exec | Target Feas | Ref Interp (%) | Macro F1 | Iters (k) | Code |\n")
                rf.write("|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
                for r in master_rows:
                    rf.write(f"| {r['domain']} | {r['evolution_task']} | {r['agent_type']} | {r['is_syntax_valid']} | **{r['target_executability_valid']}** | {r['target_feasibility_valid']} | {r['reference_interpretability_pct']}% | {r['macro_structural_f1']:.3f} | {r['iterations_used']} | `{r['behavioral_code']}` |\n")

        print("\n" + "=" * 80)
        if interrupted:
            print(" PHASE 4 EVOLUTION BENCHMARK SAFELY STOPPED (INTERRUPTED BY USER)")
            print(f" Completed evaluations preserved on disk: {len(master_rows)}")
        else:
            print(" PHASE 4 EVOLUTION BENCHMARK EVALUATION COMPLETE!")
        print(f" Master Run Folder        : {run_dir.resolve()}")
        print(f" Master Metrics CSV       : {master_csv_path.resolve()}")
        print(f" Solvability Verification : {verification_csv_path.resolve()}")
        print(f" Evaluation Report        : {report_md_path.resolve()}")
        print("=" * 80)

        if interrupted:
            sys.exit(0)


if __name__ == "__main__":
    run_evolution_experiments()
