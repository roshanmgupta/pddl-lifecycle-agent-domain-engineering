import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from eval.metrics import EvaluationMetrics
from config.paths import get_eval_output_dir


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
    Evaluates candidate PDDL domain against classical oracles (VAL & Fast Downward)
    across all ground-truth problem instances of the task.
    A task succeeds if and only if Soundness and Completeness hold across all of its problems.
    """
    eval_dir = str(get_eval_output_dir())
    os.makedirs(eval_dir, exist_ok=True)

    gt_problems: List[str] = list(getattr(task, "ground_truth_problems", None) or [])
    gt_gold_plans: List[str] = list(getattr(task, "ground_truth_gold_plans", None) or [])
    gt_prob_names: List[str] = list(getattr(task, "ground_truth_problem_names", None) or [])

    fallback_prob = getattr(task, "ground_truth_problem_pddl", None) or getattr(task, "initial_problem_pddl", None) or generated_problem_pddl
    if not gt_problems and fallback_prob:
        gt_problems = [fallback_prob]

    if not generated_domain_pddl or not gt_problems:
        return EvaluationMetrics(
            task_id=task.task_id,
            domain_family=task.domain_family,
            task_type=task.task_type.value,
            agent_type=agent_type,
            is_syntax_valid=False,
            is_solvable=False,
            executability_valid=False,
            feasibility_valid=False,
            interpretability_valid=False,
            semantic_soundness=False,
            e2e_gate_success=False,
            problems_evaluated=max(1, len(gt_problems)),
            problems_passed=0,
            iterations_used=iterations_used,
            execution_time_seconds=round(execution_time_seconds, 2),
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            error_summary="Generation Failed: Incomplete or missing domain/problem PDDL output from agent."
        )

    from nodes.validation import verify_pddl_candidate

    gt_dom_str = getattr(task, "ground_truth_domain_pddl", None) or getattr(task, "initial_domain_pddl", None)

    all_syntax_valid = True
    all_solvable = True
    any_timeout = False
    all_executability = True
    all_feasibility = True
    all_interpretability = True
    problems_passed = 0
    total_search_time = 0.0
    first_verif: Optional[Dict[str, Any]] = None
    first_fail_verif: Optional[Dict[str, Any]] = None
    first_fail_name: str = ""

    for idx, prob_str in enumerate(gt_problems):
        gp_path = gt_gold_plans[idx] if idx < len(gt_gold_plans) and gt_gold_plans[idx] else None
        p_name = gt_prob_names[idx] if idx < len(gt_prob_names) else f"problem_{idx + 1}"
        verif = verify_pddl_candidate(
            generated_domain_pddl=generated_domain_pddl,
            generated_problem_pddl=prob_str,
            ground_truth_domain_pddl=gt_dom_str,
            ground_truth_problem_pddl=prob_str,
            ground_truth_plan_path=gp_path,
            temp_dir=Path(eval_dir),
            tag=f"{task.task_id}_{agent_type}_p{idx + 1}"
        )
        if first_verif is None:
            first_verif = verif

        total_search_time += float(verif.get("search_time_sec", 0.0) or 0.0)
        all_syntax_valid = all_syntax_valid and bool(verif["is_syntax_valid"])
        all_solvable = all_solvable and bool(verif["is_solvable"])
        any_timeout = any_timeout or bool(verif["planner_timeout"])
        all_executability = all_executability and bool(verif["executability_valid"])
        all_feasibility = all_feasibility and bool(verif["feasibility_valid"])
        all_interpretability = all_interpretability and bool(verif["interpretability_valid"])

        if verif["e2e_success"]:
            problems_passed += 1
        elif first_fail_verif is None:
            first_fail_verif = verif
            first_fail_name = p_name

        # Short-circuit remaining instances as soon as any reference problem fails e2e verification
        if not verif["e2e_success"]:
            if not verif["is_syntax_valid"]:
                all_solvable = False
                all_executability = False
                all_feasibility = False
                all_interpretability = False
            break

    semantic_soundness = bool(all_feasibility and all_interpretability)
    e2e_gate_success = bool(
        all_syntax_valid
        and all_solvable
        and all_executability
        and semantic_soundness
        and (problems_passed == len(gt_problems))
    )

    ref_v = first_verif or {}
    plan_length = ref_v.get("plan_length", 0)
    plan_cost = ref_v.get("plan_cost", 0)

    if not e2e_gate_success:
        fv = first_fail_verif or ref_v
        lbl = f"[{first_fail_name} ({problems_passed}/{len(gt_problems)} passed)] " if len(gt_problems) > 1 and first_fail_name else ""
        if not fv.get("is_syntax_valid", False):
            error_summary = error_summary or (lbl + "VAL Syntax Error: " + (fv.get("val_syntax_log", "")[:200]))
        elif not fv.get("is_solvable", False):
            if fv.get("planner_timeout", False):
                error_summary = lbl + "Planner Search Timeout (30s): Unsolvability not proven."
            else:
                error_summary = error_summary or (lbl + "Planner Unsolvability: " + (fv.get("raw_fd_log", "")[:200]))
        elif not fv.get("executability_valid", False):
            error_summary = error_summary or (lbl + "Plan Certification Failed: Generated plan failed VAL on generated domain.")
        elif not fv.get("feasibility_valid", False):
            error_summary = error_summary or (lbl + "Soundness Failed: Generated plan failed VAL on ground-truth domain.")
        elif not fv.get("interpretability_valid", False):
            error_summary = error_summary or (lbl + "Completeness Failed: Ground-truth plan failed VAL on generated domain.")

    top1_element = None
    top1_repair_op = None
    if diagnostic_reports and len(diagnostic_reports) > 0:
        first_rep = diagnostic_reports[0]
        top1_element = getattr(first_rep, "faulty_element", "") if hasattr(first_rep, "faulty_element") else str(first_rep.get("faulty_element", ""))
        top1_repair_op = str(getattr(first_rep, "repair_operation_type", "") if hasattr(first_rep, "repair_operation_type") else first_rep.get("repair_operation_type", ""))

    return EvaluationMetrics(
        task_id=task.task_id,
        domain_family=task.domain_family,
        task_type=task.task_type.value,
        agent_type=agent_type,
        is_syntax_valid=all_syntax_valid,
        is_solvable=all_solvable,
        planner_timeout=any_timeout,
        executability_valid=all_executability,
        feasibility_valid=all_feasibility,
        interpretability_valid=all_interpretability,
        semantic_soundness=semantic_soundness,
        e2e_gate_success=e2e_gate_success,
        problems_evaluated=len(gt_problems),
        problems_passed=problems_passed,
        top1_element=top1_element,
        top1_repair_op=top1_repair_op,
        plan_length=plan_length,
        plan_cost=plan_cost,
        search_time=round(total_search_time, 3),
        iterations_used=iterations_used,
        execution_time_seconds=round(execution_time_seconds, 2),
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        error_summary=error_summary
    )
