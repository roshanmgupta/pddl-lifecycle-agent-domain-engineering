"""
scripts/run_six_core_domains.py
Standalone empirical benchmark script to run the 6 core domains in one go:
  - blocksworld
  - gripper
  - logistics
  - depot
  - rovers
  - satellite

Evaluates across all canonical architectures:
  1. CLOSED_LOOP_AST_AGENT (Closed-Loop AST Agent with FaultLocalizationNode & Surgical AST Repair)
  2. ABLATION_NO_TRIAGE (Ablation: Direct Raw Truncated Oracle Error Trace + Surgical AST Repair)
  3. ABLATION_NO_AST (Ablation: Layered Model-Based Fault Localization + Direct Raw PDDL Text Repair)
  4. UNSTRUCTURED_RETRY (Baseline: Direct Raw Truncated Oracle Error Trace + Direct Raw PDDL Text Repair)
  5. ZERO_SHOT (Baseline: Single-Pass Direct LLM Prompting, No Feedback Loop)

Outputs a consolidated comparative results table and saves results to CSV and JSON.
"""

import sys
import os
import argparse
import time
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.schema import BenchmarkTask, LifecycleTaskType
from benchmark.loader import load_autoplanbench_synthesis_task, load_elicitation_task
from eval.metrics import EvaluationMetrics
from eval.benchmark_runner import evaluate_candidate_pddl
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation,
)
from graph import pddl_lifecycle_graph

SIX_CORE_DOMAINS = [
    "blocksworld",
    "gripper",
    "logistics",
    "depot",
    "rovers",
    "satellite"
]

ALL_ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_TRIAGE",
    "ABLATION_NO_AST",
    "UNSTRUCTURED_RETRY",
    "ZERO_SHOT"
]


def log_phase(phase_name: str, message: str) -> None:
    sep = "=" * 80
    print(f"\n{sep}\n[PHASE: {phase_name.upper()}] {message}\n{sep}", flush=True)


def run_single_domain_architecture(
    task: BenchmarkTask,
    agent_type: str,
    max_retries: int = 5
) -> Tuple[EvaluationMetrics, Dict[str, Any]]:
    """Runs a single domain task on the designated architecture, capturing phase-by-phase observability."""
    start_t = time.time()
    log_phase("Elicitation & Prompt", f"Domain: '{task.domain_family}' | Architecture: '{agent_type}'")
    print(f"Requirements ({len(task.natural_language_requirements)} chars): {task.natural_language_requirements[:300]}...\n")

    if agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
        initial_state = {
            "requirements": task.natural_language_requirements,
            "pddl_domain_blueprint": {},
            "initial_domain_pddl": task.initial_domain_pddl or "",
            "initial_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "reference_domain_pddl": task.ground_truth_domain_pddl or "",
            "is_evolution_task": False,
            "is_synthetic_repair": False,
            "skip_elicitation": False,
            "generated_domain_pddl": "",
            "generated_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "verification_errors": [],
            "diagnostic_reports": [],
            "formatted_diagnostic_feedback": "",
            "iteration_count": 0,
            "max_iterations": max_retries,
            "generated_plan_result": {},
            "historical_plan_results": [],
            "skip_fault_localization": (agent_type == "ABLATION_NO_TRIAGE"),
            "system_type": agent_type
        }

        final_state = pddl_lifecycle_graph.invoke(initial_state)
        exec_time = time.time() - start_t

        dom_pddl = final_state.get("generated_domain_pddl", "")
        prob_pddl = final_state.get("generated_problem_pddl", "")
        iters_used = max(1, final_state.get("iteration_count", 1))
        tot_tok = final_state.get("total_tokens", 0)
        est_cost = final_state.get("estimated_cost_usd", 0.0)
        diag_reps = final_state.get("diagnostic_reports", [])
        err_sum = " ".join(final_state.get("verification_errors", [])) if final_state.get("verification_errors") else None

        # Print phase summaries
        trace = final_state.get("oracle_trace", {})
        log_phase("Symbolic Oracles", f"VAL Syntax: {trace.get('val_ok')} | Fast Downward Solvable: {trace.get('fd_ok')}")
        if trace.get("val_log"):
            print(f"[VAL Output]: {trace['val_log'][:200]}...")
        if trace.get("fd_log"):
            print(f"[FD Output]: {trace['fd_log'][:200]}...")

        rf_log = final_state.get("repair_feedback_log", [])
        if rf_log:
            log_phase("Feedback Passed Back to AST", f"{len(rf_log)} Repair Feedback Iterations Logged")
            for entry in rf_log:
                print(f" -> Iter {entry.get('iteration')}: Source='{entry.get('feedback_source')}' | Targets={entry.get('target_actions')}")
                print(f"    Diagnostic Feedback: {str(entry.get('diagnostic_feedback'))[:180]}...")

        metrics = evaluate_candidate_pddl(
            task=task,
            agent_type=agent_type,
            generated_domain_pddl=dom_pddl,
            generated_problem_pddl=prob_pddl,
            iterations_used=iters_used,
            execution_time_seconds=exec_time,
            total_tokens=tot_tok,
            estimated_cost_usd=est_cost,
            diagnostic_reports=diag_reps,
            error_summary=err_sum
        )
        return metrics, final_state

    else:
        # Baselines
        def _cli_trace_callback(evt: Dict[str, Any]) -> None:
            phase = evt.get("phase")
            if phase == "validate":
                print(f"[Oracle Check Iter {evt.get('iteration')}]: VAL OK={evt.get('val_ok')} | FD OK={evt.get('fd_ok')}")
            elif phase == "fault_feedback_passed_to_llm":
                print(f"[Feedback Loop Passed Back Iter {evt.get('iteration')}]: Type='{evt.get('feedback_type')}' Target='{evt.get('model_target')}'")
                print(f"   Payload: {str(evt.get('feedback_payload'))[:180]}...")
            elif phase == "repair_response":
                print(f"[Repair Response Iter {evt.get('iteration')}]: Model produced {len(evt.get('output_domain', ''))} chars PDDL")

        if agent_type == "UNSTRUCTURED_RETRY":
            base_res = run_unstructured_retry_baseline(task, max_retries=max_retries, on_event=_cli_trace_callback)
        elif agent_type == "ABLATION_NO_AST":
            base_res = run_no_ast_ablation(task, max_retries=max_retries, on_event=_cli_trace_callback)
        elif agent_type == "ZERO_SHOT":
            base_res = run_zero_shot_baseline(task, on_event=_cli_trace_callback)
        else:
            raise ValueError(f"Unknown architecture: {agent_type}")

        exec_time = time.time() - start_t
        dom_pddl = base_res.get("generated_domain_pddl", "")
        prob_pddl = base_res.get("generated_problem_pddl", "")
        iters_used = base_res.get("iterations_used", 1)
        tot_tok = base_res.get("total_tokens", 0)
        est_cost = base_res.get("estimated_cost_usd", 0.0)
        diag_reps = base_res.get("diagnostic_reports", [])
        err_sum = base_res.get("error")

        metrics = evaluate_candidate_pddl(
            task=task,
            agent_type=agent_type,
            generated_domain_pddl=dom_pddl,
            generated_problem_pddl=prob_pddl,
            iterations_used=iters_used,
            execution_time_seconds=exec_time,
            total_tokens=tot_tok,
            estimated_cost_usd=est_cost,
            diagnostic_reports=diag_reps,
            error_summary=err_sum
        )
        return metrics, base_res


