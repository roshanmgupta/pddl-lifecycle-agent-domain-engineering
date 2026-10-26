"""
run_repair_benchmark.py
Empirical Evaluation Benchmark for PDDL Domain Fault Repair (Category B Flaws).

Evaluates agent architectures across the 5 canonical synthetic fault categories:
1. Type Signature / Arity Inversion
2. Precondition Misalignment
3. Action Effect Deletion
4. Initial / Goal Deadlocks
5. State Reachability / Backward-Compatibility Regressions

Features:
- Evaluates 21 pure PDDL 2.1 (:strips :typing) benchmark domains.
- Automatically pairs flaws with causally activating problem instances.
- Comprehensive formal metrics: SVR, TPV, VAL Self-Certification, Semantic Soundness Transfer,
  Kuhn-Munkres Macro Structural F1, STRIPS Pre/Add/Del Component F1, Fault Localization Accuracy (FLA),
  Feedback Iterations (k), Behavioral Outcome Codes (A.1 to G), Latency, and Cost.
- Isolated per-run directory architecture: saves metrics.csv, audit.csv, report.md,
  and repaired domain/problem/plan artifacts into results/runs/repair_<tag>_<timestamp>/.
"""

import sys
import os
import csv
import time
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import (
    list_domain_flaws,
    load_flaw_task
)
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from config.paths import create_run_directory, get_temp_dir
from eval.action_reconstruction import evaluate_action_reconstruction
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness
)
from graph import pddl_lifecycle_graph
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation
)

PRICE_PROMPT_PER_M = 0.15
PRICE_COMPLETION_PER_M = 0.60

PURE_STRIPS_DOMAINS = [
    "barman14-bfs",
    "blocksworld",
    "depot",
    "driverlog02-bfs",
    "elevators08",
    "ferry",
    "floortile",
    "goldminer",
    "grid",
    "gripper",
    "logistics",
    "movie98",
    "mystery98",
    "parking11",
    "pegsol08",
    "pipesworld-notankage04-bfs",
    "rovers",
    "satellite",
    "scanalyzer08",
    "visitall",
    "zenotravel02"
]

ALL_FLAW_CATEGORIES = [
    "flaw_01_type_signature_arity",
    "flaw_02_precondition_misalignment",
    "flaw_03_action_effect_deletion",
    "flaw_04_initial_goal_deadlock",
    "flaw_05_state_reachability_regression"
]

def calculate_llm_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        (prompt_tokens * PRICE_PROMPT_PER_M / 1_000_000) +
        (completion_tokens * PRICE_COMPLETION_PER_M / 1_000_000), 
        6
    )

def classify_behavioral_outcome(
    is_syntax_valid: bool,
    is_plan_valid: bool,
    val_plan_valid: bool,
    semantic_soundness_valid: bool,
    macro_f1: float,
    iters: int,
    max_iters: int
) -> Tuple[str, str]:
    is_sound = (semantic_soundness_valid is True) or (macro_f1 >= 0.85)
    e2e_ok = is_syntax_valid and is_plan_valid and val_plan_valid and is_sound

    if e2e_ok:
        if iters == 1:
            return "A.1: First-Attempt Direct Success", "NONE"
        else:
            return "A.2: Refined Success via Feedback Loops", "RECOVERED"

    if not is_syntax_valid:
        return "B: Unparseable PDDL Syntax Failure", "SYNTAX_PARSE_ERROR"

    if is_syntax_valid and not is_plan_valid:
        return "C: Syntactically Valid but Planner Deadlock (Unsolvable)", "CAUSAL_REACHABILITY_DEADLOCK"

    if is_plan_valid and not val_plan_valid:
        return "D: Plan Generated but Fails VAL Self-Certification", "ACTION_EFFECT_CONTRADICTION"

    if not is_sound:
        return "E: Plan Execution Rejection on Standard Domain", "PRECONDITION_MISALIGNMENT"

    if iters >= max_iters:
        return "F: Iteration Budget Exhausted (Oscillation)", "UNRESOLVED_CONTRADICTION"

    return "G: Diagnostic Anomaly", "OTHER"

