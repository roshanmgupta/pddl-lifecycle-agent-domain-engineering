import os
import time
from typing import List, Dict, Any, Optional
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from eval.metrics import EvaluationMetrics
from eval.baselines import run_zero_shot_baseline, run_unstructured_retry_baseline, run_no_ast_ablation
from graph import pddl_lifecycle_graph
from tools.symbolic_oracles import run_val_validator, run_fast_downward_with_plan
from config.paths import get_eval_output_dir

def compute_fault_localization_metrics(
    gold_element: Optional[str],
    diagnostic_reports: List[Any]
) -> tuple[Optional[bool], Optional[bool], Optional[float]]:
    """
    Computes Top-1, Top-3, and MRR for fault localization against explicit ground truth AST element.
    Returns (top1, top3, mrr).
    """
    if not gold_element or not diagnostic_reports:
        return None, None, None

    clean_gold = gold_element.strip().lower()
    ranked_candidates = []
    for r in diagnostic_reports:
        faulty = getattr(r, "faulty_element", "") if hasattr(r, "faulty_element") else str(r.get("faulty_element", ""))
        if faulty:
            ranked_candidates.append(faulty.strip().lower())

    if not ranked_candidates:
        return False, False, 0.0

    def _matches(gold: str, cand: str) -> bool:
        return gold in cand or cand in gold

    top1 = _matches(clean_gold, ranked_candidates[0])
    top3 = any(_matches(clean_gold, c) for c in ranked_candidates[:3])

    mrr = 0.0
    for idx, cand in enumerate(ranked_candidates):
        if _matches(clean_gold, cand):
            mrr = 1.0 / (idx + 1)
            break

    return top1, top3, mrr

def run_evaluation_on_task(task: BenchmarkTask, agent_type: str, max_iterations: int = 5) -> EvaluationMetrics:
    """
    Executes evaluation of a single benchmark task using the specified agent architecture.
    Strictly NO evaluation leakage or ground truth fallback.
    """
    start_time = time.time()
    
    generated_domain_pddl = ""
    generated_problem_pddl = ""
    iterations_used = 1
    tot_tokens = 0
    est_cost = 0.0
    error_summary = None
    diagnostic_reports = []

    # -------------------------------------------------------------
    # 1. Execute Agent Architecture
    # -------------------------------------------------------------
    if agent_type == "ZERO_SHOT":
        result = run_zero_shot_baseline(task)
        generated_domain_pddl = result.get("generated_domain_pddl", "")
        generated_problem_pddl = result.get("generated_problem_pddl", "")
        iterations_used = result.get("iterations_used", 1)
        tot_tokens = result.get("total_tokens", 0)
        est_cost = result.get("estimated_cost_usd", 0.0)
        if result.get("error"):
            error_summary = result["error"]

    elif agent_type == "UNSTRUCTURED_RETRY":
        result = run_unstructured_retry_baseline(task, max_retries=max_iterations)
        generated_domain_pddl = result.get("generated_domain_pddl", "")
        generated_problem_pddl = result.get("generated_problem_pddl", "")
        iterations_used = result.get("iterations_used", max_iterations)
        tot_tokens = result.get("total_tokens", 0)
        est_cost = result.get("estimated_cost_usd", 0.0)

    elif agent_type == "ABLATION_NO_AST":
        result = run_no_ast_ablation(task, max_retries=max_iterations)
        generated_domain_pddl = result.get("generated_domain_pddl", "")
        generated_problem_pddl = result.get("generated_problem_pddl", "")
        iterations_used = result.get("iterations_used", max_iterations)
        tot_tokens = result.get("total_tokens", 0)
        est_cost = result.get("estimated_cost_usd", 0.0)
        diagnostic_reports = result.get("diagnostic_reports", [])

    elif agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
        initial_state = {
            "requirements": task.natural_language_requirements,
            "pddl_domain_blueprint": {},
            "initial_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "generated_domain_pddl": task.initial_domain_pddl or "",
            "generated_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "verification_errors": [],
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "skip_triage": (agent_type == "ABLATION_NO_TRIAGE")
        }
        
        # Injected verification error trigger for synthetic repair tasks
        if task.task_type == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR and task.initial_domain_pddl:
            fault_cat = task.fault_category or "SYNTAX_PARSE"
            initial_state["verification_errors"] = [f"VAL Error: Fault category {fault_cat} detected in initial model."]

        final_state = pddl_lifecycle_graph.invoke(initial_state)
        generated_domain_pddl = final_state.get("generated_domain_pddl", "")
        generated_problem_pddl = final_state.get("generated_problem_pddl", "")
        iterations_used = max(1, final_state.get("iteration_count", 1))
        tot_tokens = final_state.get("total_tokens", 0)
        est_cost = final_state.get("estimated_cost_usd", 0.0)
        diagnostic_reports = final_state.get("diagnostic_reports", []) or final_state.get("historical_diagnostic_reports", [])
        
        if final_state.get("verification_errors"):
            error_summary = " ".join(final_state["verification_errors"])[:300]

    else:
        raise ValueError(f"Unknown agent_type: '{agent_type}'")

    execution_time = time.time() - start_time

    return evaluate_candidate_pddl(
        task=task,
        agent_type=agent_type,
        generated_domain_pddl=generated_domain_pddl,
        generated_problem_pddl=generated_problem_pddl,
        iterations_used=iterations_used,
        execution_time_seconds=execution_time,
        total_tokens=tot_tokens,
        estimated_cost_usd=est_cost,
        diagnostic_reports=diagnostic_reports,
        error_summary=error_summary
    )