def main():
    parser = argparse.ArgumentParser(description="Run the 6 Core Domains across all Baselines and Ablations.")
    parser.add_argument("--domains", nargs="+", default=SIX_CORE_DOMAINS, help="Specific domains to evaluate (default: all 6 core domains).")
    parser.add_argument("--architectures", nargs="+", default=ALL_ARCHITECTURES, help="Specific architectures to evaluate (default: all 5).")
    parser.add_argument("--dataset", choices=["autoplanbench", "lifecyclebench"], default="autoplanbench", help="Dataset source (default: autoplanbench).")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum repair iterations (default: 5).")
    parser.add_argument("--output-csv", type=str, default="results/six_core_domains_results.csv", help="CSV output destination.")
    args = parser.parse_args()

    print("=" * 80)
    print("  AUTONOMOUS PDDL LIFECYCLE: 6 CORE DOMAINS BENCHMARK")
    print(f"  Domains: {args.domains}")
    print(f"  Architectures: {args.architectures}")
    print(f"  Dataset: {args.dataset} | Max Retries: {args.max_retries}")
    print("=" * 80, flush=True)

    rows = []
    total_runs = len(args.domains) * len(args.architectures)
    run_idx = 0

    for domain in args.domains:
        if args.dataset == "autoplanbench":
            task = load_autoplanbench_synthesis_task(domain)
        else:
            task = load_elicitation_task(domain)

        if not task:
            print(f"[Warning]: Failed to load task for domain '{domain}', skipping.")
            continue

        for arch in args.architectures:
            run_idx += 1
            print(f"\n>>> [{run_idx}/{total_runs}] Running {arch} on '{domain}'...")
            try:
                metrics, final_res = run_single_domain_architecture(task, arch, max_retries=args.max_retries)
                row = {
                    "Domain": domain,
                    "Architecture": arch,
                    "Status": "Verified [PASS]" if metrics.e2e_success else "Unverified [FAIL]",
                    "SVR": round(metrics.svr_syntax_valid_rate, 2),
                    "TPV": "PASS" if metrics.tpv_target_plan_valid else "FAIL",
                    "PTS (Executability)": "Certified" if metrics.executability_valid else "FAIL",
                    "Feasibility": "PASS" if metrics.feasibility_valid else ("FAIL" if metrics.feasibility_valid is False else "N/A"),
                    "Interpretability": "PASS" if metrics.interpretability_valid else ("FAIL" if metrics.interpretability_valid is False else "N/A"),
                    "Plan Length": metrics.plan_length if metrics.plan_length is not None else "N/A",
                    "Iterations": metrics.iterations_used,
                    "Latency (s)": round(metrics.execution_time_seconds, 2),
                    "Total Tokens": metrics.total_tokens,
                    "Cost ($)": f"${metrics.estimated_cost_usd:.5f}"
                }
                rows.append(row)
                print(f" -> Completed '{domain}' with {arch}: Status={row['Status']} | SVR={row['SVR']} | TPV={row['TPV']} | Feas={row['Feasibility']} | Interp={row['Interpretability']}")

                # Write incremental CSV
                out_path = Path(args.output_csv)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    for r in rows:
                        writer.writerow(r)

            except Exception as e:
                print(f" [ERROR]: Run failed for '{domain}' with '{arch}': {e}")

    # Print summary table
    print("\n" + "=" * 100)
    print("CONSOLIDATED COMPARATIVE MATRIX (6 CORE DOMAINS)")
    print("=" * 100)
    import pandas as pd
    if rows:
        df = pd.DataFrame(rows)
        print(df.to_string(index=False))
        print(f"\nSaved full results to '{args.output_csv}'.")
    else:
        print("No successful runs recorded.")


if __name__ == "__main__":
    main()


