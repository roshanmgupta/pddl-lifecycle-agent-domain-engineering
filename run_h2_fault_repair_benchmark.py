"""
scripts/run_h2_fault_repair_benchmark.py
Empirical Evaluation of Hypothesis H2:
Compares CLOSED_LOOP_AST_AGENT (Structured Layered Triage) against
ABLATION_NO_TRIAGE (Raw Unstructured Oracle Error Traces) across the curated
flaw tasks of the 21 AutoPlanBench domains (default manifest: 2 operators x 2 mutants
x 21 domains = 84 tasks; select another manifest with --manifest).

Statistical Testing:
  1. Repair Success Rate (RSR / E2E Success): Evaluated via McNemar's exact test (binomial distribution).
  2. Repair Iterations (k): Evaluated via Wilcoxon signed-rank test (penalizing failures at max_iterations).

Features:
  - Checkpoint and resume support: saves progress after each task.
  - Zero external statistical dependencies (pure Python math).
  - Generates comprehensive CSV, saved repaired PDDL files, and summary JSON.
"""

import os
import sys
import time
import math
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import load_flaw_task
from nodes.pddl_to_ast_parser import parse_pddl_domain_to_representation
from graph import pddl_lifecycle_graph
from eval.benchmark_runner import evaluate_candidate_pddl
from eval.metrics import EvaluationMetrics

BASE_DIR = Path("autoplanbench/data")
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DOMAINS_H2_DIR = RESULTS_DIR / "generated_domains_h2"
GENERATED_DOMAINS_H2_DIR.mkdir(parents=True, exist_ok=True)
RUNS_CSV = RESULTS_DIR / "h2_evaluation_84_flaws_runs_gpt4o.csv"
SUMMARY_JSON = RESULTS_DIR / "h2_evaluation_84_flaws_summary_gpt4o.json"

# Default: 2 operators x 2 mutants (distinct action schemas) x 21 domains = 84 tasks
MANIFEST_FILE = BASE_DIR / "curated_21_domains_84_flaws_manifest.json"

ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_TRIAGE"
]

MAX_ITERATIONS = 3


def binom_test_exact(k: int, n: int, p: float = 0.5) -> float:
    """Exact two-sided binomial test (pure Python)."""
    if n == 0:
        return 1.0
    prob_k = math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    total_p = 0.0
    for i in range(n + 1):
        prob_i = math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
        if prob_i <= prob_k + 1e-12:
            total_p += prob_i
    return min(1.0, total_p)


def wilcoxon_signed_rank_pure(x: list, y: list) -> Tuple[float, float]:
    """Wilcoxon signed-rank test (pure Python with continuity correction)."""
    diffs = [xi - yi for xi, yi in zip(x, y)]
    non_zero = [d for d in diffs if d != 0]
    n = len(non_zero)
    if n == 0:
        return 0.0, 1.0

    abs_diffs = sorted([(abs(d), i, d) for i, d in enumerate(non_zero)], key=lambda item: item[0])

    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and abs_diffs[j][0] == abs_diffs[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    w_pos = sum(ranks[k] for k in range(n) if abs_diffs[k][2] > 0)
    w_neg = sum(ranks[k] for k in range(n) if abs_diffs[k][2] < 0)
    w_stat = min(w_pos, w_neg)

    mean_w = n * (n + 1) / 4.0
    var_w = n * (n + 1) * (2 * n + 1) / 24.0
    std_w = math.sqrt(var_w) if var_w > 0 else 1.0

    z = (w_stat - mean_w + 0.5) / std_w
    p_val = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    p_two_sided = min(1.0, 2.0 * p_val)
    return w_stat, p_two_sided


def load_manifest_tasks(manifest_file: Path = MANIFEST_FILE) -> List[Tuple[str, str]]:
    """Loads all verified flaw tasks from a manifest ('flaws' or 'tasks' lists per domain)."""
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_file}")
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    tasks = []
    for d in data.get("domains", []):
        dname = d["domain"]
        for f in d.get("flaws", d.get("tasks", [])):
            if f.get("verified_unsolvable", True) is False:
                continue
            tasks.append((dname, f["flaw_id"]))
    return tasks


