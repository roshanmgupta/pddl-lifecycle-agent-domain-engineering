"""
eval/statistical_significance.py
Rigorous literature-grounded statistical significance and 3-run aggregation
module for Master's Thesis empirical evaluation.

Directly implements the experimental evaluation protocols:
1. 3-Run Aggregation:
   - Task success: True if at least 2 of the 3 runs succeed (>= 2/3).
   - Iterations: Mean over the 3 runs, with failed runs penalized as 6.
2. Hypothesis H1 Tests:
   - McNemar's test on binary success, comparing Full Agent with ABLATION_NO_AST and ZERO_SHOT.
3. Hypothesis H2 Tests:
   - McNemar's test on binary success comparing Full Agent with ABLATION_NO_TRIAGE.
   - Wilcoxon signed-rank test on iterations comparing Full Agent with ABLATION_NO_TRIAGE.
4. Descriptive reporting tables for SVR, Success Rate, Mean Iterations, Tokens, and Latency.
"""

import math
from typing import List, Dict, Any, Tuple, Optional


def compute_exact_mcnemar_test(
    condition_a_successes: List[bool],
    condition_b_successes: List[bool]
) -> Dict[str, Any]:
    """
    Computes McNemar's test with exact binomial distribution for paired binary outcomes.
    
    Contingency matrix:
      b = Condition A succeeds, Condition B fails
      c = Condition A fails, Condition B succeeds
    """
    if len(condition_a_successes) != len(condition_b_successes):
        raise ValueError("Paired samples must have equal length.")
    
    n = len(condition_a_successes)
    a_count = 0  # Both succeed
    b_count = 0  # A succeeds, B fails
    c_count = 0  # A fails, B succeeds
    d_count = 0  # Both fail

    for sa, sb in zip(condition_a_successes, condition_b_successes):
        if sa and sb:
            a_count += 1
        elif sa and not sb:
            b_count += 1
        elif not sa and sb:
            c_count += 1
        else:
            d_count += 1

    total_discordant = b_count + c_count
    
    if total_discordant == 0:
        return {
            "n_total": n,
            "both_succeed": a_count,
            "a_only": b_count,
            "b_only": c_count,
            "both_fail": d_count,
            "statistic_chi2": 0.0,
            "p_value": 1.0,
            "method": "Exact Binomial (No discordant pairs)"
        }

    # Chi-square with Edwards continuity correction
    chi2 = ((abs(b_count - c_count) - 1.0) ** 2) / total_discordant

    # Exact two-sided binomial p-value: P(X <= min(b, c)) where X ~ Binomial(n_discordant, 0.5)
    k = min(b_count, c_count)
    p_cum = sum(math.comb(total_discordant, i) * (0.5 ** total_discordant) for i in range(k + 1))
    p_value = min(1.0, 2.0 * p_cum)

    return {
        "n_total": n,
        "both_succeed": a_count,
        "a_only": b_count,
        "b_only": c_count,
        "both_fail": d_count,
        "statistic_chi2": round(chi2, 4),
        "p_value": round(p_value, 5),
        "method": "Exact Binomial Two-Sided"
    }


def compute_wilcoxon_signed_rank_test(
    condition_a_values: List[float],
    condition_b_values: List[float]
) -> Dict[str, Any]:
    """
    Computes Wilcoxon signed-rank test for paired continuous/ordinal samples.
    Used for comparing iteration counts on paired benchmark tasks.
    """
    if len(condition_a_values) != len(condition_b_values):
        raise ValueError("Paired samples must have equal length.")

    n_pairs = len(condition_a_values)
    diffs = [a - b for a, b in zip(condition_a_values, condition_b_values)]
    
    # Filter out zero differences (standard Pratt or Wilcoxon reduction)
    non_zero = [(abs(d), d) for d in diffs if d != 0]
    n_nonzero = len(non_zero)

    if n_nonzero == 0:
        return {
            "n_pairs": n_pairs,
            "n_nonzero": 0,
            "w_statistic": 0.0,
            "z_statistic": 0.0,
            "p_value": 1.0,
            "method": "Zero differences across all pairs"
        }

    # Sort by absolute difference
    non_zero.sort(key=lambda x: x[0])

    # Assign average ranks for ties
    ranked = []
    i = 0
    while i < n_nonzero:
        val = non_zero[i][0]
        tie_indices = [j for j in range(i, n_nonzero) if non_zero[j][0] == val]
        avg_rank = sum(idx + 1 for idx in tie_indices) / len(tie_indices)
        for idx in tie_indices:
            ranked.append((avg_rank, non_zero[idx][1]))
        i += len(tie_indices)

    # Sum positive and negative ranks
    w_pos = sum(r for r, d in ranked if d > 0)
    w_neg = sum(r for r, d in ranked if d < 0)
    w_stat = min(w_pos, w_neg)

    # Normal approximation with continuity correction
    mean_w = n_nonzero * (n_nonzero + 1) / 4.0
    var_w = (n_nonzero * (n_nonzero + 1) * (2 * n_nonzero + 1)) / 24.0

    if var_w > 0:
        # Continuity correction toward mean
        z = (w_stat - mean_w + 0.5) / math.sqrt(var_w) if w_stat < mean_w else (w_stat - mean_w - 0.5) / math.sqrt(var_w)
        # Two-sided standard normal p-value
        p_val = 2.0 * 0.5 * math.erfc(abs(z) / math.sqrt(2.0))
    else:
        z = 0.0
        p_val = 1.0

    return {
        "n_pairs": n_pairs,
        "n_nonzero": n_nonzero,
        "w_pos": round(w_pos, 2),
        "w_neg": round(w_neg, 2),
        "w_statistic": round(w_stat, 2),
        "z_statistic": round(z, 4),
        "p_value": round(p_val, 5),
        "method": "Wilcoxon Signed-Rank (Normal Approx with Continuity Correction)"
    }