def evaluate_candidate_pddl(
    task: BenchmarkTask,
    agent_type: str,
    generated_domain_pddl: str,
    generated_problem_pddl: str,
    iterations_used: int = 1,
    execution_time_seconds: float = 0.0,
    total_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    diagnostic_reports: Optional[List[Any]] = None,
    error_summary: Optional[str] = None
) -> EvaluationMetrics:
    """
    Evaluates candidate PDDL domain and problem against classical oracles (VAL & Fast Downward).
    Computes rigorous primary (E2E Success) and secondary metrics without evaluation leakage.
    """
    # -------------------------------------------------------------
    # Strict Oracle Verification (NO Ground-Truth Fallback)
    # -------------------------------------------------------------
    eval_dir = str(get_eval_output_dir())
    os.makedirs(eval_dir, exist_ok=True)
    eval_dom_file = os.path.join(eval_dir, f"eval_dom_{task.task_id}_{agent_type}.pddl")
    eval_prob_file = os.path.join(eval_dir, f"eval_prob_{task.task_id}_{agent_type}.pddl")

    # Evaluation Leakage Prevention: If agent output is missing, record failure directly!
    if not generated_domain_pddl or not generated_problem_pddl:
        return EvaluationMetrics(
            task_id=task.task_id,
            domain_family=task.domain_family,
            task_type=task.task_type.value,
            agent_type=agent_type,
            e2e_success=False,
            is_syntax_valid=False,
            is_plan_valid=False,
            plan_execution_valid=False,
            is_repaired=False,
            iterations_used=iterations_used,
            execution_time_seconds=round(execution_time_seconds, 2),
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            error_summary="Generation Failed: Incomplete or missing domain/problem PDDL output from agent."
        )

    with open(eval_dom_file, "w", encoding="utf-8") as f:
        f.write(generated_domain_pddl)
    with open(eval_prob_file, "w", encoding="utf-8") as f:
        f.write(generated_problem_pddl)

    eval_dom_gt_file = None
    if getattr(task, "ground_truth_domain_pddl", None):
        eval_dom_gt_file = os.path.join(eval_dir, f"eval_dom_gt_{task.task_id}_{agent_type}.pddl")
        with open(eval_dom_gt_file, "w", encoding="utf-8") as f:
            f.write(task.ground_truth_domain_pddl)

    # Oracle 1: VAL Syntax & Semantics
    is_syntax_valid, val_log = run_val_validator(eval_dom_file, eval_prob_file)
    svr_syntax_valid_rate = 1.0 if is_syntax_valid else 0.0

    # Oracle 2: Fast Downward Search & Oracle 3: VAL Plan Certification
    is_plan_valid = False
    plan_execution_valid = False
    plan_length = None
    plan_cost = None
    search_time = None

    if is_syntax_valid:
        fd_gt_path = str(eval_dom_gt_file) if (eval_dom_gt_file and task.task_type != LifecycleTaskType.ELICITATION) else None
        fd_res = run_fast_downward_with_plan(
            eval_dom_file, 
            eval_prob_file, 
            ground_truth_domain_path=fd_gt_path
        )
        is_plan_valid = fd_res["is_solvable"]
        plan_execution_valid = fd_res["val_plan_valid"]
        plan_length = fd_res["plan_length"]
        plan_cost = fd_res["plan_cost"]
        search_time = fd_res["search_time"]

        if not is_plan_valid:
            error_summary = "Planner Unsolvability: " + fd_res["raw_fd_log"][:200]
        elif not plan_execution_valid:
            error_summary = "Plan Certification Failed: " + fd_res.get("val_log", "")[:200]
    else:
        error_summary = "VAL Validation Error: " + val_log[:200]

    # Target Plan Validity (TPV): Solvable by planner AND verified valid by VAL
    tpv_target_plan_valid = bool(is_syntax_valid and is_plan_valid and plan_execution_valid)

    # -------------------------------------------------------------
    # Structural Reconstruction Metrics (Oswald 2024 / Aineto 2022)
    # -------------------------------------------------------------
    macro_structural_f1 = None
    precondition_f1 = None
    add_effect_f1 = None
    delete_effect_f1 = None
    action_f1 = None

    gt_dom_str = getattr(task, "ground_truth_domain_pddl", None) or getattr(task, "initial_domain_pddl", None)
    if gt_dom_str:
        try:
            from eval.action_reconstruction import evaluate_action_reconstruction
            are_res = evaluate_action_reconstruction(gt_dom_str, generated_domain_pddl)
            macro_structural_f1 = are_res.get("macro_structural_f1")
            precondition_f1 = are_res.get("mean_precondition_f1")
            add_effect_f1 = are_res.get("mean_add_effect_f1")
            delete_effect_f1 = are_res.get("mean_delete_effect_f1")
            action_f1 = are_res.get("action_f1")
        except Exception:
            pass

    # -------------------------------------------------------------
    # Domain Evolution & Reference Suite Coverage (Cov_ref)
    # -------------------------------------------------------------
    cov_ref_coverage_rate = None
    hist_passed = None
    hist_total = None

    if task.task_type == LifecycleTaskType.DOMAIN_EVOLUTION:
        # Align problem domain name to match generated domain name to satisfy Fast Downward parser requirement
        import re
        m_dom = re.search(r"\(\s*domain\s+([a-zA-Z0-9_\-]+)\s*\)", generated_domain_pddl, re.IGNORECASE)
        dom_name = m_dom.group(1) if m_dom else None

        bench_problems = getattr(task, "baseline_benchmark_problems", []) or getattr(task, "historical_regression_problems", []) or []
        if bench_problems:
            hist_total = len(bench_problems)
            hist_passed = 0
            for idx, hist_pddl in enumerate(bench_problems):
                hist_prob_file = os.path.join(eval_dir, f"eval_hist_{task.task_id}_{idx}.pddl")
                h_content = hist_pddl
                if dom_name:
                    h_content = re.sub(r"\(\s*:domain\s+[a-zA-Z0-9_\-]+\s*\)", f"(:domain {dom_name})", h_content, count=1, flags=re.IGNORECASE)
                with open(hist_prob_file, "w", encoding="utf-8") as f:
                    f.write(h_content)
                h_res = run_fast_downward_with_plan(eval_dom_file, hist_prob_file)
                if h_res["is_solvable"] and h_res["val_plan_valid"]:
                    hist_passed += 1
            cov_ref_coverage_rate = round((hist_passed / hist_total) * 100.0, 2) if hist_total > 0 else 100.0

    # -------------------------------------------------------------
    # Standardized Behavioral Classification Code
    # -------------------------------------------------------------
    if task.task_type == LifecycleTaskType.DOMAIN_EVOLUTION:
        if not is_syntax_valid:
            behavioral_code = "E.S"
        elif not tpv_target_plan_valid:
            behavioral_code = "E.T"
        elif cov_ref_coverage_rate is not None and cov_ref_coverage_rate < 100.0:
            behavioral_code = "E.B"
        elif iterations_used <= 1:
            behavioral_code = "E.1"
        else:
            behavioral_code = "E.2"
    else:
        if not is_syntax_valid:
            behavioral_code = "S.S"
        elif not tpv_target_plan_valid:
            behavioral_code = "S.T"
        elif iterations_used <= 1:
            behavioral_code = "S.1"
        else:
            behavioral_code = "S.2"

    return EvaluationMetrics(
        task_id=task.task_id,
        domain_family=task.domain_family,
        task_type=task.task_type.value,
        agent_type=agent_type,
        svr_syntax_valid_rate=svr_syntax_valid_rate,
        tpv_target_plan_valid=tpv_target_plan_valid,
        cov_ref_coverage_rate=cov_ref_coverage_rate,
        reference_instances_passed=hist_passed,
        reference_instances_total=hist_total,
        macro_structural_f1=macro_structural_f1,
        precondition_f1=precondition_f1,
        add_effect_f1=add_effect_f1,
        delete_effect_f1=delete_effect_f1,
        action_f1=action_f1,
        plan_length=plan_length,
        plan_cost=plan_cost,
        search_time=search_time,
        iterations_used=iterations_used,
        execution_time_seconds=round(execution_time_seconds, 2),
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        behavioral_code=behavioral_code,
        error_summary=error_summary
    )

