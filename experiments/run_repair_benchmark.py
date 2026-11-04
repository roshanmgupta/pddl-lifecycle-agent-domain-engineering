"""Empirical benchmark for PDDL domain fault repair."""

import sys
import os
import csv
import time
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import list_domain_flaws, load_flaw_task
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from config.paths import create_run_directory, get_temp_dir
from graph import pddl_lifecycle_graph
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation
)
from eval.verification_pipeline import (
    calculate_llm_cost,
    extract_hmgfl_diagnostics,
    classify_behavioral_outcome,
    verify_pddl_candidate
)
from eval.report_formatter import (
    format_funnel_table,
    format_hmgfl_table,
    format_aggregate_funnel_summary,
    generate_markdown_report
)
from tools.symbolic_oracles import run_val_validator, run_fast_downward_with_plan

PURE_STRIPS_DOMAINS = [
    "barman14-bfs", "blocksworld", "depot", "driverlog02-bfs", "elevators08",
    "ferry", "floortile", "goldminer", "grid", "gripper", "logistics",
    "movie98", "mystery98", "parking11", "pegsol08", "pipesworld-notankage04-bfs",
    "rovers", "satellite", "scanalyzer08", "visitall", "zenotravel02"
]

ALL_FLAW_CATEGORIES = [
    "flaw_01_type_signature_arity",
    "flaw_02_precondition_misalignment",
    "flaw_03_action_effect_deletion",
    "flaw_04_initial_goal_deadlock",
    "flaw_05_state_reachability_regression"
]

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

    prob_id = re.search(r"\((instance-[^\)]+)\)", task.title).group(1) if (task.title and re.search(r"\((instance-[^\)]+)\)", task.title)) else "instance-1.pddl"

    print("\n" + "#" * 85, flush=True)
    print(f" EXPERIMENT TASK: [{domain_name.upper()}] -> {flaw_name} | Agent: {agent_type}", flush=True)
    print(f" • Curated Fault Category : {task.fault_category}", flush=True)
    print(f" • Target Flawed Action   : {task.gold_fault_element}", flush=True)
    print(f" • Target Test Problem    : {prob_id}", flush=True)
    print(f" • Pre-Execution Check    : Syntax Valid={init_syntax_ok} | Planner Solvable={init_solvable}", flush=True)
    print("#" * 85, flush=True)

    repaired_dom = ""
    repaired_prob = task.initial_problem_pddl
    iterations_used = 1
    prompt_tokens = 0
    completion_tokens = 0
    diag_reports = []
    error_summary = ""

    try:
        if agent_type == "ZERO_SHOT":
            res = run_zero_shot_baseline(task)
            repaired_dom = res.get("generated_domain_pddl", "")
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)

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
            skip_fault_loc = (agent_type == "ABLATION_NO_TRIAGE")
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
                "skip_fault_localization": skip_fault_loc,
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

    # Extract fault diagnostics
    hmgfl = extract_hmgfl_diagnostics(diag_reports, task.gold_fault_element)

    # Verification pipeline execution
    verif = verify_pddl_candidate(
        generated_domain_pddl=repaired_dom,
        generated_problem_pddl=repaired_prob,
        ground_truth_domain_pddl=task.ground_truth_domain_pddl,
        ground_truth_problem_pddl=task.initial_problem_pddl,
        temp_dir=temp_dir,
        tag=f"{domain_name}_{flaw_name}_{agent_type}"
    )

    # 3. Behavioral Outcome Classification (A.1 to G)
    macro_f1 = verif.get("macro_structural_f1", 1.0 if verif.get("e2e_success") else 0.0)
    beh_code, def_class = classify_behavioral_outcome(
        is_syntax_valid=verif["is_syntax_valid"],
        is_solvable=verif["is_solvable"],
        executability_valid=verif["executability_valid"],
        feasibility_valid=verif["feasibility_valid"],
        interpretability_valid=verif["interpretability_valid"],
        macro_f1=macro_f1,
        iters=iterations_used,
        max_retries=max_retries,
        planner_timed_out=verif["planner_timeout"]
    )

    prob_id = re.search(r"\((instance-[^\)]+)\)", task.title).group(1) if (task.title and re.search(r"\((instance-[^\)]+)\)", task.title)) else "instance-1.pddl"

    e2e_str = "PASS" if verif["e2e_success"] else "FAIL"
    print("\n" + "-" * 85, flush=True)
    print(f" [ORACLE VERIFICATION VERDICT]: {domain_name.upper()} | {flaw_name} -> {e2e_str} (Time: {elapsed_time}s | Iterations: {iterations_used})", flush=True)
    print(f"   Stage 1: Syntactic Validity  (VAL)          : {'PASS' if verif['is_syntax_valid'] else 'FAIL'}", flush=True)
    print(f"   Stage 2: Planner Solvability (FD)           : {'PASS' if verif['is_solvable'] else 'FAIL'} (Plan Length: {verif['plan_length']}, Cost: {verif['plan_cost']})", flush=True)
    print(f"   Stage 3a: Internal Executability (Self-VAL) : {'PASS' if verif['executability_valid'] else 'FAIL'}", flush=True)
    print(f"   Stage 3b: Forward Soundness (Feasibility)   : {'PASS' if verif['feasibility_valid'] else 'FAIL'}", flush=True)
    print(f"   Stage 3c: Inverse Completeness (Interpret.) : {'PASS' if verif['interpretability_valid'] else 'FAIL'}", flush=True)
    print(f"   Strict End-to-End Gate Success              : {e2e_str}", flush=True)
    print("-" * 85 + "\n", flush=True)

    return {
        "domain": domain_name,
        "flaw": flaw_name,
        "agent": agent_type,
        "flaw_category": task.fault_category,
        "gold_target_action": task.gold_fault_element,
        "problem_tested": prob_id,
        "init_syntax_ok": init_syntax_ok,
        "init_solvable": init_solvable,
        # Multi-stage funnel metrics
        "is_syntax_valid": verif["is_syntax_valid"],
        "is_solvable": verif["is_solvable"],
        "planner_timeout": verif["planner_timeout"],
        "executability_valid": verif["executability_valid"],
        "feasibility_valid": verif["feasibility_valid"],
        "interpretability_valid": verif["interpretability_valid"],
        "semantic_soundness": verif["semantic_soundness"],
        "e2e_success": verif["e2e_success"],
        # H-MGFL elements
        "top1_element": hmgfl["top1_element"],
        "top1_repair_op": hmgfl["top1_repair_op"],
        "parameter_arity_match": verif.get("parameter_arity_match", True),
        # Structural Conformance
        "macro_structural_f1": macro_f1,
        # Operational metrics
        "iterations_used": iterations_used,
        "plan_length": verif["plan_length"],
        "plan_cost": verif["plan_cost"],
        "search_time_sec": verif["search_time_sec"],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": cost_usd,
        "execution_time_sec": elapsed_time,
        "behavioral_code": beh_code,
        "defect_class": def_class,
        "error_summary": error_summary or verif["val_syntax_log"][:200] if not verif["is_syntax_valid"] else "",
        "generated_domain_pddl": repaired_dom,
        "generated_problem_pddl": repaired_prob,
        "plan_text": verif["plan_text"]
    }

