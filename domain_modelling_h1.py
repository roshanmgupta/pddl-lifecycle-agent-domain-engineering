"""
domain_modelling_h1.py
Empirical Evaluation Runner for Hypothesis H1 (Domain Modelling across 21 Canonical IPC Domains).

Protocol (Hypothesis H1):
  - 21 Canonical Classical Planning Domains (deduplicated IPC representations from AutoPlanBench)
  - 3 Core Architectural Conditions:
      1. CLOSED_LOOP_AST_AGENT (Full Agent: Schema-constrained AST modelling + compilation + closed-loop validation)
      2. ABLATION_NO_AST (Iterative raw PDDL text generation without AST constraints)
      3. ZERO_SHOT (Single-pass raw PDDL text generation without feedback)
  - 3 Independent Runs per Domain (R = 3) with majority voting gate (>= 2/3)
  - Max 3 Repair Iterations (k_max = 3, failure penalty P = 6)
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

PROJECT_ROOT = Path(__file__).resolve().parent
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
from benchmark.pure_strips_benchmarks import DOMAINS_21
from eval.metrics import EvaluationMetrics
from eval.benchmark_runner import evaluate_candidate_pddl
from eval.baselines import (
    run_zero_shot_baseline,
    run_no_ast_ablation,
)
from eval.statistical_significance import aggregate_runs_per_task
from graph import pddl_lifecycle_graph

# 3 Core Architectures for Hypothesis H1
ALL_ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_AST",
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

    if agent_type == "CLOSED_LOOP_AST_AGENT":
        initial_state = {
            "requirements": task.natural_language_requirements,
            "pddl_domain_representation": {},
            "initial_domain_pddl": task.initial_domain_pddl or "",
            "initial_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "reference_domain_pddl": task.ground_truth_domain_pddl or "",
            "reference_problems": list(task.ground_truth_problems or []),
            "reference_gold_plans": list(task.ground_truth_gold_plans or []),
            "reference_problem_names": list(task.ground_truth_problem_names or []),
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
            "skip_fault_localization": False,
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
                print(
                    f"  [Oracle Check Iter {evt.get('iteration')}]: VAL OK={evt.get('val_ok')} | FD OK={evt.get('fd_ok')} "
                    f"| Sound={evt.get('feasibility_valid')} | Complete={evt.get('interpretability_valid')}",
                    flush=True
                )

        if agent_type == "ABLATION_NO_AST":
            base_res = run_no_ast_ablation(task, max_retries=max_retries, on_event=_cli_trace_callback)
        elif agent_type == "ZERO_SHOT":
            base_res = run_zero_shot_baseline(task, on_event=_cli_trace_callback)
        else:
            raise ValueError(f"Unknown architecture for Hypothesis H1: {agent_type}")

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
    parser = argparse.ArgumentParser(description="Run Domain Modelling Benchmark (Hypothesis H1) across 21 Canonical Domains for 3 Core Architectures.")
    parser.add_argument("--all-21", action="store_true", help="Evaluate all 21 pure STRIPS + :typing IPC domains.")
    parser.add_argument("--domains", nargs="+", default=None, help="Explicit domains to evaluate.")
    parser.add_argument("--architectures", nargs="+", default=ALL_ARCHITECTURES, help="Architectures to evaluate (default: CLOSED_LOOP_AST_AGENT, ABLATION_NO_AST, ZERO_SHOT).")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per task (default: 3).")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum repair iterations (default: 3).")
    parser.add_argument("--output-csv", type=str, default=None, help="Raw runs CSV destination.")
    parser.add_argument("--aggregated-csv", type=str, default=None, help="Aggregated CSV destination.")
    args = parser.parse_args()

    # Domain resolution
    if not args.domains:
        args.domains = DOMAINS_21

    # Default CSV filenames
    if not args.output_csv:
        args.output_csv = "results/domain_modelling_h1_runs.csv"
    if not args.aggregated_csv:
        args.aggregated_csv = args.output_csv.replace(".csv", "_aggregated.csv")

    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gen_domains_root = (out_path.parent / "generated_domains_h1").resolve()
    gen_domains_root.mkdir(parents=True, exist_ok=True)
    saved_domain_records: List[Tuple[str, str, int, str]] = []

    # Check for existing completed runs to support resume
    completed_runs = set()
    rows = []
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    r_num = int(r.get("Run", 1))
                    completed_runs.add((r.get("Domain"), r.get("Architecture"), r_num))
                    rows.append(r)
                    if r.get("Generated Domain Path"):
                        saved_domain_records.append((r.get("Domain", ""), r.get("Architecture", ""), r_num, r["Generated Domain Path"]))
            print(f"[*] Resuming from existing results: {len(completed_runs)} run(s) already completed.")
        except Exception as e:
            print(f"[!] Warning reading existing CSV: {e}")

    total_runs = len(args.domains) * len(args.architectures) * args.runs
    current_run_count = len(completed_runs)

    print("=" * 85)
    print("  DOMAIN MODELLING BENCHMARK (HYPOTHESIS H1): 21 CANONICAL IPC DOMAINS")
    print(f"  Domains ({len(args.domains)}): {args.domains}")
    print(f"  Architectures ({len(args.architectures)}): {args.architectures}")
    print(f"  Runs per task: {args.runs} | Max Iterations: {args.max_retries} | Penalty P = {2 * args.max_retries}")
    print(f"  Total planned executions: {total_runs} (Completed: {current_run_count})")
    print(f"  Raw CSV destination: {args.output_csv}")
    print(f"  Aggregated CSV destination: {args.aggregated_csv}")
    print(f"  Generated domains dir: {gen_domains_root}")
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
                    metrics, state_or_res = run_single_domain_architecture(task, arch, max_retries=args.max_retries, run_idx=r_idx)
                    dom_pddl_str = (state_or_res or {}).get("generated_domain_pddl", "") if isinstance(state_or_res, dict) else ""
                    saved_dom_path = ""
                    if dom_pddl_str and dom_pddl_str.strip():
                        dom_folder = gen_domains_root / domain
                        dom_folder.mkdir(parents=True, exist_ok=True)
                        dom_file = dom_folder / f"{domain}_{arch}_run{r_idx}.pddl"
                        dom_file.write_text(dom_pddl_str.strip() + "\n", encoding="utf-8")
                        saved_dom_path = str(dom_file.resolve())
                        saved_domain_records.append((domain, arch, r_idx, saved_dom_path))

                    row = {
                        "Domain": domain,
                        "Architecture": arch,
                        "Run": r_idx,
                        "Status": "Verified [PASS]" if metrics.e2e_success else "Unverified [FAIL]",
                        "e2e_success": metrics.e2e_success,
                        "Problems Passed": f"{metrics.problems_passed}/{metrics.problems_evaluated}",
                        "Executability": "Certified" if metrics.executability_valid else "FAIL",
                        "Feasibility": "PASS" if metrics.feasibility_valid else ("FAIL" if metrics.feasibility_valid is False else "N/A"),
                        "Interpretability": "PASS" if metrics.interpretability_valid else ("FAIL" if metrics.interpretability_valid is False else "N/A"),
                        "Semantic Soundness": "PASS" if metrics.semantic_soundness else "FAIL",
                        "Plan Length": metrics.plan_length if metrics.plan_length is not None else "N/A",
                        "Iterations": metrics.iterations_used,
                        "Latency (s)": round(metrics.execution_time_seconds, 2),
                        "Total Tokens": metrics.total_tokens,
                        "Cost ($)": f"${metrics.estimated_cost_usd:.5f}",
                        "Generated Domain Path": saved_dom_path,
                        "Error Summary": (metrics.error_summary or "")[:150]
                    }
                    rows.append(row)
                    completed_runs.add((domain, arch, r_idx))

                    print(
                        f" -> Result: Status={row['Status']} | Problems={row['Problems Passed']} | Exec={row['Executability']} "
                        f"| Sound={row['Feasibility']} | Complete={row['Interpretability']} | Iters={row['Iterations']} | Time={row['Latency (s)']}s",
                        flush=True
                    )
                    if saved_dom_path:
                        print(f" -> Saved Domain: {saved_dom_path}", flush=True)

                    # Persist incrementally
                    all_fieldnames = list(dict.fromkeys(k for r in rows for k in r.keys()))
                    with open(out_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
                        writer.writeheader()
                        for r in rows:
                            writer.writerow(r)

                except Exception as e:
                    print(f"[ERROR]: Execution failed for '{domain}' with '{arch}' (Run {r_idx}): {e}", flush=True)

    print("\n" + "=" * 85)
    print("HYPOTHESIS H1 DOMAIN MODELLING RUNS COMPLETED")
    print(f"Saved full raw data to '{args.output_csv}'.")
    if saved_domain_records:
        print("\nSAVED GENERATED DOMAIN FILES:")
        for d_name, a_name, r_num, d_path in saved_domain_records:
            print(f"  * [{d_name} | {a_name} | Run {r_num}] -> {d_path}")
    print("=" * 85, flush=True)

    # Compute 3-run aggregated metrics per (Domain, Architecture)
    try:
        agg_rows = []
        domain_arch_pairs = []
        for r in rows:
            pair = (r.get("Domain"), r.get("Architecture"))
            if pair not in domain_arch_pairs:
                domain_arch_pairs.append(pair)

        for dom, arch in domain_arch_pairs:
            group = [r for r in rows if r.get("Domain") == dom and r.get("Architecture") == arch]
            n_runs = len(group)
            n_pass = sum(1 for r in group if "PASS" in str(r.get("Status", "")))
            majority_pass = (n_pass >= 2) if n_runs >= 3 else (n_pass >= 1)

            # Iterations penalty rule: failed runs count as 2 * max_retries (e.g. 6 when k_max = 3)
            iters_list = []
            lat_list = []
            for r in group:
                if "PASS" in str(r.get("Status", "")):
                    iters_list.append(float(r.get("Iterations", 1)))
                else:
                    iters_list.append(float(2 * args.max_retries))
                try:
                    lat_list.append(float(r.get("Latency (s)", 0.0)))
                except (ValueError, TypeError):
                    pass

            mean_iters = sum(iters_list) / len(iters_list) if iters_list else 1.0
            mean_lat = sum(lat_list) / len(lat_list) if lat_list else 0.0

            agg_rows.append({
                "Domain": dom,
                "Architecture": arch,
                "Total Runs": n_runs,
                "Passed Runs": n_pass,
                "Majority Success": "PASS" if majority_pass else "FAIL",
                "Mean Penalized Iterations": round(mean_iters, 2),
                "Mean Latency (s)": round(mean_lat, 2)
            })

        agg_path = Path(args.aggregated_csv)
        if agg_rows:
            agg_fieldnames = list(agg_rows[0].keys())
            with open(agg_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
                writer.writeheader()
                for r in agg_rows:
                    writer.writerow(r)
            print(f"\nSaved aggregated metrics to '{agg_path}'.")
            print("\nAGGREGATED SUMMARY TABLE:")
            for r in agg_rows:
                print(f"  {r['Domain']:22s} | {r['Architecture']:24s} | Runs: {r['Passed Runs']}/{r['Total Runs']} | Status: {r['Majority Success']:4s} | Mean Iters: {r['Mean Penalized Iterations']:.2f}")
    except Exception as e:
        print(f"[!] Warning generating aggregated summary: {e}")


if __name__ == "__main__":
    main()