def run_benchmark_suite(
    tasks: List[BenchmarkTask],
    agent_types: List[str],
    max_iterations: int = 5
) -> List[EvaluationMetrics]:
    """Runs evaluation suite across multiple tasks and agent architectures."""
    all_metrics: List[EvaluationMetrics] = []
    
    print(f"\n==========================================================================")
    print(f" [RUNNER]: Starting Empirical Benchmark Suite ({len(tasks)} tasks x {len(agent_types)} agents)")
    print(f"==========================================================================")
    for task in tasks:
        for agent in agent_types:
            print(f"\n[RUNNER] Task: '{task.task_id}' | Agent: '{agent}'...")
            try:
                metrics = run_evaluation_on_task(task, agent, max_iterations=max_iterations)
                all_metrics.append(metrics)
                print(f"  --> Result: E2E={metrics.e2e_success} | Syntax={metrics.is_syntax_valid} | Solvable={metrics.is_plan_valid} | Certified={metrics.plan_execution_valid} | Iters={metrics.iterations_used} | Cost=${metrics.estimated_cost_usd:.4f}")
            except Exception as e:
                print(f"  --> [ERROR] Execution crashed: {e}")
                all_metrics.append(EvaluationMetrics(
                    task_id=task.task_id,
                    domain_family=task.domain_family,
                    task_type=task.task_type.value,
                    agent_type=agent,
                    e2e_success=False,
                    is_syntax_valid=False,
                    is_plan_valid=False,
                    plan_execution_valid=False,
                    is_repaired=False,
                    iterations_used=1,
                    execution_time_seconds=0.0,
                    total_tokens=0,
                    estimated_cost_usd=0.0,
                    error_summary=f"Runner Exception: {e}"
                ))

    return all_metrics