def evaluate_single_flaw_task(
    domain_name: str,
    flaw_name: str,
    agent_type: str,
    max_retries: int = 5
) -> Dict[str, Any]:
    task = load_flaw_task(domain_name, flaw_name)
    if not task:
        print(f"[{domain_name.upper()} | {flaw_name}] ERROR: Flaw task not found.")
        return {"domain": domain_name, "flaw": flaw_name, "error": "Task not found", "e2e_success": False}

    print(f"[{domain_name.upper()} | {flaw_name} | {agent_type}] Starting Fault Repair...", flush=True)
    start_time = time.time()

    # Pre-execution oracle check on the flawed domain
    temp_dir = get_temp_dir()
    pre_dom_file = str(temp_dir / f"pre_{domain_name}_{flaw_name}_dom.pddl")
    pre_prob_file = str(temp_dir / f"pre_{domain_name}_{flaw_name}_prob.pddl")
    with open(pre_dom_file, "w", encoding="utf-8") as f:
        f.write(task.initial_domain_pddl)
    with open(pre_prob_file, "w", encoding="utf-8") as f:
        f.write(task.initial_problem_pddl)

    init_syntax_ok, _ = run_val_validator(pre_dom_file, pre_prob_file)
    init_plan_res = run_fast_downward_with_plan(pre_dom_file, pre_prob_file) if init_syntax_ok else {}
    init_solvable = init_plan_res.get("is_solvable", False)

    repaired_dom = ""
    repaired_prob = task.initial_problem_pddl
    iterations_used = 1
    prompt_tokens = 0
    completion_tokens = 0
    diag_reports = []
    fla_correct = False
    error_summary = ""

    try:
        if agent_type == "ZERO_SHOT":
            res = run_zero_shot_baseline(task)
            repaired_dom = res.get("generated_domain_pddl", "")
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)
            iterations_used = 1

        elif agent_type == "UNSTRUCTURED_RETRY":
            res = run_unstructured_retry_baseline(task, max_retries=max_retries)
            repaired_dom = res.get("generated_domain_pddl", "")
            iterations_used = res.get("iterations_used", 1)
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)

        elif agent_type == "ABLATION_NO_AST":
            res = run_no_ast_ablation(task, max_retries=max_retries)
            repaired_dom = res.get("generated_domain_pddl", "")
            iterations_used = res.get("iterations_used", 1)
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)
            diag_reports = res.get("diagnostic_reports", [])

        elif agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
            skip_triage = (agent_type == "ABLATION_NO_TRIAGE")
            init_state = {
                "requirements": task.natural_language_requirements,
                "initial_domain_pddl": task.initial_domain_pddl,
                "initial_problem_pddl": task.initial_problem_pddl,
                "reference_domain_pddl": task.ground_truth_domain_pddl,
                "pddl_domain_blueprint": {},
                "pddl_problem_blueprint": {},
                "generated_domain_pddl": task.initial_domain_pddl,
                "generated_problem_pddl": task.initial_problem_pddl,
                "is_synthetic_repair": True,
                "skip_elicitation": True,
                "skip_triage": skip_triage,
                "system_type": agent_type,
                "verification_errors": ["Initial Oracle Check Pending"],
                "iteration_count": 0,
                "max_iterations": max_retries,
            }
            final_state = pddl_lifecycle_graph.invoke(init_state)
            repaired_dom = final_state.get("generated_domain_pddl", "")
            repaired_prob = final_state.get("generated_problem_pddl") or task.initial_problem_pddl
            iterations_used = max(1, final_state.get("iteration_count", 1))
            prompt_tokens = final_state.get("total_prompt_tokens", 0)
            completion_tokens = final_state.get("total_completion_tokens", 0)
            diag_reports = final_state.get("historical_diagnostic_reports", []) or final_state.get("diagnostic_reports", [])

    except Exception as e:
        error_summary = f"Execution Crash: {str(e)}"
        print(f"[{domain_name.upper()} | {flaw_name}] Crash: {e}")

    elapsed_time = round(time.time() - start_time, 2)
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = calculate_llm_cost(prompt_tokens, completion_tokens)

    # Check Fault Localization Accuracy (FLA) against gold target action
    gold_target = task.gold_fault_element
    if gold_target and diag_reports:
        g_clean = gold_target.lower().replace("-", "").replace("_", "")
        for r in diag_reports:
            elem = getattr(r, "faulty_element", "") if hasattr(r, "faulty_element") else str(r.get("faulty_element", ""))
            e_clean = re.sub(r"^(domain\.)?actions?\.", "", str(elem).strip("'\"` "), flags=re.IGNORECASE).lower().replace("-", "").replace("_", "")
            if e_clean and (g_clean == e_clean or g_clean in e_clean or e_clean in g_clean):
                fla_correct = True
                break

    # Save repaired PDDL to temporary files for symbolic oracle certification
    eval_dom_file = str(temp_dir / f"eval_{domain_name}_{flaw_name}_{agent_type}_dom.pddl")
    eval_prob_file = str(temp_dir / f"eval_{domain_name}_{flaw_name}_{agent_type}_prob.pddl")
    eval_plan_file = str(temp_dir / f"eval_{domain_name}_{flaw_name}_{agent_type}_plan.txt")
    ref_dom_file = str(temp_dir / f"ref_{domain_name}_{flaw_name}_dom.pddl")

    with open(eval_dom_file, "w", encoding="utf-8") as f:
        f.write(repaired_dom)
    with open(eval_prob_file, "w", encoding="utf-8") as f:
        f.write(repaired_prob)
    with open(ref_dom_file, "w", encoding="utf-8") as f:
        f.write(task.ground_truth_domain_pddl)

    # 1. VAL Syntax Validation (SVR)
    is_syntax_valid, val_syntax_log = run_val_validator(eval_dom_file, eval_prob_file)

    # 2. Fast Downward Plan Solvability (SR / TPV)
    plan_res = run_fast_downward_with_plan(
        eval_dom_file,
        eval_prob_file,
        ground_truth_domain_path=None,
        plan_path=eval_plan_file
    ) if is_syntax_valid else {}

    is_plan_valid = plan_res.get("is_solvable", False) or plan_res.get("plan_found", False)
    val_plan_valid = plan_res.get("val_plan_valid", False) or plan_res.get("val_valid", False)
    plan_steps = plan_res.get("plan_steps", [])
    plan_length = len(plan_steps)
    plan_cost = plan_res.get("plan_cost", 0)

    # 3. Plan Transfer Soundness (Semantic Soundness) on Gold Reference Domain
    semantic_soundness_valid = False
    if is_plan_valid and os.path.exists(eval_plan_file):
        ss_valid, ss_log = validate_plan_semantic_soundness(
            ground_truth_domain_path=ref_dom_file,
            problem_path=eval_prob_file,
            plan_path=eval_plan_file,
            generated_domain_path=eval_dom_file
        )
        semantic_soundness_valid = ss_valid

    # 4. Kuhn-Munkres Macro Structural F1 & STRIPS Component F1
    are_res = evaluate_action_reconstruction(task.ground_truth_domain_pddl, repaired_dom) if repaired_dom else {}
    macro_f1 = are_res.get("macro_structural_f1", 0.0)
    pre_f1 = are_res.get("mean_precondition_f1", 0.0)
    add_f1 = are_res.get("mean_add_effect_f1", 0.0)
    del_f1 = are_res.get("mean_delete_effect_f1", 0.0)
    act_f1 = are_res.get("action_f1", 0.0)

    # 5. Behavioral Classification
    beh_code, def_class = classify_behavioral_outcome(
        is_syntax_valid, is_plan_valid, val_plan_valid, semantic_soundness_valid, macro_f1, iterations_used, max_retries
    )
    e2e_success = is_syntax_valid and is_plan_valid and val_plan_valid and (semantic_soundness_valid or macro_f1 >= 0.85)

    print(f"[{domain_name.upper()} | {flaw_name}] DONE ({elapsed_time}s) | Syntax: {is_syntax_valid} | Solved: {is_plan_valid} | VAL: {val_plan_valid} | Transfer: {semantic_soundness_valid} | F1: {macro_f1:.2f} | FLA: {fla_correct} | Iters: {iterations_used}", flush=True)

    return {
        "domain": domain_name,
        "flaw": flaw_name,
        "agent": agent_type,
        "flaw_category": task.fault_category,
        "gold_target_action": task.gold_fault_element,
        "problem_tested": re.search(r"\((instance-[^\)]+)\)", task.title).group(1) if (task.title and re.search(r"\((instance-[^\)]+)\)", task.title)) else "instance-1.pddl",
        "init_syntax_ok": init_syntax_ok,
        "init_solvable": init_solvable,
        "e2e_success": e2e_success,
        "is_syntax_valid": is_syntax_valid,
        "is_plan_valid": is_plan_valid,
        "val_plan_valid": val_plan_valid,
        "semantic_soundness_valid": semantic_soundness_valid,
        "fla_correct": fla_correct,
        "iterations_used": iterations_used,
        "macro_structural_f1": macro_f1,
        "precondition_f1": pre_f1,
        "add_effect_f1": add_f1,
        "delete_effect_f1": del_f1,
        "action_f1": act_f1,
        "plan_length": plan_length,
        "plan_cost": plan_cost,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost_usd,
        "execution_time_sec": elapsed_time,
        "behavioral_code": beh_code,
        "defect_class": def_class,
        "error_summary": error_summary,
        "generated_domain_pddl": repaired_dom,
        "generated_problem_pddl": repaired_prob,
        "plan_text": "\n".join(plan_steps) if plan_steps else ""
    }

