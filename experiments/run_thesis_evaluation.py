"""
run_thesis_evaluation.py
Autonomous Empirical Thesis Evaluation Runner strictly implementing
the 6 Core Domains Experimental Design:

Scope:
- 6 Domains: Blocksworld, Gripper, Logistics, Depot, Rovers, Satellite.
- One LLM: OpenAI GPT-4o (configured via .env).
- 3 Runs per Task (Voting: >= 2/3 succeeds; Iterations: mean with failed = 6).
- Max 3 Repair Iterations (k_max = 3).
- H1: Formulation (Full Agent vs ABLATION_NO_AST vs ZERO_SHOT).
      Semantic correctness: Soundness (feasibility on D_gold) & Completeness (interpretability on D_gen).
      McNemar's test on binary success.
- H2: Fault Repair (Full Agent vs ABLATION_NO_TRIAGE).
      24 curated tasks across 2 mutation operators.
      McNemar's test on success and Wilcoxon signed-rank test on iterations.
- RQ4: Descriptive reporting of SVR, success rate, mean iterations, tokens, latency.
"""

import sys
import os
import csv
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import (
    load_elicitation_task,
    load_flaw_task,
    list_domain_flaws
)
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from config.paths import create_run_directory, get_temp_dir
from graph import pddl_lifecycle_graph
from eval.baselines import run_zero_shot_baseline, run_no_ast_ablation
from eval.verification_pipeline import (
    calculate_llm_cost,
    classify_behavioral_outcome,
    verify_pddl_candidate
)
from eval.statistical_significance import (
    aggregate_runs_per_task,
    compute_exact_mcnemar_test,
    compute_wilcoxon_signed_rank_test,
    format_descriptive_thesis_table
)
from tools.symbolic_oracles import run_val_validator, run_fast_downward_with_plan

CORE_6_DOMAINS = ["blocksworld", "gripper", "logistics", "depot", "rovers", "satellite"]