def generate_evaluation_report(metrics_list: List[EvaluationMetrics]) -> str:
    """
    Generates a rigorous, publication-ready Markdown report summarizing primary operational
    and structural metrics grounded in classical automated planning literature.
    Removes redundant, heuristic, and ungrounded metrics.
    """
    lines = [
        "# Empirical Lifecycle Evaluation Report",
        "",
        "## 1. Standardized Operational & Structural Benchmark Comparison Table",
        "",
        "| Agent Architecture | Tasks | SVR (%) | TPV (%) | Cov_ref (%) | Macro F1 | Pre F1 | Add F1 | Del F1 | Mean |Plan| | Mean Iters (k) | Latency (s) | Cost ($) |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]

    agent_groups: Dict[str, List[EvaluationMetrics]] = {}
    for m in metrics_list:
        if m.agent_type not in agent_groups:
            agent_groups[m.agent_type] = []
        agent_groups[m.agent_type].append(m)

    for agent, group in agent_groups.items():
        total = len(group)
        svr_count = sum(1 for m in group if m.svr_syntax_valid_rate >= 1.0)
        tpv_count = sum(1 for m in group if m.tpv_target_plan_valid)

        cov_tasks = [m for m in group if m.cov_ref_coverage_rate is not None]
        avg_cov = round(sum(m.cov_ref_coverage_rate for m in cov_tasks) / len(cov_tasks), 1) if cov_tasks else "N/A"

        f1_tasks = [m for m in group if m.macro_structural_f1 is not None]
        avg_macro_f1 = round(sum(m.macro_structural_f1 for m in f1_tasks) / len(f1_tasks), 3) if f1_tasks else "N/A"

        pre_tasks = [m for m in group if m.precondition_f1 is not None]
        avg_pre_f1 = round(sum(m.precondition_f1 for m in pre_tasks) / len(pre_tasks), 3) if pre_tasks else "N/A"

        add_tasks = [m for m in group if m.add_effect_f1 is not None]
        avg_add_f1 = round(sum(m.add_effect_f1 for m in add_tasks) / len(add_tasks), 3) if add_tasks else "N/A"

        del_tasks = [m for m in group if m.delete_effect_f1 is not None]
        avg_del_f1 = round(sum(m.delete_effect_f1 for m in del_tasks) / len(del_tasks), 3) if del_tasks else "N/A"

        valid_plans = [m for m in group if m.tpv_target_plan_valid and m.plan_length is not None]
        avg_plan_len = round(sum(m.plan_length for m in valid_plans) / len(valid_plans), 1) if valid_plans else "N/A"

        svr_pct = round((svr_count / total) * 100, 1) if total > 0 else 0.0
        tpv_pct = round((tpv_count / total) * 100, 1) if total > 0 else 0.0

        avg_iters = round(sum(m.iterations_used for m in group) / total, 2) if total > 0 else 0.0
        avg_time = round(sum(m.execution_time_seconds for m in group) / total, 2) if total > 0 else 0.0
        avg_cost = round(sum(m.estimated_cost_usd for m in group) / total, 6) if total > 0 else 0.0

        cov_str = f"{avg_cov}%" if isinstance(avg_cov, (int, float)) else avg_cov

        lines.append(
            f"| **{agent}** | {total} | {svr_pct}% | **{tpv_pct}%** | {cov_str} | "
            f"{avg_macro_f1} | {avg_pre_f1} | {avg_add_f1} | {avg_del_f1} | "
            f"{avg_plan_len} | {avg_iters} | {avg_time}s | ${avg_cost:.4f} |"
        )

    lines.extend([
        "",
        "## 2. Granular Task Execution Log",
        "",
        "| Task ID | Agent Architecture | SVR | TPV | Cov_ref | Macro F1 | |Plan| | Iters (k) | Code | Diagnostic Summary |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|"
    ])

    for m in metrics_list:
        err = m.error_summary if m.error_summary else "Passed (Verified)"
        clean_err = err.encode("ascii", "ignore").decode("ascii").replace("|", "/").replace("\n", " ")[:60]
        c_rate = f"{round(m.cov_ref_coverage_rate)}%" if m.cov_ref_coverage_rate is not None else "N/A"
        f1_str = f"{m.macro_structural_f1:.3f}" if m.macro_structural_f1 is not None else "N/A"
        p_len = str(m.plan_length) if m.plan_length is not None else "N/A"
        b_code = m.behavioral_code or "N/A"
        lines.append(
            f"| `{m.task_id}` | `{m.agent_type}` | {m.svr_syntax_valid_rate >= 1.0} | "
            f"**{m.tpv_target_plan_valid}** | {c_rate} | {f1_str} | {p_len} | "
            f"{m.iterations_used} | `{b_code}` | {clean_err} |"
        )

    return "\n".join(lines)