def main():
    parser = argparse.ArgumentParser(description="Empirical Evaluation Benchmark for PDDL Domain Fault Repair (Category B).")
    parser.add_argument("--domains", type=str, default="blocksworld,gripper,depot,logistics", help="Comma-separated pure STRIPS domains, or 'all'.")
    parser.add_argument("--flaws", type=str, default="all", help="Comma-separated flaw categories, or 'all'.")
    parser.add_argument("--agents", type=str, default="CLOSED_LOOP_AST_AGENT,ABLATION_NO_AST,ABLATION_NO_TRIAGE,UNSTRUCTURED_RETRY", help="Comma-separated agents: CLOSED_LOOP_AST_AGENT,ABLATION_NO_AST,ABLATION_NO_TRIAGE,UNSTRUCTURED_RETRY")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum repair feedback iterations.")
    parser.add_argument("--tag", type=str, default="eval", help="Tag for isolated run output directory.")
    args = parser.parse_args()

    # Resolve target domains
    if args.domains.strip().lower() == "all":
        target_domains = PURE_STRIPS_DOMAINS
    else:
        req_doms = [d.strip() for d in args.domains.split(",") if d.strip()]
        target_domains = [d for d in req_doms if d in PURE_STRIPS_DOMAINS]

    # Resolve target flaws
    if args.flaws.strip().lower() == "all":
        target_flaws = ALL_FLAW_CATEGORIES
    else:
        req_flaws = [f.strip() for f in args.flaws.split(",") if f.strip()]
        target_flaws = [f for f in req_flaws if f in ALL_FLAW_CATEGORIES]

    # Resolve target agents
    target_agents = [a.strip() for a in args.agents.split(",") if a.strip()]

    print("=" * 85)
    print(" AUTONOMOUS EMPIRICAL BENCHMARK: PDDL DOMAIN FAULT REPAIR (CATEGORY B)")
    print(f" Target Domains ({len(target_domains)}): {target_domains}")
    print(f" Flaws Evaluated ({len(target_flaws)}): {target_flaws}")
    print(f" Agent Architectures ({len(target_agents)}): {target_agents}")
    print(f" Max Repair Retries: {args.max_retries} | Tag: {args.tag}")
    print("=" * 85)

    # Create isolated per-run directory
    run_dir = create_run_directory(tag=f"repair_{args.tag}")
    out_csv = run_dir / "metrics.csv"
    audit_csv = run_dir / "audit.csv"
    report_md = run_dir / "report.md"

    metric_fields = [
        "domain", "flaw", "agent", "flaw_category", "gold_target_action", "problem_tested",
        "init_syntax_ok", "init_solvable", "e2e_success", "is_syntax_valid", "is_plan_valid",
        "val_plan_valid", "semantic_soundness_valid", "fla_correct", "iterations_used",
        "macro_structural_f1", "precondition_f1", "add_effect_f1", "delete_effect_f1", "action_f1",
        "plan_length", "plan_cost", "prompt_tokens", "completion_tokens", "total_tokens",
        "estimated_cost_usd", "execution_time_sec", "behavioral_code", "defect_class", "error_summary"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=metric_fields)
        writer.writeheader()

    audit_fields = [
        "domain", "flaw", "agent", "flaw_category", "gold_target_action", "fla_correct",
        "iterations_used", "macro_structural_f1", "precondition_f1", "add_effect_f1",
        "delete_effect_f1", "e2e_success", "behavioral_code"
    ]
    with open(audit_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=audit_fields)
        writer.writeheader()

    master_results = []
    start_total_t = time.time()

    for domain_name in target_domains:
        available_flaws = list_domain_flaws(domain_name)
        flaws_to_run = [f for f in target_flaws if f in available_flaws]

        for flaw_name in flaws_to_run:
            for agent_type in target_agents:
                res = evaluate_single_flaw_task(
                    domain_name=domain_name,
                    flaw_name=flaw_name,
                    agent_type=agent_type,
                    max_retries=args.max_retries
                )
                master_results.append(res)

                # Incremental flush to metrics.csv and audit.csv
                with open(out_csv, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=metric_fields)
                    writer.writerow({k: res.get(k, "") for k in metric_fields})

                with open(audit_csv, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=audit_fields)
                    writer.writerow({k: res.get(k, "") for k in audit_fields})

                # Save generated artifacts inside dedicated subfolder
                task_folder = run_dir / f"{domain_name}_{flaw_name}_{agent_type}"
                task_folder.mkdir(parents=True, exist_ok=True)
                if res.get("generated_domain_pddl"):
                    with open(task_folder / "domain_repaired.pddl", "w", encoding="utf-8") as df:
                        df.write(res["generated_domain_pddl"])
                if res.get("generated_problem_pddl"):
                    with open(task_folder / "problem.pddl", "w", encoding="utf-8") as pf:
                        pf.write(res["generated_problem_pddl"])
                if res.get("plan_text"):
                    with open(task_folder / "plan.txt", "w", encoding="utf-8") as plf:
                        plf.write(res["plan_text"])

    total_elapsed = round(time.time() - start_total_t, 2)

    # 3. Print Summary Table
    print("\n" + "=" * 95)
    print(" DOMAIN FAULT REPAIR BENCHMARK SUMMARY REPORT")
    print("=" * 95)
    print(f"{'DOMAIN':<14} | {'FLAW CATEGORY':<32} | {'AGENT':<22} | {'SUCCESS':<8} | {'STRUCT F1':<10} | {'FLA':<6} | {'ITERS'}")
    print("-" * 95)

    for r in master_results:
        d = r.get("domain", "")
        f = r.get("flaw_category", "")[:32]
        a = r.get("agent", "")[:22]
        s = "PASS" if r.get("e2e_success") else "FAIL"
        f1 = f"{r.get('macro_structural_f1', 0.0):.2f}"
        fla = "TRUE" if r.get("fla_correct") else "FALSE"
        it = f"{r.get('iterations_used', 1)}"
        print(f"{d:<14} | {f:<32} | {a:<22} | {s:<8} | {f1:<10} | {fla:<6} | {it}")

    print("-" * 95)
    total_tasks = len(master_results)
    success_count = sum(1 for r in master_results if r.get("e2e_success"))
    avg_f1 = sum(r.get("macro_structural_f1", 0.0) for r in master_results) / max(1, total_tasks)
    fla_count = sum(1 for r in master_results if r.get("fla_correct"))
    avg_iters = sum(r.get("iterations_used", 1) for r in master_results) / max(1, total_tasks)

    print(f"AGGREGATE SUMMARY ({total_tasks} evaluated tasks across {len(target_domains)} pure domains):")
    print(f"  - Repair Success Rate (RSR)      : {success_count}/{total_tasks} ({success_count/max(1, total_tasks)*100:.1f}%)")
    print(f"  - Fault Localization Acc. (FLA)  : {fla_count}/{total_tasks} ({fla_count/max(1, total_tasks)*100:.1f}%)")
    print(f"  - Mean Macro Structural F1       : {avg_f1:.4f}")
    print(f"  - Mean Repair Iterations (k)     : {avg_iters:.2f}")
    print(f"  - Total Elapsed Execution Time   : {total_elapsed}s")
    print(f"Outputs written to: '{run_dir.resolve()}'.")
    print("=" * 95)

if __name__ == "__main__":
    main()