def run_single_repair_task(
    domain_name: str,
    flaw_id: str,
    agent_type: str,
    max_iters: int = MAX_ITERATIONS
) -> Dict[str, Any]:
    """Runs a single flaw task with the specified architecture."""
    task = load_flaw_task(domain_name, flaw_id)
    if not task:
        raise ValueError(f"Failed to load flaw task for {domain_name}/{flaw_id}")

    t0 = time.time()
    representation = parse_pddl_domain_to_representation(task.initial_domain_pddl)

    initial_state = {
        "requirements": task.natural_language_requirements,
        "pddl_domain_representation": representation,
        "initial_domain_pddl": task.initial_domain_pddl,
        "initial_problem_pddl": task.initial_problem_pddl,
        "reference_domain_pddl": task.ground_truth_domain_pddl or "",
        "gold_reference_plan_file": (task.ground_truth_gold_plans[0] if task.ground_truth_gold_plans and task.ground_truth_gold_plans[0] else None),
        "reference_problems": list(task.ground_truth_problems or []),
        "reference_gold_plans": list(task.ground_truth_gold_plans or []),
        "reference_problem_names": list(task.ground_truth_problem_names or []),
        "generated_domain_pddl": task.initial_domain_pddl,
        "generated_problem_pddl": task.initial_problem_pddl,
        "is_synthetic_repair": True,
        "skip_elicitation": True,
        "verification_errors": [],
        "diagnostic_reports": [],
        "formatted_diagnostic_feedback": "",
        "iteration_count": 0,
        "max_iterations": max_iters,
        "skip_fault_localization": (agent_type == "ABLATION_NO_TRIAGE"),
        "system_type": agent_type
    }

    final_state = pddl_lifecycle_graph.invoke(initial_state)
    elapsed = time.time() - t0
    iters = final_state.get("iteration_count", 1)
    gen_dom = final_state.get("generated_domain_pddl", "")
    gen_prob = final_state.get("generated_problem_pddl", "")

    saved_dom_dir = GENERATED_DOMAINS_H2_DIR / domain_name
    saved_dom_dir.mkdir(parents=True, exist_ok=True)
    saved_dom_path = saved_dom_dir / f"{domain_name}_{flaw_id}_{agent_type}.pddl"
    saved_dom_path.write_text(gen_dom or "", encoding="utf-8")

    metrics: EvaluationMetrics = evaluate_candidate_pddl(
        task=task,
        agent_type=agent_type,
        generated_domain_pddl=gen_dom,
        generated_problem_pddl=gen_prob,
        iterations_used=iters,
        execution_time_seconds=elapsed,
        total_tokens=final_state.get("total_tokens", 0),
        estimated_cost_usd=final_state.get("estimated_cost_usd", 0.0)
    )

    penalized_iterations = iters if metrics.e2e_success else max_iters
    probs_total = metrics.problems_evaluated if metrics.problems_evaluated > 0 else 1

    return {
        "domain": domain_name,
        "flaw_id": flaw_id,
        "fault_category": task.fault_category,
        "target_action": task.gold_fault_element,
        "agent_type": agent_type,
        "e2e_success": metrics.e2e_success,
        "problems_passed": f"{metrics.problems_passed}/{probs_total}",
        "syntax_valid": metrics.is_syntax_valid,
        "internal_solvable": metrics.is_solvable,
        "executability": metrics.executability_valid,
        "feasibility": metrics.feasibility_valid,
        "interpretability": metrics.interpretability_valid,
        "iterations_used": iters,
        "penalized_iterations": penalized_iterations,
        "execution_time_sec": round(elapsed, 2),
        "total_tokens": metrics.total_tokens,
        "estimated_cost_usd": round(metrics.estimated_cost_usd, 6),
        "generated_domain_path": str(saved_dom_path)
    }


