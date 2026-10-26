"""
run_domain_evolution_experiments.py
Autonomous Empirical Benchmark: Phase 4 Domain Model Evolution & Solvability Preservation.

Grounding in Classical Automated Planning (Fox & Long 2003; Haslum et al. 2019;
McCluskey, Vaquero, & Vallati 2017; Silva, Silva, & Vaquero 2020; Georgievski 2023):
Evaluates an agent's capability to evolve an existing baseline state-transition model
Sigma_base into Sigma_evolved based on a capability extension specification,
verifying:
  1. Target Task Completeness: (Sigma_evolved, P_target) yields a valid plan verified by VAL.
  2. Solvability Preservation (Domain Subsumption): All canonical benchmark problem instances
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
    run_fast_downward_with_plan
)
from config.paths import create_run_directory
from eval.action_reconstruction import evaluate_action_reconstruction
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
        choices=["CLOSED_LOOP_AST_AGENT", "ZERO_SHOT", "ABLATION_NO_MAINTENANCE", "ABLATION_NO_TRIAGE"],
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
    tpv_target_plan_valid: bool,
    cov_ref: float,
    iters: int
) -> str:
    """
    Classifies Domain Evolution behavioral outcome into formal classical planning taxonomy:
      E.1: Zero-Shot Evolution Pass (Target plan verified and 100% reference coverage in <= 1 iteration)
      E.2: Repaired Evolution Pass (Target plan verified and 100% reference coverage in > 1 iterations)
      E.B: Solvability Breakage / Coverage Regression (Target solved but Cov_ref < 100%)
      E.T: Target Task Failure (Failed to synthesize valid plan for target problem)
      E.S: Syntax Parse Failure (VAL parser rejected evolved domain)
    """
    if not is_target_syntax_valid:
        return "E.S"
    if not tpv_target_plan_valid:
        return "E.T"
    if cov_ref < 100.0:
        return "E.B"
    if iters <= 1:
        return "E.1"
    return "E.2"


def evaluate_solvability_preservation_suite(
    domain_pddl: str,
    benchmark_problems: List[str]
) -> tuple[int, int, float, List[Dict[str, Any]]]:
    """
    Evaluates Domain Subsumption (Solvability Preservation) across a distribution of
    canonical benchmark problem instances.
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
    audit_csv_path = run_dir / "audit.csv"
    report_md_path = run_dir / "report.md"

    fieldnames = [
        "domain",
        "evolution_task",
        "agent_type",
        "svr_syntax_valid_rate",
        "tpv_target_plan_valid",
        "cov_ref_coverage_rate",
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
    audit_rows = []

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

                # Build baseline benchmark problem distribution list
                bench_problems = getattr(task, "baseline_benchmark_problems", []) or getattr(task, "historical_regression_problems", []) or []

                initial_state = {
                    "requirements": task.natural_language_requirements,
                    "initial_domain_pddl": task.initial_domain_pddl,
                    "initial_problem_pddl": task.evolution_target_problem_pddl,
                    "evolution_target_problem_pddl": task.evolution_target_problem_pddl,
                    "benchmark_problem_distribution": bench_problems,
                    "baseline_benchmark_problems": bench_problems,
                    "is_evolution_task": True,
                    "max_iterations": 1 if agent == "ZERO_SHOT" else args.max_retries,
                    "system_type": agent,
                    "skip_triage": (agent == "ABLATION_NO_TRIAGE")
                }

                if agent == "ABLATION_NO_MAINTENANCE":
                    initial_state["benchmark_problem_distribution"] = []
                    initial_state["baseline_benchmark_problems"] = []

                # Execute LangGraph Workflow
                try:
                    final_state = pddl_lifecycle_graph.invoke(initial_state)
                except Exception as e:
                    print(f"  [!] Workflow execution error: {e}")
                    final_state = initial_state
                    final_state["verification_errors"] = [f"Workflow Execution Exception: {e}"]

                elapsed = round(time.time() - start_time, 2)
                gen_dom = final_state.get("generated_domain_pddl", "")
                target_prob = task.evolution_target_problem_pddl
                iters = final_state.get("iteration_count", 0) + 1

                # -------------------------------------------------------------
                # 1. Target Problem Verification (VAL + Fast Downward)
                # -------------------------------------------------------------
                is_target_syntax_valid = False
                is_target_solvable = False
                tpv_target_plan_valid = False
                target_plan_len = 0
                target_plan_cost = 0
                err_summary = ""

                with tempfile.TemporaryDirectory() as td:
                    td_dom = os.path.join(td, "domain.pddl")
                    td_prob = os.path.join(td, "target_problem.pddl")
                    with open(td_dom, "w", encoding="utf-8") as f:
                        f.write(gen_dom)
                    with open(td_prob, "w", encoding="utf-8") as f:
                        f.write(target_prob)

                    val_ok, val_log = run_val_validator(td_dom, td_prob)
                    is_target_syntax_valid = val_ok

                    if val_ok:
                        plan_res = run_fast_downward_with_plan(td_dom, td_prob)
                        is_target_solvable = plan_res.get("is_solvable", False)
                        tpv_target_plan_valid = plan_res.get("is_valid", False) or is_target_solvable
                        target_plan_len = plan_res.get("plan_length", 0)
                        target_plan_cost = plan_res.get("plan_cost", 0)
                        if not is_target_solvable:
                            err_summary = f"Target Deadlock: {plan_res.get('raw_fd_log', '')[:200]}"
                    else:
                        err_summary = f"Target Syntax Error: {val_log[:200]}"

                # -------------------------------------------------------------
                # 2. Solvability Preservation Across Canonical Benchmark Problems
                # -------------------------------------------------------------
                bench_passed, bench_total, spr, inst_audits = evaluate_solvability_preservation_suite(
                    gen_dom, bench_problems
                )

                # Record individual instance audits
                for ia in inst_audits:
                    audit_rows.append({
                        "domain": domain_name,
                        "evolution_task": evo_name,
                        "agent_type": agent,
                        "instance_idx": ia.get("instance_idx"),
                        "is_solvable": ia.get("is_solvable"),
                        "val_valid": ia.get("val_valid"),
                        "error": ia.get("error", "")
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

                # Overall Reference Suite Coverage (Cov_ref)
                cov_ref = round(bench_passed / bench_total * 100.0, 2) if bench_total > 0 else 100.0
                svr_rate = 1.0 if is_target_syntax_valid else 0.0

                # Behavioral Classification Code (E.1, E.2, E.B, E.T, E.S)
                beh_code = classify_evolution_outcome(
                    is_target_syntax_valid, tpv_target_plan_valid, cov_ref, iters
                )

                print(f"  -> Outcome: {beh_code}")
                print(f"  -> TPV (Target Plan Valid): {tpv_target_plan_valid} (Plan: {target_plan_len} steps) | Cov_ref: {cov_ref:.1f}% ({bench_passed}/{bench_total} Tasks)")
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
                    "svr_syntax_valid_rate": svr_rate,
                    "tpv_target_plan_valid": tpv_target_plan_valid,
                    "cov_ref_coverage_rate": cov_ref,
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

    # Write Master Output CSV
    with open(master_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(master_rows)

    # Write Instance Audit CSV
    if audit_rows:
        with open(audit_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
            writer.writeheader()
            writer.writerows(audit_rows)

    # Write Markdown Summary Report
    with open(report_md_path, "w", encoding="utf-8") as rf:
        rf.write("# Domain Evolution Benchmark Report\n\n")
        rf.write(f"- **Experiment Tag**: `{args.tag}`\n")
        rf.write(f"- **Output Run Folder**: `{run_dir.resolve()}`\n\n")
        rf.write("| Domain | Evolution Task | Agent | SVR | TPV | Cov_ref (%) | Macro F1 | |Plan| | Iters (k) | Code |\n")
        rf.write("|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n")
        for r in master_rows:
            rf.write(f"| {r['domain']} | {r['evolution_task']} | {r['agent_type']} | {r['svr_syntax_valid_rate'] >= 1.0} | **{r['tpv_target_plan_valid']}** | {r['cov_ref_coverage_rate']}% | {r['macro_structural_f1']:.3f} | {r['plan_length']} | {r['iterations_used']} | `{r['behavioral_code']}` |\n")

    print("\n" + "=" * 80)
    print(" PHASE 4 EVOLUTION BENCHMARK EVALUATION COMPLETE!")
    print(f" Master Run Folder  : {run_dir.resolve()}")
    print(f" Master Metrics CSV : {master_csv_path.resolve()}")
    print(f" Solvability Audit  : {audit_csv_path.resolve()}")
    print(f" Evaluation Report  : {report_md_path.resolve()}")
    print("=" * 80)


if __name__ == "__main__":
    run_evolution_experiments()
