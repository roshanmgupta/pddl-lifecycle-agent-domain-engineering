"""
eval/merge_h2_results.py
Merges H2 fault repair runs across all 6 core domains:
- Blocksworld + Gripper (from dir_1)
- Logistics + Depot (from dir_2)
- Rovers + Satellite (from dir_3)
Computing the unified 24-task statistics, McNemar test on success, and Wilcoxon signed-rank test on iterations.
"""

import sys
import os
import csv
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.statistical_significance import (
    aggregate_runs_per_task,
    compute_exact_mcnemar_test,
    compute_wilcoxon_signed_rank_test,
    format_descriptive_thesis_table
)

def merge_all_h2_runs(dir_bg: Path, dir_ld: Path, dir_rs: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Blocksworld & Gripper from dir_bg
    with open(dir_bg / "metrics_all_runs.csv", "r", encoding="utf-8") as f:
        bg_records = [
            row for row in csv.DictReader(f)
            if row.get("domain") in ["blocksworld", "gripper"]
        ]
    print(f"Loaded {len(bg_records)} records for Blocksworld & Gripper from {dir_bg.name}")

    # 2. Logistics & Depot from dir_ld
    with open(dir_ld / "metrics_all_runs.csv", "r", encoding="utf-8") as f:
        ld_records = [
            row for row in csv.DictReader(f)
            if row.get("domain") in ["logistics", "depot"]
        ]
    print(f"Loaded {len(ld_records)} records for Logistics & Depot from {dir_ld.name}")

    # 3. Rovers & Satellite from dir_rs
    with open(dir_rs / "metrics_all_runs.csv", "r", encoding="utf-8") as f:
        rs_records = [
            row for row in csv.DictReader(f)
            if row.get("domain") in ["rovers", "satellite"]
        ]
    print(f"Loaded {len(rs_records)} records for Rovers & Satellite from {dir_rs.name}")

    all_records = bg_records + ld_records + rs_records
    print(f"Total unified H2 run records: {len(all_records)} (Expected: 144 = 24 tasks * 2 agents * 3 runs)")

    # Cast fields
    for r in all_records:
        r["run_idx"] = int(r.get("run_idx", 1))
        r["is_syntax_valid"] = str(r.get("is_syntax_valid")).strip().lower() == "true"
        r["e2e_success"] = str(r.get("e2e_success")).strip().lower() == "true"
        r["iterations_used"] = int(r.get("iterations_used", 1))
        r["prompt_tokens"] = int(float(r.get("prompt_tokens") or 0))
        r["completion_tokens"] = int(float(r.get("completion_tokens") or 0))
        r["total_tokens"] = int(float(r.get("total_tokens") or 0))
        r["execution_time_sec"] = float(r.get("execution_time_sec") or 0.0)

    # Save unified metrics_all_runs.csv
    fieldnames = list(all_records[0].keys())
    with open(out_dir / "metrics_all_runs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_records:
            writer.writerow(r)

    # Separate by condition
    conditions = ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]
    by_agent = {c: [r for r in all_records if r.get("agent") == c] for c in conditions}

    aggregated = {}
    for c in conditions:
        aggregated[c] = aggregate_runs_per_task(by_agent[c])

    # Save aggregated_tasks.csv
    agg_fields = [
        "task_id", "domain", "agent", "runs_evaluated", "runs_succeeded",
        "task_succeeds", "mean_iterations_penalized", "svr_rate",
        "mean_prompt_tokens", "mean_completion_tokens", "mean_total_tokens", "mean_latency_sec"
    ]
    with open(out_dir / "aggregated_tasks.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=agg_fields)
        writer.writeheader()
        for cond_dict in aggregated.values():
            for t in cond_dict.values():
                writer.writerow({k: t.get(k, "") for k in agg_fields})

    # Statistical significance: McNemar on success and Wilcoxon on iterations
    task_keys = sorted(list(aggregated["CLOSED_LOOP_AST_AGENT"].keys()))
    full_successes = [aggregated["CLOSED_LOOP_AST_AGENT"][k]["task_succeeds"] for k in task_keys]
    no_triage_successes = [aggregated["ABLATION_NO_TRIAGE"][k]["task_succeeds"] for k in task_keys]

    full_iters = [aggregated["CLOSED_LOOP_AST_AGENT"][k]["mean_iterations_penalized"] for k in task_keys]
    no_triage_iters = [aggregated["ABLATION_NO_TRIAGE"][k]["mean_iterations_penalized"] for k in task_keys]

    mcnemar_res = compute_exact_mcnemar_test(full_successes, no_triage_successes)
    wilcoxon_res = compute_wilcoxon_signed_rank_test(full_iters, no_triage_iters)

    # Generate Markdown Report
    table_str = format_descriptive_thesis_table(aggregated)
    report_lines = [
        "# Empirical Thesis Evaluation Report: Hypothesis H2 (Unified 24 Tasks)",
        "\n**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3 | **Total Runs**: 144\n",
        "## Hypothesis H2: Fault Repair Benchmark (Descriptive Table)",
        "```",
        table_str,
        "```\n",
        "### Statistical Significance Tests (H2 across 24 Tasks):",
        f"- **Full Agent vs ABLATION_NO_TRIAGE (Exact McNemar on Success)**: "
        f"Chi2 = {mcnemar_res['statistic_chi2']}, p-value = {mcnemar_res['p_value']} "
        f"(Discordant Pairs: Full Agent only = {mcnemar_res['a_only']}, No Triage only = {mcnemar_res['b_only']})",
        f"- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon Signed-Rank on Iterations)**: "
        f"W-statistic = {wilcoxon_res['w_statistic']}, z = {wilcoxon_res['z_statistic']}, p-value = {wilcoxon_res['p_value']}\n"
    ]

    report_text = "\n".join(report_lines)
    with open(out_dir / "thesis_report.md", "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n" + report_text)
    return {
        "aggregated": aggregated,
        "mcnemar": mcnemar_res,
        "wilcoxon": wilcoxon_res
    }

if __name__ == "__main__":
    dir_bg = PROJECT_ROOT / "results" / "runs" / "eval_h2_thesis_3runs_20261029_111801"
    dir_ld = PROJECT_ROOT / "results" / "runs" / "eval_h2_thesis_remaining_20261029_121435"
    dir_rs = PROJECT_ROOT / "results" / "runs" / "eval_h2_rovers_satellite_20261029_132015"
    out_dir = PROJECT_ROOT / "results" / "runs" / "eval_h2_thesis_unified_24tasks"
    merge_all_h2_runs(dir_bg, dir_ld, dir_rs, out_dir)
