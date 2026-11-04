"""
scripts/run_canonical_17_domains_benchmark.py
Empirical Evaluation Runner for the 17 Canonical Domain Families across all 5 Agent Architectures.
Protocol:
  - 17 Canonical Domains (deduplicated IPC representations)
  - 5 Architectures: CLOSED_LOOP_AST_AGENT, ABLATION_NO_TRIAGE, ABLATION_NO_AST, UNSTRUCTURED_RETRY, ZERO_SHOT
  - 3 Runs per Task (with 3-run majority voting >= 2/3)
  - Max 3 Repair Iterations (k_max = 3)
  - Resume-capable incremental CSV persistence
"""

import sys
import os
import argparse
import time
import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 stdout
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
except Exception:
    pass

from benchmark.schema import BenchmarkTask, LifecycleTaskType
from benchmark.loader import load_autoplanbench_synthesis_task
from eval.metrics import EvaluationMetrics
from eval.benchmark_runner import evaluate_candidate_pddl
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation,
)
from eval.statistical_significance import aggregate_runs_per_task
from graph import pddl_lifecycle_graph

CANONICAL_17_DOMAINS = [
    "gripper",
    "depot",
    "rovers",
    "satellite",
    "elevators08",
    "parking11",
    "goldminer",
    "scanalyzer08",
    "visitall",
    "transport08-bfs",
    "floortile",
    "tpp06-bfs",
    "pegsol08",
    "nomystery11-bfs",
    "barman14-bfs",
    "pipesworld-notankage04-bfs",
    "woodworking08"
]

DOMAINS_21 = [
    "blocksworld",
    "gripper",
    "logistics",
    "depot",
    "rovers",
    "satellite",
    "elevators08",
    "parking11",
    "goldminer",
    "scanalyzer08",
    "visitall",
    "transport08-bfs",
    "floortile",
    "tpp06-bfs",
    "pegsol08",
    "nomystery11-bfs",
    "barman14-bfs",
    "pipesworld-notankage04-bfs",
    "woodworking08",
    "zenotravel02",
    "driverlog02-bfs"
]

ALL_ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_TRIAGE",
    "ABLATION_NO_AST",
    "UNSTRUCTURED_RETRY",
    "ZERO_SHOT"
]