def evaluate_single_task_run(
    task: BenchmarkTask,
    agent_type: str,
    run_idx: int,
    max_retries: int = 3
) -> Dict[str, Any]:
    """Evaluates a single execution run of a task under the specified agent condition."""
    start_time = time.time()
    domain_name = task.domain_family
    task_id = task.task_id
    temp_dir = get_temp_dir()

    # Pre-execution oracle check
    pre_dom_file = str(temp_dir / f"pre_{task_id}_{agent_type}_{run_idx}_dom.pddl")
    pre_prob_file = str(temp_dir / f"pre_{task_id}_{agent_type}_{run_idx}_prob.pddl")
    init_dom = task.initial_domain_pddl or task.ground_truth_domain_pddl or ""
    init_prob = task.initial_problem_pddl or task.ground_truth_problem_pddl or ""
    
    with open(pre_dom_file, "w", encoding="utf-8") as f:
        f.write(init_dom)
    with open(pre_prob_file, "w", encoding="utf-8") as f:
        f.write(init_prob)

    init_syntax_ok, _ = run_val_validator(pre_dom_file, pre_prob_file)

    repaired_dom = ""
    repaired_prob = init_prob
    iterations_used = 1
    prompt_tokens = 0
    completion_tokens = 0
    error_summary = ""

    try:
        if agent_type == "ZERO_SHOT":
            res = run_zero_shot_baseline(task)
            repaired_dom = res.get("generated_domain_pddl", "")
            repaired_prob = res.get("generated_problem_pddl") or init_prob
            iterations_used = 1
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)
            if res.get("error"):
                error_summary = res["error"]

        elif agent_type == "ABLATION_NO_AST":
            res = run_no_ast_ablation(task, max_retries=max_retries)
            repaired_dom = res.get("generated_domain_pddl", "")
            repaired_prob = res.get("generated_problem_pddl") or init_prob
            iterations_used = res.get("iterations_used", max_retries)
            prompt_tokens = res.get("prompt_tokens", 0)
            completion_tokens = res.get("completion_tokens", 0)

        elif agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
            skip_fault_loc = (agent_type == "ABLATION_NO_TRIAGE")
            is_repair = (task.task_type == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR)

            init_state = {
                "requirements": task.natural_language_requirements,
                "initial_domain_pddl": task.initial_domain_pddl or "",
                "initial_problem_pddl": init_prob,
                "reference_domain_pddl": task.ground_truth_domain_pddl or "",
                "ground_truth_domain_pddl": task.ground_truth_domain_pddl or "",
                "pddl_domain_blueprint": {},
                "pddl_problem_blueprint": {},
                "generated_domain_pddl": task.initial_domain_pddl or "",
                "generated_problem_pddl": init_prob,
                "is_synthetic_repair": is_repair,
                "skip_elicitation": is_repair,
                "skip_fault_localization": skip_fault_loc,
                "system_type": agent_type,
                "verification_errors": ["Initial Oracle Check Pending"] if is_repair else [],
                "iteration_count": 0,
                "max_iterations": max_retries,
            }
            final_state = pddl_lifecycle_graph.invoke(init_state)
            repaired_dom = final_state.get("generated_domain_pddl", "")
            repaired_prob = final_state.get("generated_problem_pddl") or init_prob
            iterations_used = max(1, final_state.get("iteration_count", 1))
            prompt_tokens = final_state.get("total_prompt_tokens", 0)
            completion_tokens = final_state.get("total_completion_tokens", 0)

    except Exception as e:
        error_summary = f"Execution Crash: {str(e)}"
        print(f"[{domain_name.upper()} | {task_id} | {agent_type} | Run {run_idx}] Crash: {e}")

    elapsed_time = round(time.time() - start_time, 2)
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = calculate_llm_cost(prompt_tokens, completion_tokens)

    # Formal multi-stage verification
    verif = verify_pddl_candidate(
        generated_domain_pddl=repaired_dom,
        generated_problem_pddl=repaired_prob,
        ground_truth_domain_pddl=task.ground_truth_domain_pddl,
        ground_truth_problem_pddl=task.ground_truth_problem_pddl or init_prob,
        temp_dir=temp_dir,
        tag=f"{task_id}_{agent_type}_r{run_idx}"
    )

    # Bidirectional Semantic Correctness Gate:
    # Soundness: plan found with generated domain is valid on ground truth domain (feasibility_valid)
    # Completeness: plan found with ground truth domain is valid on generated domain (interpretability_valid)
    is_sound = bool(verif.get("feasibility_valid"))
    is_complete = bool(verif.get("interpretability_valid"))
    is_syntax = bool(verif.get("is_syntax_valid"))
    is_solvable = bool(verif.get("is_solvable"))
    
    # Task succeeds if both Soundness and Completeness hold
    semantic_success = is_syntax and is_solvable and is_sound and is_complete

    beh_code, def_class = classify_behavioral_outcome(
        is_syntax_valid=is_syntax,
        is_solvable=is_solvable,
        executability_valid=verif.get("executability_valid", False),
        feasibility_valid=is_sound,
        interpretability_valid=is_complete,
        macro_f1=verif.get("macro_structural_f1", 0.0),
        iters=iterations_used,
        max_retries=max_retries,
        planner_timed_out=verif.get("planner_timeout", False)
    )

    print(
        f"[{domain_name.upper()} | {task_id} | {agent_type} | Run {run_idx}] DONE ({elapsed_time}s) | "
        f"Syntax: {is_syntax} | Solv: {is_solvable} | Sound: {is_sound} | Comp: {is_complete} | "
        f"SUCCESS: {semantic_success} | Iters: {iterations_used}",
        flush=True
    )

    return {
        "task_id": task_id,
        "domain": domain_name,
        "task_type": task.task_type.value,
        "agent": agent_type,
        "run_idx": run_idx,
        "init_syntax_ok": init_syntax_ok,
        "is_syntax_valid": is_syntax,
        "is_solvable": is_solvable,
        "soundness_valid": is_sound,
        "completeness_valid": is_complete,
        "e2e_success": semantic_success,
        "iterations_used": iterations_used,
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
        "plan_text": verif.get("plan_text", "")
    }


def run_h1_formulation_benchmark(domains: List[str], num_runs: int = 3, max_retries: int = 3) -> Dict[str, Any]:
    """Executes H1 Formulation benchmark across the 3 conditions: Full Agent, ABLATION_NO_AST, ZERO_SHOT."""
    print("\n" + "=" * 90)
    print(" EXPERIMENT 1: HYPOTHESIS H1 (FORMULATION / SYNTHESIS BENCHMARK)")
    print(f" Target Domains ({len(domains)}): {domains}")
    print(f" Runs per Task: {num_runs} | Max Retries: {max_retries}")
    print(" Conditions: CLOSED_LOOP_AST_AGENT, ABLATION_NO_AST, ZERO_SHOT")
    print(" Success Gate: Bidirectional Semantic Correctness (Soundness & Completeness)")
    print("=" * 90)

    conditions = ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_AST", "ZERO_SHOT"]
    raw_results: Dict[str, List[Dict[str, Any]]] = {c: [] for c in conditions}

    for dom in domains:
        task = load_elicitation_task(dom)
        if not task:
            print(f"[H1 ERROR]: Could not load elicitation task for domain '{dom}'.")
            continue

        for agent in conditions:
            for r_idx in range(1, num_runs + 1):
                rec = evaluate_single_task_run(task, agent, run_idx=r_idx, max_retries=max_retries)
                raw_results[agent].append(rec)

    # 3-Run Aggregation
    aggregated_by_condition: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for agent in conditions:
        aggregated_by_condition[agent] = aggregate_runs_per_task(raw_results[agent])

    # McNemar tests
    task_keys = sorted(list(aggregated_by_condition["CLOSED_LOOP_AST_AGENT"].keys()))
    full_successes = [aggregated_by_condition["CLOSED_LOOP_AST_AGENT"][k]["task_succeeds"] for k in task_keys]
    no_ast_successes = [aggregated_by_condition["ABLATION_NO_AST"][k]["task_succeeds"] for k in task_keys]
    zero_shot_successes = [aggregated_by_condition["ZERO_SHOT"][k]["task_succeeds"] for k in task_keys]

    mcnemar_no_ast = compute_exact_mcnemar_test(full_successes, no_ast_successes)
    mcnemar_zero_shot = compute_exact_mcnemar_test(full_successes, zero_shot_successes)

    return {
        "raw_results": raw_results,
        "aggregated": aggregated_by_condition,
        "mcnemar_vs_no_ast": mcnemar_no_ast,
        "mcnemar_vs_zero_shot": mcnemar_zero_shot
    }