def aggregate_runs_per_task(
    run_records: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregates multi-run records per task under the 3-run majority voting and penalty rules:
    - Task succeeds if at least 2 of the 3 runs succeed.
    - Iterations are the mean over the 3 runs, with failed runs counted as 6.
    - Automatically averages SVR, tokens, and latency.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in run_records:
        tid = r.get("task_id") or f"{r.get('domain')}_{r.get('flaw', 'task')}"
        grouped.setdefault(tid, []).append(r)

    aggregated: Dict[str, Dict[str, Any]] = {}
    for tid, runs in grouped.items():
        n_runs = len(runs)
        successes = [bool(r.get("e2e_success")) for r in runs]
        n_success = sum(1 for s in successes if s)
        
        # Rule 1: A condition succeeds per task if at least 2 of 3 runs succeed
        task_succeeds = (n_success >= 2) if n_runs >= 2 else (n_success >= 1)

        # Rule 2: Iterations mean over the 3 runs, with failed runs counted as 6
        penalized_iters = []
        for r in runs:
            if bool(r.get("e2e_success")):
                penalized_iters.append(float(r.get("iterations_used", 1)))
            else:
                penalized_iters.append(6.0)
        mean_iters = sum(penalized_iters) / len(penalized_iters) if penalized_iters else 6.0

        # SVR mean
        svrs = [1.0 if bool(r.get("is_syntax_valid") or r.get("init_syntax_ok")) else 0.0 for r in runs]
        mean_svr = sum(svrs) / len(svrs) if svrs else 0.0

        # Mean tokens and latency
        mean_prompt_tok = sum(r.get("prompt_tokens", 0) for r in runs) / n_runs
        mean_comp_tok = sum(r.get("completion_tokens", 0) for r in runs) / n_runs
        mean_tot_tok = sum(r.get("total_tokens", 0) for r in runs) / n_runs
        mean_latency = sum(r.get("execution_time_sec", 0.0) or r.get("execution_time_seconds", 0.0) for r in runs) / n_runs

        sample = runs[0]
        aggregated[tid] = {
            "task_id": tid,
            "domain": sample.get("domain") or sample.get("domain_family"),
            "agent": sample.get("agent") or sample.get("agent_type"),
            "runs_evaluated": n_runs,
            "runs_succeeded": n_success,
            "task_succeeds": task_succeeds,
            "mean_iterations_penalized": round(mean_iters, 2),
            "svr_rate": round(mean_svr, 3),
            "mean_prompt_tokens": round(mean_prompt_tok, 1),
            "mean_completion_tokens": round(mean_comp_tok, 1),
            "mean_total_tokens": round(mean_tot_tok, 1),
            "mean_latency_sec": round(mean_latency, 2)
        }

    return aggregated


def format_descriptive_thesis_table(
    condition_aggregates: Dict[str, Dict[str, Dict[str, Any]]]
) -> str:
    """
    Formats the definitive thesis descriptive table reporting:
    - Condition / Agent
    - Evaluated Tasks
    - Syntactic Validity Rate (SVR)
    - Success Rate (>= 2/3 voting rule)
    - Mean Iterations (with failed runs = 6)
    - Mean Total Tokens
    - Mean Latency (seconds)
    """
    lines = [
        "=" * 110,
        f"{'CONDITION / AGENT':<24} | {'TASKS':<7} | {'SVR':<8} | {'SUCCESS RATE':<14} | {'MEAN ITERS (P=6)':<18} | {'TOKENS':<10} | {'LATENCY (s)'}",
        "-" * 110
    ]

    for cond_name, tasks_dict in condition_aggregates.items():
        n_tasks = len(tasks_dict)
        if n_tasks == 0:
            continue
        n_succ = sum(1 for t in tasks_dict.values() if t["task_succeeds"])
        succ_pct = (n_succ / n_tasks) * 100.0
        avg_svr = (sum(t["svr_rate"] for t in tasks_dict.values()) / n_tasks) * 100.0
        avg_iters = sum(t["mean_iterations_penalized"] for t in tasks_dict.values()) / n_tasks
        avg_tokens = sum(t["mean_total_tokens"] for t in tasks_dict.values()) / n_tasks
        avg_latency = sum(t["mean_latency_sec"] for t in tasks_dict.values()) / n_tasks

        succ_str = f"{n_succ}/{n_tasks} ({succ_pct:.1f}%)"
        lines.append(
            f"{cond_name:<24} | {n_tasks:<7} | {avg_svr:.1f}%   | {succ_str:<14} | {avg_iters:<18.2f} | {int(avg_tokens):<10} | {avg_latency:<10.2f}"
        )

    lines.append("=" * 110)
    return "\n".join(lines)