def main():
    parser = argparse.ArgumentParser(description="Empirical Evaluation Benchmark for PDDL Domain Fault Repair (Category B).")
    parser.add_argument("--domains", type=str, default="blocksworld,gripper,depot,logistics", help="Comma-separated pure STRIPS domains, or 'all'.")
    parser.add_argument("--flaws", type=str, default="all", help="Comma-separated flaw categories, or 'all'.")
    parser.add_argument("--agents", type=str, default="CLOSED_LOOP_AST_AGENT,ZERO_SHOT,UNSTRUCTURED_RETRY,ABLATION_NO_AST,ABLATION_NO_TRIAGE", help="Comma-separated agents.")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum repair feedback iterations.")
    parser.add_argument("--tag", type=str, default="eval", help="Tag for isolated run output directory.")
    args = parser.parse_args()

    target_domains = PURE_STRIPS_DOMAINS if args.domains.strip().lower() == "all" else [d.strip() for d in args.domains.split(",") if d.strip() in PURE_STRIPS_DOMAINS]
    target_flaws = None if args.flaws.strip().lower() == "all" else [f.strip() for f in args.flaws.split(",")]
    target_agents = [a.strip() for a in args.agents.split(",") if a.strip()]

    print("=" * 85)
    print(" AUTONOMOUS EMPIRICAL BENCHMARK: PDDL DOMAIN FAULT REPAIR (H2)")
    print(f" Target Domains ({len(target_domains)}): {target_domains}")
    print(f" Flaws Evaluated: {'ALL_AVAILABLE' if target_flaws is None else target_flaws}")
    print(f" Agent Architectures ({len(target_agents)}): {target_agents}")
    print(f" Max Repair Retries: {args.max_retries} | Tag: {args.tag}")
    print("=" * 85)

    run_dir = create_run_directory(tag=f"repair_{args.tag}")
    out_csv = run_dir / "metrics.csv"
    verification_csv = run_dir / "detailed_verification.csv"
    report_md = run_dir / "report.md"

    metric_fields = [
        "domain", "flaw", "agent", "flaw_category", "gold_target_action", "problem_tested",
        "init_syntax_ok", "init_solvable",
        "is_syntax_valid", "is_solvable", "planner_timeout",
        "executability_valid", "feasibility_valid", "interpretability_valid", "semantic_soundness", "e2e_success",
        "top1_element", "top1_repair_op",
        "parameter_arity_match", "macro_structural_f1",
        "iterations_used", "plan_length", "plan_cost", "search_time_sec",
        "prompt_tokens", "completion_tokens", "total_tokens", "estimated_cost_usd", "execution_time_sec",
        "behavioral_code", "defect_class", "error_summary"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=metric_fields)
        writer.writeheader()

    verification_fields = [
        "domain", "flaw", "agent", "flaw_category", "gold_target_action",
        "is_syntax_valid", "is_solvable", "planner_timeout",
        "executability_valid", "feasibility_valid", "interpretability_valid", "semantic_soundness", "e2e_success",
        "top1_element", "top1_repair_op",
        "parameter_arity_match", "macro_structural_f1",
        "iterations_used", "behavioral_code"
    ]
    with open(verification_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=verification_fields)
        writer.writeheader()

    master_results = []
    start_total_t = time.time()
    interrupted = False

    try:
        for domain_name in target_domains:
            available_flaws = list_domain_flaws(domain_name)
            flaws_to_run = available_flaws if target_flaws is None else [f for f in target_flaws if f in available_flaws]

            for flaw_name in flaws_to_run:
                for agent_type in target_agents:
                    res = evaluate_single_flaw_task(
                        domain_name=domain_name,
                        flaw_name=flaw_name,
                        agent_type=agent_type,
                        max_retries=args.max_retries
                    )
                    master_results.append(res)

                    # Incremental flush to disk
                    with open(out_csv, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=metric_fields)
                        writer.writerow({k: res.get(k, "") for k in metric_fields})

                    with open(verification_csv, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=verification_fields)
                        writer.writerow({k: res.get(k, "") for k in verification_fields})

                    # Save generated artifacts
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
    except KeyboardInterrupt:
        interrupted = True
        print("\n\n" + "!" * 95)
        print(" [INTERRUPT DETECTED]: Received KeyboardInterrupt (Ctrl+C). Safely preserving results...")
        print("!" * 95)

    total_elapsed = round(time.time() - start_total_t, 2)

    # Print Clean Formatted Tables & Aggregate Funnel Summary
    print("\n" + format_funnel_table(master_results))
    summary_text = format_aggregate_funnel_summary(master_results, total_elapsed)
    print("\n" + summary_text)

    # Generate Markdown Report Artifact
    generate_markdown_report("Domain Fault Repair Evaluation Report", master_results, report_md)

    print(f"\nOutputs written to: '{run_dir.resolve()}'.")
    print(f"Markdown report generated: '{report_md.resolve()}'.")
    print("=" * 125)

    if interrupted:
        sys.exit(0)

if __name__ == "__main__":
    main()