def run_h2_repair_benchmark(domains: List[str], num_runs: int = 3, max_retries: int = 3) -> Dict[str, Any]:
    """Executes H2 Fault Repair benchmark across 2 conditions: Full Agent vs ABLATION_NO_TRIAGE."""
    print("\n" + "=" * 90)
    print(" EXPERIMENT 2: HYPOTHESIS H2 (FAULT REPAIR BENCHMARK)")
    print(f" Target Domains ({len(domains)}): {domains}")
    print(f" Runs per Task: {num_runs} | Max Retries: {max_retries}")
    print(" Conditions: CLOSED_LOOP_AST_AGENT, ABLATION_NO_TRIAGE")
    print(" Dataset: 24 Curated Tasks across 2 Classical Mutation Operators")
    print("=" * 90)

    conditions = ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]
    raw_results: Dict[str, List[Dict[str, Any]]] = {c: [] for c in conditions}

    for dom in domains:
        flaws = list_domain_flaws(dom)
        for flaw_name in flaws:
            task = load_flaw_task(dom, flaw_name)
            if not task:
                continue

            for agent in conditions:
                for r_idx in range(1, num_runs + 1):
                    rec = evaluate_single_task_run(task, agent, run_idx=r_idx, max_retries=max_retries)
                    raw_results[agent].append(rec)

    # 3-Run Aggregation
    aggregated_by_condition: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for agent in conditions:
        aggregated_by_condition[agent] = aggregate_runs_per_task(raw_results[agent])

    # Statistical tests: McNemar (success) and Wilcoxon (iterations)
    task_keys = sorted(list(aggregated_by_condition["CLOSED_LOOP_AST_AGENT"].keys()))
    full_successes = [aggregated_by_condition["CLOSED_LOOP_AST_AGENT"][k]["task_succeeds"] for k in task_keys]
    no_triage_successes = [aggregated_by_condition["ABLATION_NO_TRIAGE"][k]["task_succeeds"] for k in task_keys]

    full_iters = [aggregated_by_condition["CLOSED_LOOP_AST_AGENT"][k]["mean_iterations_penalized"] for k in task_keys]
    no_triage_iters = [aggregated_by_condition["ABLATION_NO_TRIAGE"][k]["mean_iterations_penalized"] for k in task_keys]

    mcnemar_res = compute_exact_mcnemar_test(full_successes, no_triage_successes)
    wilcoxon_res = compute_wilcoxon_signed_rank_test(full_iters, no_triage_iters)

    return {
        "raw_results": raw_results,
        "aggregated": aggregated_by_condition,
        "mcnemar_vs_no_triage": mcnemar_res,
        "wilcoxon_iterations": wilcoxon_res
    }


