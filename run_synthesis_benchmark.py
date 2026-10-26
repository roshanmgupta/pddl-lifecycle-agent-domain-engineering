"""
run_synthesis_benchmark.py
Autonomous Empirical Benchmark Runner for the 10 Selected Benchmark Domains.

Evaluates the 5 formal experimental conditions:
1. ZERO_SHOT (Baseline 1): Direct one-shot PDDL text generation from prompt.
2. UNSTRUCTURED_RETRY (Baseline 2): Closed-loop raw PDDL text re-prompting with terminal compiler/solver logs.
3. ABLATION_NO_AST (Ablation 1 - Tests H1): Closed-loop direct PDDL text repair with structured Diagnostic Triage reports.
4. ABLATION_NO_TRIAGE (Ablation 2 - Tests H2): Closed-loop AST Blueprint repair with raw terminal logs (skips triage).
5. CLOSED_LOOP_AST_AGENT (Full Proposed UPDEAgent): Closed-loop AST Blueprint + Layered Diagnostic Triage + Deterministic Compiler.

Outputs:
- Dedicated isolated directory: results/runs/synthesis_benchmark_<timestamp>/
  - metrics.csv: Standardized operational and structural metrics.
  - report.md: Formatted Markdown evaluation report.
  - artifacts/: Generated domain, problem, and plan files per evaluated task.
"""

import sys
import os
import csv
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.loader import load_selected_evaluation_tasks, SELECTED_BENCHMARK_DOMAINS
from eval.benchmark_runner import run_evaluation_on_task, generate_evaluation_report
from eval.metrics import EvaluationMetrics
from config.paths import create_run_directory

def main():
    tasks = load_selected_evaluation_tasks()
    print(f"==========================================================================")
    print(f" EMPIRICAL BENCHMARK: 10 SELECTED BENCHMARK DOMAINS ({len(tasks)} TASKS)")
    print(f" Target Domains: {SELECTED_BENCHMARK_DOMAINS}")
    print(f"==========================================================================")

    # Agent configurations to evaluate
    agent_configs = [
        "ZERO_SHOT",
        "UNSTRUCTURED_RETRY",
        "ABLATION_NO_AST",
        "ABLATION_NO_TRIAGE",
        "CLOSED_LOOP_AST_AGENT"
    ]

    all_metrics = []
    
    # Isolated Per-Run Output Directory
    run_dir = create_run_directory(tag="synthesis_benchmark")
    csv_file = run_dir / "metrics.csv"
    report_file = run_dir / "report.md"

    fieldnames = [
        "task_id", "domain_family", "task_type", "agent_type",
        "svr_syntax_valid_rate", "tpv_target_plan_valid", "cov_ref_coverage_rate",
        "reference_instances_passed", "reference_instances_total",
        "macro_structural_f1", "precondition_f1", "add_effect_f1", "delete_effect_f1", "action_f1",
        "plan_length", "plan_cost", "search_time",
        "iterations_used", "execution_time_seconds", "total_tokens", "estimated_cost_usd",
        "behavioral_code", "error_summary"
    ]

    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, task in enumerate(tasks, 1):
            print(f"\n--------------------------------------------------------------------------")
            print(f" Task [{idx}/{len(tasks)}]: {task.task_id} ({task.task_type.value}) - Domain: {task.domain_family}")
            print(f"--------------------------------------------------------------------------")

            for agent in agent_configs:
                print(f"  [Evaluating Agent: {agent}]...", end="", flush=True)
                start_t = time.time()
                try:
                    m = run_evaluation_on_task(task, agent, max_iterations=5)
                    all_metrics.append(m)
                    elapsed = round(time.time() - start_t, 2)
                    print(f" Done in {elapsed}s | SVR={m.svr_syntax_valid_rate >= 1.0} | TPV={m.tpv_target_plan_valid} | Macro_F1={m.macro_structural_f1} | Iters={m.iterations_used}")
                    
                    row_dict = {k: getattr(m, k, None) for k in fieldnames}
                    writer.writerow(row_dict)
                    f.flush()
                except Exception as e:
                    print(f" FAILED with exception: {e}")

    # Generate and save summary report
    report_md = generate_evaluation_report(all_metrics)
    with open(report_file, "w", encoding="utf-8") as rf:
        rf.write(report_md)

    print(f"\n==========================================================================")
    print(f" Benchmark Complete! Results saved to:")
    print(f" - Run Folder : {run_dir.resolve()}")
    print(f" - CSV        : {csv_file.resolve()}")
    print(f" - Report     : {report_file.resolve()}")
    print(f"==========================================================================")

if __name__ == "__main__":
    main()