def run_single_domain_architecture(
    task: BenchmarkTask,
    agent_type: str,
    max_retries: int = 3,
    run_idx: int = 1
) -> Tuple[EvaluationMetrics, Dict[str, Any]]:
    """Runs a single domain task on the designated architecture."""
    start_t = time.time()
    print(f"\n[{task.domain_family.upper()} | {agent_type} | Run {run_idx}] Starting synthesis...", flush=True)

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
                print(f"  [Oracle Check Iter {evt.get('iteration')}]: VAL OK={evt.get('val_ok')} | FD OK={evt.get('fd_ok')}", flush=True)

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
    parser = argparse.ArgumentParser(description="Run Canonical IPC Domains across Agents with 3 runs and max 3 iterations.")
    parser.add_argument("--all-21", action="store_true", help="Evaluate all 21 pure STRIPS + :typing IPC domains.")
    parser.add_argument("--domains", nargs="+", default=None, help="Explicit domains to evaluate.")
    parser.add_argument("--architectures", nargs="+", default=ALL_ARCHITECTURES, help="Architectures to evaluate.")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per task (default: 3).")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum repair iterations (default: 3).")
    parser.add_argument("--output-csv", type=str, default=None, help="Raw runs CSV destination.")
    parser.add_argument("--aggregated-csv", type=str, default=None, help="Aggregated CSV destination.")
    args = parser.parse_args()

    # Domain resolution
    if args.all_21 or (args.domains and "all_21" in args.domains):
        args.domains = DOMAINS_21
    elif not args.domains:
        args.domains = CANONICAL_17_DOMAINS

    # Default CSV filenames
    if not args.output_csv:
        if args.domains == DOMAINS_21:
            args.output_csv = "results/h1_21_domains_all_agents_runs.csv"
            args.aggregated_csv = args.aggregated_csv or "results/h1_21_domains_all_agents_aggregated.csv"
        else:
            args.output_csv = "results/canonical_17_domains_all_agents_runs.csv"
            args.aggregated_csv = args.aggregated_csv or "results/canonical_17_domains_all_agents_aggregated.csv"
    if not args.aggregated_csv:
        args.aggregated_csv = args.output_csv.replace(".csv", "_aggregated.csv")

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for existing completed runs to support resume
    completed_runs = set()
    rows = []
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    completed_runs.add((r.get("Domain"), r.get("Architecture"), int(r.get("Run", 1))))
                    rows.append(r)
            print(f"[*] Resuming from existing results: {len(completed_runs)} run(s) already completed.")
        except Exception as e:
            print(f"[!] Warning reading existing CSV: {e}")

    total_runs = len(args.domains) * len(args.architectures) * args.runs
    current_run_count = len(completed_runs)

    print("=" * 85)
    print("  AUTONOMOUS PDDL LIFECYCLE: 17 CANONICAL DOMAINS MULTI-AGENT BENCHMARK")
    print(f"  Domains ({len(args.domains)}): {args.domains}")
    print(f"  Architectures ({len(args.architectures)}): {args.architectures}")
    print(f"  Runs per task: {args.runs} | Max Iterations: {args.max_retries}")
    print(f"  Total planned executions: {total_runs} (Completed: {current_run_count})")
    print(f"  Raw CSV destination: {args.output_csv}")
    print("=" * 85, flush=True)

    for domain in args.domains:
        task = load_autoplanbench_synthesis_task(domain)
        if not task:
            print(f"[Warning]: Failed to load task for domain '{domain}', skipping.", flush=True)
            continue

        for arch in args.architectures:
            for r_idx in range(1, args.runs + 1):
                if (domain, arch, r_idx) in completed_runs:
                    continue

                current_run_count += 1
                print(f"\n>>> [{current_run_count}/{total_runs}] Executing {domain} | {arch} | Run {r_idx}/{args.runs}...", flush=True)

                try:
                    metrics, _ = run_single_domain_architecture(task, arch, max_retries=args.max_retries, run_idx=r_idx)
                    row = {
                        "Domain": domain,
                        "Architecture": arch,
                        "Run": r_idx,
                        "Status": "Verified [PASS]" if metrics.e2e_success else "Unverified [FAIL]",
                        "e2e_success": metrics.e2e_success,
                        "SVR": 1.0 if metrics.is_syntax_valid else 0.0,
                        "TPV": "PASS" if metrics.tpv_target_plan_valid else "FAIL",
                        "Executability": "Certified" if metrics.executability_valid else "FAIL",
                        "Feasibility": "PASS" if metrics.feasibility_valid else ("FAIL" if metrics.feasibility_valid is False else "N/A"),
                        "Interpretability": "PASS" if metrics.interpretability_valid else ("FAIL" if metrics.interpretability_valid is False else "N/A"),
                        "Plan Length": metrics.plan_length if metrics.plan_length is not None else "N/A",
                        "Iterations": metrics.iterations_used,
                        "Latency (s)": round(metrics.execution_time_seconds, 2),
                        "Total Tokens": metrics.total_tokens,
                        "Cost ($)": f"${metrics.estimated_cost_usd:.5f}",
                        "Error Summary": (metrics.error_summary or "")[:150]
                    }
                    rows.append(row)
                    completed_runs.add((domain, arch, r_idx))

                    print(f" -> Result: Status={row['Status']} | SVR={row['SVR']} | TPV={row['TPV']} | Feas={row['Feasibility']} | Interp={row['Interpretability']} | Iters={row['Iterations']} | Time={row['Latency (s)']}s", flush=True)

                    # Persist incrementally
                    with open(out_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                        writer.writeheader()
                        for r in rows:
                            writer.writerow(r)

                except Exception as e:
                    print(f"[ERROR]: Execution failed for '{domain}' with '{arch}' (Run {r_idx}): {e}", flush=True)

    print("\n" + "=" * 85)
    print("ALL 17 CANONICAL DOMAIN RUNS COMPLETED")
    print(f"Saved full raw data to '{args.output_csv}'.")
    print("=" * 85, flush=True)

    # Compute 3-run aggregated metrics per (Domain, Architecture)
    try:
        import pandas as pd
        df_raw = pd.DataFrame(rows)
        if not df_raw.empty:
            agg_rows = []
            for (dom, arch), group in df_raw.groupby(["Domain", "Architecture"]):
                n_runs = len(group)
                n_pass = group["Status"].str.contains("PASS").sum()
                majority_pass = (n_pass >= 2) if n_runs >= 3 else (n_pass >= 1)
                
                # Iterations penalty rule: failed runs count as 6 (or max_retries + 1)
                iters_list = []
                for _, r in group.iterrows():
                    if "PASS" in str(r["Status"]):
                        iters_list.append(float(r["Iterations"]))
                    else:
                        iters_list.append(float(args.max_retries + 1))
                mean_iters = sum(iters_list) / len(iters_list) if iters_list else 1.0

                numeric_svr = pd.to_numeric(group["SVR"], errors="coerce").mean()
                numeric_lat = pd.to_numeric(group["Latency (s)"], errors="coerce").mean()

                agg_rows.append({
                    "Domain": dom,
                    "Architecture": arch,
                    "Total Runs": n_runs,
                    "Passed Runs": n_pass,
                    "Majority Success": "PASS" if majority_pass else "FAIL",
                    "Mean SVR": round(numeric_svr, 2),
                    "Mean Penalized Iterations": round(mean_iters, 2),
                    "Mean Latency (s)": round(numeric_lat, 2)
                })

            df_agg = pd.DataFrame(agg_rows)
            agg_path = Path(args.aggregated_csv)
            df_agg.to_csv(agg_path, index=False)
            print(f"\nSaved aggregated metrics to '{agg_path}'.")
            print("\nAGGREGATED SUMMARY TABLE:")
            print(df_agg.to_string(index=False))
    except Exception as e:
        print(f"[!] Warning generating aggregated summary: {e}")


if __name__ == "__main__":
    main()