def main():
    parser = argparse.ArgumentParser(description="Empirical Thesis Evaluation Runner across 6 Core Domains.")
    parser.add_argument("--hypothesis", type=str, default="all", choices=["h1", "h2", "all"], help="Which hypothesis benchmark to run.")
    parser.add_argument("--domains", type=str, default="all", help="Comma-separated domains or 'all' for the 6 core domains.")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per task (default: 3).")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum repair iterations (default: 3).")
    parser.add_argument("--tag", type=str, default="thesis_final", help="Tag for output folder.")
    args = parser.parse_args()

    target_domains = CORE_6_DOMAINS if args.domains.strip().lower() == "all" else [d.strip() for d in args.domains.split(",") if d.strip()]

    run_dir = create_run_directory(tag=f"eval_{args.tag}")
    out_all_csv = run_dir / "metrics_all_runs.csv"
    out_agg_csv = run_dir / "aggregated_tasks.csv"
    report_md_file = run_dir / "thesis_report.md"

    from config.model_config import get_phase_model
    active_model = get_phase_model(1)
    print("=" * 95)
    print(" MASTER'S THESIS EMPIRICAL EVALUATION SUITE")
    print(f" LLM Configured: {active_model} (via .env)")
    print(f" Target Domains: {target_domains}")
    print(f" Runs per Task: {args.runs} | Max Repair Retries: {args.max_retries}")
    print(f" Output Directory: {run_dir.resolve()}")
    print("=" * 95)

    all_raw_records = []
    h1_output = None
    h2_output = None

    if args.hypothesis in ["h1", "all"]:
        h1_output = run_h1_formulation_benchmark(target_domains, num_runs=args.runs, max_retries=args.max_retries)
        for agent_records in h1_output["raw_results"].values():
            all_raw_records.extend(agent_records)

    if args.hypothesis in ["h2", "all"]:
        h2_output = run_h2_repair_benchmark(target_domains, num_runs=args.runs, max_retries=args.max_retries)
        for agent_records in h2_output["raw_results"].values():
            all_raw_records.extend(agent_records)

    # Save metrics_all_runs.csv
    fieldnames = [
        "task_id", "domain", "task_type", "agent", "run_idx",
        "init_syntax_ok", "is_syntax_valid", "is_solvable",
        "soundness_valid", "completeness_valid", "e2e_success",
        "iterations_used", "prompt_tokens", "completion_tokens", "total_tokens",
        "estimated_cost_usd", "execution_time_sec", "behavioral_code", "defect_class", "error_summary"
    ]
    with open(out_all_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_raw_records:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    # Save aggregated_tasks.csv
    agg_fields = [
        "task_id", "domain", "agent", "runs_evaluated", "runs_succeeded",
        "task_succeeds", "mean_iterations_penalized", "svr_rate",
        "mean_prompt_tokens", "mean_completion_tokens", "mean_total_tokens", "mean_latency_sec"
    ]
    with open(out_agg_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fields)
        writer.writeheader()
        if h1_output:
            for cond_dict in h1_output["aggregated"].values():
                for t in cond_dict.values():
                    writer.writerow({k: t.get(k, "") for k in agg_fields})
        if h2_output:
            for cond_dict in h2_output["aggregated"].values():
                for t in cond_dict.values():
                    writer.writerow({k: t.get(k, "") for k in agg_fields})

    # Generate Markdown Thesis Report
    md_lines = [
        "# Empirical Thesis Evaluation Report (Reduced Experimental Design)",
        f"\n**Model**: {active_model} | **Runs per Task**: {args.runs} | **Max Retries**: {args.max_retries}\n"
    ]

    if h1_output:
        md_lines.append("## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)")
        md_lines.append("```")
        md_lines.append(format_descriptive_thesis_table(h1_output["aggregated"]))
        md_lines.append("```\n")
        md_lines.append("### Statistical Significance Tests (H1):")
        md_lines.append(f"- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = {h1_output['mcnemar_vs_no_ast']['statistic_chi2']}, p-value = {h1_output['mcnemar_vs_no_ast']['p_value']} (Discordant: {h1_output['mcnemar_vs_no_ast']['a_only']} vs {h1_output['mcnemar_vs_no_ast']['b_only']})")
        md_lines.append(f"- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = {h1_output['mcnemar_vs_zero_shot']['statistic_chi2']}, p-value = {h1_output['mcnemar_vs_zero_shot']['p_value']} (Discordant: {h1_output['mcnemar_vs_zero_shot']['a_only']} vs {h1_output['mcnemar_vs_zero_shot']['b_only']})\n")

    if h2_output:
        md_lines.append("## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)")
        md_lines.append("```")
        md_lines.append(format_descriptive_thesis_table(h2_output["aggregated"]))
        md_lines.append("```\n")
        md_lines.append("### Statistical Significance Tests (H2):")
        md_lines.append(f"- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = {h2_output['mcnemar_vs_triage']['statistic_chi2'] if 'mcnemar_vs_triage' in h2_output else h2_output['mcnemar_vs_no_triage']['statistic_chi2']}, p-value = {h2_output.get('mcnemar_vs_no_triage', {}).get('p_value')}")
        md_lines.append(f"- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = {h2_output['wilcoxon_iterations']['w_statistic']}, z = {h2_output['wilcoxon_iterations']['z_statistic']}, p-value = {h2_output['wilcoxon_iterations']['p_value']}\n")

    report_text = "\n".join(md_lines)
    with open(report_md_file, "w", encoding="utf-8") as rf:
        rf.write(report_text)

    print("\n" + report_text)
    print(f"\nOutputs written to: '{run_dir.resolve()}'.")
    print("=" * 95)


if __name__ == "__main__":
    main()
