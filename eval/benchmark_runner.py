import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from eval.metrics import EvaluationMetrics
from eval.baselines import run_zero_shot_baseline, run_unstructured_retry_baseline, run_no_ast_ablation
from graph import pddl_lifecycle_graph
from tools.symbolic_oracles import run_val_validator, run_fast_downward_with_plan
from config.paths import get_eval_output_dir


def run_evaluation_on_task(task: BenchmarkTask, agent_type: str, max_iterations: int = 5) -> EvaluationMetrics:
    """Executes evaluation of a single benchmark task using the specified agent architecture."""
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
            "skip_fault_localization": (agent_type == "ABLATION_NO_TRIAGE")
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
            executability_valid=False,
            is_repaired=False,
            iterations_used=iterations_used,
            execution_time_seconds=round(execution_time_seconds, 2),
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            error_summary="Generation Failed: Incomplete or missing domain/problem PDDL output from agent."
        )

    from eval.verification_pipeline import verify_pddl_candidate

    gt_dom_str = getattr(task, "ground_truth_domain_pddl", None) or getattr(task, "initial_domain_pddl", None)
    gt_prob_str = getattr(task, "ground_truth_problem_pddl", None) or getattr(task, "initial_problem_pddl", None)

    verif = verify_pddl_candidate(
        generated_domain_pddl=generated_domain_pddl,
        generated_problem_pddl=generated_problem_pddl,
        ground_truth_domain_pddl=gt_dom_str,
        ground_truth_problem_pddl=gt_prob_str,
        temp_dir=Path(eval_dir),
        tag=f"{task.task_id}_{agent_type}"
    )

    is_syntax_valid = verif["is_syntax_valid"]
    svr_syntax_valid_rate = 1.0 if is_syntax_valid else 0.0
    is_solvable = verif["is_solvable"]
    is_plan_valid = is_solvable
    planner_timeout = verif["planner_timeout"]
    executability_valid = verif["executability_valid"]
    feasibility_valid = verif["feasibility_valid"]
    interpretability_valid = verif["interpretability_valid"]
    semantic_soundness = verif["semantic_soundness"]
    e2e_gate_success = verif["e2e_success"]
    tpv_target_plan_valid = bool(is_syntax_valid and is_solvable and executability_valid)

    plan_length = verif["plan_length"]
    plan_cost = verif["plan_cost"]
    search_time = verif["search_time_sec"]

    if not is_syntax_valid:
        error_summary = error_summary or ("VAL Syntax Error: " + (verif.get("val_syntax_log", "")[:200]))
    elif not is_plan_valid:
        if planner_timeout:
            error_summary = "Planner Search Timeout (30s): Unsolvability not proven."
        else:
            error_summary = error_summary or ("Planner Unsolvability: " + (verif.get("raw_fd_log", "")[:200]))
    elif not executability_valid:
        error_summary = error_summary or "Plan Certification Failed: Generated plan failed VAL on generated domain."
    elif not feasibility_valid:
        error_summary = error_summary or "Feasibility Failed: Generated plan failed VAL on ground-truth domain."
    elif not interpretability_valid:
        error_summary = error_summary or "Interpretability Failed: Ground-truth plan failed VAL on generated domain."

    macro_structural_f1 = verif.get("macro_structural_f1")
    precondition_f1 = verif.get("precondition_f1")
    add_effect_f1 = verif.get("add_effect_f1")
    delete_effect_f1 = verif.get("delete_effect_f1")
    action_f1 = verif.get("action_f1")
    parameter_arity_match = verif.get("parameter_arity_match")

    # -------------------------------------------------------------
    # Hierarchical Multi-Granular Fault Localization (H-MGFL) Metrics
    # -------------------------------------------------------------
    top1_element = None
    top1_repair_op = None

    if diagnostic_reports and len(diagnostic_reports) > 0:
        first_rep = diagnostic_reports[0]
        top1_element = getattr(first_rep, "faulty_element", "") if hasattr(first_rep, "faulty_element") else str(first_rep.get("faulty_element", ""))
        top1_repair_op = str(getattr(first_rep, "repair_operation_type", "") if hasattr(first_rep, "repair_operation_type") else first_rep.get("repair_operation_type", ""))


    cov_ref_coverage_rate = None
    hist_passed = None
    hist_total = None

    # -------------------------------------------------------------
    # Standardized Behavioral Outcome Classification
    # -------------------------------------------------------------
    from eval.verification_pipeline import classify_behavioral_outcome
    behavioral_code, defect_class = classify_behavioral_outcome(
        is_syntax_valid=is_syntax_valid,
        is_solvable=is_solvable,
        executability_valid=executability_valid,
        feasibility_valid=feasibility_valid,
        interpretability_valid=interpretability_valid,
        macro_f1=macro_structural_f1 or 0.0,
        iters=iterations_used,
        planner_timed_out=planner_timeout
    )

    return EvaluationMetrics(
        task_id=task.task_id,
        domain_family=task.domain_family,
        task_type=task.task_type.value,
        agent_type=agent_type,
        svr_syntax_valid_rate=svr_syntax_valid_rate,
        is_solvable=is_solvable,
        planner_timeout=planner_timeout,
        executability_valid=executability_valid,
        feasibility_valid=feasibility_valid,
        interpretability_valid=interpretability_valid,
        semantic_soundness=semantic_soundness,
        e2e_gate_success=e2e_gate_success,
        tpv_target_plan_valid=tpv_target_plan_valid,
        cov_ref_coverage_rate=cov_ref_coverage_rate,
        reference_instances_passed=hist_passed,
        reference_instances_total=hist_total,
        macro_structural_f1=macro_structural_f1,
        precondition_f1=None,
        add_effect_f1=None,
        delete_effect_f1=None,
        action_f1=None,
        parameter_arity_match=parameter_arity_match,
        top1_element=top1_element,
        top1_repair_op=top1_repair_op,
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
                print(f"  --> Result: E2E={metrics.e2e_success} | Syntax={metrics.is_syntax_valid} | Solvable={metrics.is_plan_valid} | Exec={metrics.executability_valid} | Iters={metrics.iterations_used} | Cost=${metrics.estimated_cost_usd:.4f}")
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
                    executability_valid=False,
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
        "## 1. Decoupled Multi-Stage Verification Funnel Table",
        "",
        "| Agent Architecture | Tasks | SVR (%) | Solvability (%) | Timeout (%) | Executability (%) | Feasibility (%) | Interpretability (%) | Semantic Soundness (%) | Strict E2E (%) |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]

    agent_groups: Dict[str, List[EvaluationMetrics]] = {}
    for m in metrics_list:
        if m.agent_type not in agent_groups:
            agent_groups[m.agent_type] = []
        agent_groups[m.agent_type].append(m)

    for agent, group in agent_groups.items():
        total = len(group)
        svr_count = sum(1 for m in group if m.svr_syntax_valid_rate >= 1.0)
        solv_count = sum(1 for m in group if m.is_solvable)
        tout_count = sum(1 for m in group if m.planner_timeout)
        exec_count = sum(1 for m in group if m.executability_valid)
        feas_count = sum(1 for m in group if m.feasibility_valid)
        interp_count = sum(1 for m in group if m.interpretability_valid)
        sound_count = sum(1 for m in group if m.semantic_soundness)
        e2e_count = sum(1 for m in group if m.e2e_success)

        svr_pct = round((svr_count / total) * 100, 1) if total > 0 else 0.0
        solv_pct = round((solv_count / total) * 100, 1) if total > 0 else 0.0
        tout_pct = round((tout_count / total) * 100, 1) if total > 0 else 0.0
        exec_pct = round((exec_count / total) * 100, 1) if total > 0 else 0.0
        feas_pct = round((feas_count / total) * 100, 1) if total > 0 else 0.0
        interp_pct = round((interp_count / total) * 100, 1) if total > 0 else 0.0
        sound_pct = round((sound_count / total) * 100, 1) if total > 0 else 0.0
        e2e_pct = round((e2e_count / total) * 100, 1) if total > 0 else 0.0

        lines.append(
            f"| **{agent}** | {total} | {svr_pct}% | {solv_pct}% | {tout_pct}% | "
            f"{exec_pct}% | {feas_pct}% | {interp_pct}% | {sound_pct}% | **{e2e_pct}%** |"
        )

    # -------------------------------------------------------------
    # 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Table
    # -------------------------------------------------------------
    lines.extend([
        "",
        "## 2. Hierarchical Multi-Granular Semantic Alignment Performance",
        "",
        "| Agent Architecture | Tasks | L1: Action F1 | L2: Parameter Arity (%) | L2: Pre F1 | L2: Add F1 | L2: Del F1 |",
        "|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    ])

    for agent, group in agent_groups.items():
        total = len(group)
        act_tasks = [m for m in group if m.action_f1 is not None]
        avg_act_f1 = round(sum(m.action_f1 for m in act_tasks) / len(act_tasks), 3) if act_tasks else "N/A"


        arity_tasks = [m for m in group if m.parameter_arity_match is not None]
        avg_arity = round(sum(m.parameter_arity_match for m in arity_tasks) / len(arity_tasks) * 100, 1) if arity_tasks else "N/A"

        pre_tasks = [m for m in group if m.precondition_f1 is not None]
        avg_pre = round(sum(m.precondition_f1 for m in pre_tasks) / len(pre_tasks), 3) if pre_tasks else "N/A"

        add_tasks = [m for m in group if m.add_effect_f1 is not None]
        avg_add = round(sum(m.add_effect_f1 for m in add_tasks) / len(add_tasks), 3) if add_tasks else "N/A"

        del_tasks = [m for m in group if m.delete_effect_f1 is not None]
        avg_del = round(sum(m.delete_effect_f1 for m in del_tasks) / len(del_tasks), 3) if del_tasks else "N/A"

        arity_str = f"{avg_arity}%" if isinstance(avg_arity, (int, float)) else avg_arity

        lines.append(
            f"| **{agent}** | {total} | {avg_act_f1} | {arity_str} | {avg_pre} | {avg_add} | {avg_del} |"
        )

    lines.extend([
        "",
        "## 3. Granular Task Execution Log",
        "",
        "| Task ID | Agent Architecture | SVR | TPV | Cov_ref | L1 Top-1 Element | L2 Top-1 Op | |Plan| | Iters (k) | Code | Diagnostic Summary |",
        "|:---|:---|:---:|:---:|:---:|:---|:---|:---:|:---:|:---:|:---|"
    ])

    for m in metrics_list:
        err = m.error_summary if m.error_summary else "Passed (Verified)"
        clean_err = err.encode("ascii", "ignore").decode("ascii").replace("|", "/").replace("\n", " ")[:60]
        c_rate = f"{round(m.cov_ref_coverage_rate)}%" if m.cov_ref_coverage_rate is not None else "N/A"
        p_len = str(m.plan_length) if m.plan_length is not None else "N/A"
        b_code = m.behavioral_code or "N/A"
        top1_elem_str = m.top1_element or "N/A"
        top1_op_str = m.top1_repair_op or "N/A"
        lines.append(
            f"| `{m.task_id}` | `{m.agent_type}` | {m.svr_syntax_valid_rate >= 1.0} | "
            f"**{m.tpv_target_plan_valid}** | {c_rate} | `{top1_elem_str}` | `{top1_op_str}` | {p_len} | "
            f"{m.iterations_used} | `{b_code}` | {clean_err} |"
        )

    return "\n".join(lines)


def save_metrics_to_csv(metrics_list: List[EvaluationMetrics], output_csv_path: str):
    """Saves all evaluation metrics including Hierarchical Multi-Granular Fault Localization (H-MGFL) to CSV."""
    import csv
    if not metrics_list:
        return

    csv_fields = [
        "task_id", "domain_family", "task_type", "agent_type",
        # Decoupled Multi-Stage Verification Funnel
        "svr_syntax_valid_rate", "is_solvable", "planner_timeout",
        "executability_valid", "feasibility_valid", "interpretability_valid",
        "semantic_soundness", "e2e_gate_success", "e2e_success",
        "tpv_target_plan_valid", "cov_ref_coverage_rate",
        "reference_instances_passed", "reference_instances_total",
        # Level 1 AST Element Granularity
        "action_f1", "top1_element",
        # Level 2 Causal Component Granularity
        "top1_repair_op", "parameter_arity_match", "precondition_f1", "add_effect_f1", "delete_effect_f1",
        "plan_length", "plan_cost", "search_time",
        "iterations_used", "execution_time_seconds", "total_tokens", "estimated_cost_usd",
        "behavioral_code", "error_summary"
    ]

    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for m in metrics_list:
            row = {}
            for k in csv_fields:
                val = getattr(m, k, None)
                row[k] = val if val is not None else ""
            writer.writerow(row)