def compute_statistics(completed_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes McNemar's exact test and Wilcoxon signed-rank test."""
    paired = {}
    for r in completed_records:
        key = (r["domain"], r["flaw_id"])
        if key not in paired:
            paired[key] = {}
        paired[key][r["agent_type"]] = r

    valid_pairs = [p for p in paired.values() if "CLOSED_LOOP_AST_AGENT" in p and "ABLATION_NO_TRIAGE" in p]
    if not valid_pairs:
        return {}

    n_pairs = len(valid_pairs)
    a = sum(1 for p in valid_pairs if p["CLOSED_LOOP_AST_AGENT"]["e2e_success"] and p["ABLATION_NO_TRIAGE"]["e2e_success"])
    b = sum(1 for p in valid_pairs if p["CLOSED_LOOP_AST_AGENT"]["e2e_success"] and not p["ABLATION_NO_TRIAGE"]["e2e_success"])
    c = sum(1 for p in valid_pairs if not p["CLOSED_LOOP_AST_AGENT"]["e2e_success"] and p["ABLATION_NO_TRIAGE"]["e2e_success"])
    d = sum(1 for p in valid_pairs if not p["CLOSED_LOOP_AST_AGENT"]["e2e_success"] and not p["ABLATION_NO_TRIAGE"]["e2e_success"])

    total_discordant = b + c
    if total_discordant > 0:
        mcnemar_p = binom_test_exact(b, total_discordant, 0.5)
    else:
        mcnemar_p = 1.0

    full_iters = [p["CLOSED_LOOP_AST_AGENT"]["penalized_iterations"] for p in valid_pairs]
    notriage_iters = [p["ABLATION_NO_TRIAGE"]["penalized_iterations"] for p in valid_pairs]

    w_stat, wilcoxon_p = wilcoxon_signed_rank_pure(full_iters, notriage_iters)

    full_successes = sum(1 for p in valid_pairs if p["CLOSED_LOOP_AST_AGENT"]["e2e_success"])
    notriage_successes = sum(1 for p in valid_pairs if p["ABLATION_NO_TRIAGE"]["e2e_success"])

    full_mean_iter = sum(full_iters) / n_pairs
    notriage_mean_iter = sum(notriage_iters) / n_pairs

    return {
        "n_evaluated_tasks": n_pairs,
        "closed_loop_agent": {
            "success_count": full_successes,
            "success_rate_percent": round(full_successes / n_pairs * 100, 2),
            "mean_penalized_iterations": round(full_mean_iter, 3)
        },
        "ablation_no_triage": {
            "success_count": notriage_successes,
            "success_rate_percent": round(notriage_successes / n_pairs * 100, 2),
            "mean_penalized_iterations": round(notriage_mean_iter, 3)
        },
        "mcnemar_test": {
            "table": {"a_both_pass": a, "b_full_only": b, "c_notriage_only": c, "d_both_fail": d},
            "discordant_pairs": total_discordant,
            "p_value": round(mcnemar_p, 5),
            "significant_at_05": mcnemar_p < 0.05
        },
        "wilcoxon_test": {
            "statistic": round(w_stat, 2),
            "p_value": round(wilcoxon_p, 5),
            "significant_at_05": wilcoxon_p < 0.05
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate Hypothesis H2 on Curated Flaws Benchmark")
    parser.add_argument("--output-csv", default=str(RUNS_CSV), help="Path to output CSV file")
    parser.add_argument("--summary-json", default=str(SUMMARY_JSON), help="Path to summary JSON file")
    parser.add_argument("--max-iters", type=int, default=MAX_ITERATIONS, help="Max repair iterations")
    parser.add_argument("--domains", nargs="+", default=None, help="Specific domain(s) to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Limit total number of flaw tasks")
    parser.add_argument("--manifest", default=str(MANIFEST_FILE), help="Path to flaw manifest JSON")
    args = parser.parse_args()

    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)

    tasks = load_manifest_tasks(Path(args.manifest))
    if args.domains:
        target_doms = set(args.domains)
        tasks = [t for t in tasks if t[0] in target_doms]
    if args.limit and args.limit > 0:
        tasks = tasks[:args.limit]

    print("=" * 85)
    print("  HYPOTHESIS H2 EVALUATION: CLOSED_LOOP_AST_AGENT vs ABLATION_NO_TRIAGE")
    print(f"  Manifest: {args.manifest}")
    print(f"  Target Output CSV: {output_csv}")
    print(f"  Target Summary JSON: {summary_json}")
    print(f"  Saved Domains Dir: {GENERATED_DOMAINS_H2_DIR}")
    print(f"  Max Iterations per Task: {args.max_iters}")
    print("=" * 85, flush=True)

    print(f"Total benchmark tasks loaded for evaluation: {len(tasks)}")

    completed_keys = set()
    records = []
    fieldnames = [
        "domain", "flaw_id", "fault_category", "target_action", "agent_type",
        "e2e_success", "problems_passed", "syntax_valid", "internal_solvable", "executability",
        "feasibility", "interpretability", "iterations_used", "penalized_iterations",
        "execution_time_sec", "total_tokens", "estimated_cost_usd", "generated_domain_path"
    ]

    if output_csv.exists():
        with open(output_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                completed_keys.add((row["domain"], row["flaw_id"], row["agent_type"]))
                records.append({
                    "domain": row["domain"],
                    "flaw_id": row["flaw_id"],
                    "fault_category": row["fault_category"],
                    "target_action": row["target_action"],
                    "agent_type": row["agent_type"],
                    "e2e_success": row["e2e_success"].lower() == "true",
                    "problems_passed": row.get("problems_passed", ""),
                    "syntax_valid": row["syntax_valid"].lower() == "true",
                    "internal_solvable": row["internal_solvable"].lower() == "true",
                    "executability": row["executability"].lower() == "true",
                    "feasibility": row["feasibility"].lower() == "true",
                    "interpretability": row["interpretability"].lower() == "true",
                    "iterations_used": int(row["iterations_used"]),
                    "penalized_iterations": int(row["penalized_iterations"]),
                    "execution_time_sec": float(row["execution_time_sec"]),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "estimated_cost_usd": float(row.get("estimated_cost_usd") or 0.0),
                    "generated_domain_path": row.get("generated_domain_path", "")
                })
        print(f"Loaded {len(records)} existing completed task records from {output_csv.name}.")

    total_runs = len(tasks) * len(ARCHITECTURES)
    run_idx = len(records)

    for domain_name, flaw_id in tasks:
        for agent_type in ARCHITECTURES:
            key = (domain_name, flaw_id, agent_type)
            if key in completed_keys:
                continue

            run_idx += 1
            print(f"\n[{run_idx}/{total_runs}] Running {agent_type} on {domain_name} / {flaw_id}...", flush=True)
            try:
                res = run_single_repair_task(domain_name, flaw_id, agent_type, max_iters=args.max_iters)
                records.append(res)
                completed_keys.add(key)

                print(
                    f"  -> Result: E2E={res['e2e_success']} | Problems={res['problems_passed']} "
                    f"| Iterations={res['iterations_used']} | Time={res['execution_time_sec']}s",
                    flush=True
                )
                print(f"  -> Saved Domain: {res['generated_domain_path']}", flush=True)

                file_exists = output_csv.exists() and output_csv.stat().st_size > 0
                with open(output_csv, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(res)

            except Exception as e:
                print(f"  [!] Error executing task {key}: {e}", flush=True)

    print("\n" + "=" * 85)
    print("  SAVED REPAIRED DOMAIN FILES:")
    for r in records:
        if r.get("generated_domain_path"):
            print(f"  * [{r['domain']} | {r['flaw_id']} | {r['agent_type']}] -> {r['generated_domain_path']}")
    print("=" * 85)
    print("  COMPUTING FORMAL HYPOTHESIS H2 STATISTICAL TESTS")
    print("=" * 85)

    stats_summary = compute_statistics(records)
    summary_json.write_text(json.dumps(stats_summary, indent=2), encoding="utf-8")

    print(json.dumps(stats_summary, indent=2))
    print("=" * 85)
    print(f"Runs saved to: {output_csv}")
    print(f"Summary saved to: {summary_json}")
    print("=" * 85, flush=True)


if __name__ == "__main__":
    main()
