"""Unified Validation Node and Verification Pipeline for PDDL Domain Models.

Integrates the canonical tri-criteria semantic verification oracles:
1. Solvability & Internal Consistency (Fast Downward)
2. Forward Feasibility / Soundness (VAL on D_gold with pi_gen)
3. Inverse Interpretability / Completeness (VAL on D_gen with pi_gold) - evaluated independently
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from config.paths import get_temp_dir, get_temp_domain_path, get_temp_problem_path
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness
)


def extract_val_failure_trace(raw_log: str) -> str:
    """Extracts informative failure sections from VAL output."""
    stripped = re.sub(
        r"Type-checking\s+[a-zA-Z0-9_\-]+\s*\.\.\.action passes type checking\.",
        "",
        raw_log or ""
    )
    collapsed = re.sub(r"\s+", " ", stripped).strip()
    for marker in ("Plan failed", "Goal not satisfied", "The goal was not achieved", "Plan Repair Advice", "Plan Transfer Arity Mismatch"):
        idx = collapsed.find(marker)
        if idx != -1:
            start_idx = max(0, idx - 300)
            return collapsed[start_idx:start_idx + 1800]
    return collapsed[-1500:] if len(collapsed) > 1500 else collapsed


def verify_pddl_candidate(
    generated_domain_pddl: str,
    generated_problem_pddl: str,
    ground_truth_domain_pddl: Optional[str] = None,
    ground_truth_problem_pddl: Optional[str] = None,
    ground_truth_plan_path: Optional[str] = None,
    temp_dir: Optional[Path] = None,
    tag: str = "eval"
) -> Dict[str, Any]:
    """
    Verifies generated PDDL candidate against formal oracles (Fast Downward and VAL).
    Crucially evaluates Solvability, Feasibility, and Interpretability independently.
    """
    if not temp_dir:
        temp_dir = get_temp_dir()
    os.makedirs(temp_dir, exist_ok=True)

    eval_dom_file = str(temp_dir / f"eval_{tag}_dom.pddl")
    eval_prob_file = str(temp_dir / f"eval_{tag}_prob.pddl")
    eval_plan_file = str(temp_dir / f"eval_{tag}_plan.txt")
    ref_dom_file = str(temp_dir / f"ref_{tag}_dom.pddl")

    with open(eval_dom_file, "w", encoding="utf-8") as f:
        f.write(generated_domain_pddl or "")
    with open(eval_prob_file, "w", encoding="utf-8") as f:
        f.write(generated_problem_pddl or "")

    has_gt = bool(ground_truth_domain_pddl and ground_truth_domain_pddl.strip())
    if has_gt:
        with open(ref_dom_file, "w", encoding="utf-8") as f:
            f.write(ground_truth_domain_pddl)

    # 1. Syntax & Typing Check (VAL)
    is_syntax_valid, val_syntax_log = run_val_validator(eval_dom_file, eval_prob_file)

    # 2. Solvability & Executability Check (Fast Downward)
    is_solvable = False
    planner_timeout = False
    executability_valid = False
    plan_steps: List[str] = []
    plan_length = 0
    plan_cost = 0
    search_time = 0.0
    raw_fd_log = ""

    if is_syntax_valid:
        fd_res = run_fast_downward_with_plan(
            eval_dom_file,
            eval_prob_file,
            ground_truth_domain_path=None,
            plan_path=eval_plan_file
        )
        is_solvable = fd_res.get("is_solvable", False) or fd_res.get("plan_found", False)
        planner_timeout = bool(fd_res.get("timed_out", False))
        executability_valid = bool(fd_res.get("executability_valid", False) or fd_res.get("val_valid", False))
        plan_steps = fd_res.get("plan_steps", [])
        plan_length = len(plan_steps)
        plan_cost = fd_res.get("plan_cost", 0)
        search_time = fd_res.get("search_time", 0.0)
        raw_fd_log = fd_res.get("raw_fd_log", "")

    # 3. Plan Feasibility (Forward Soundness: VAL(D_gold, P_gold, pi_gen))
    feasibility_valid = False
    feasibility_log = ""
    if is_solvable and executability_valid and has_gt:
        if os.path.exists(eval_plan_file) and os.path.exists(ref_dom_file):
            feasibility_valid, feasibility_log = validate_plan_semantic_soundness(
                ground_truth_domain_path=ref_dom_file,
                problem_path=eval_prob_file,
                plan_path=eval_plan_file,
                generated_domain_path=eval_dom_file
            )

    # 4. Plan Interpretability (Inverse Completeness: VAL(D_gen, P_gold, pi_gold))
    # EVALUATED INDEPENDENTLY of feasibility or solvability of D_gen!
    interpretability_valid = False
    interpretability_log = ""
    if has_gt and is_syntax_valid:
        if ground_truth_plan_path and os.path.exists(ground_truth_plan_path) and os.path.getsize(ground_truth_plan_path) > 0:
            gold_plan_file = ground_truth_plan_path
        else:
            gold_plan_file = str(temp_dir / f"gold_{tag}_plan.txt")
            if os.path.exists(gold_plan_file):
                try:
                    os.remove(gold_plan_file)
                except Exception:
                    pass
            run_fast_downward_with_plan(
                ref_dom_file,
                eval_prob_file,
                ground_truth_domain_path=None,
                plan_path=gold_plan_file
            )
        if os.path.exists(gold_plan_file) and os.path.exists(eval_dom_file) and os.path.getsize(gold_plan_file) > 0:
            interpretability_valid, interpretability_log = validate_plan_semantic_soundness(
                ground_truth_domain_path=eval_dom_file,
                problem_path=eval_prob_file,
                plan_path=gold_plan_file,
                generated_domain_path=ref_dom_file
            )
    elif not has_gt:
        feasibility_valid = executability_valid
        interpretability_valid = executability_valid

    semantic_soundness = bool(feasibility_valid and interpretability_valid)
    e2e_success = bool(is_syntax_valid and is_solvable and executability_valid and semantic_soundness)

    return {
        "is_syntax_valid": is_syntax_valid,
        "syntax_log": val_syntax_log,
        "val_syntax_log": val_syntax_log,
        "is_solvable": is_solvable,
        "planner_timeout": planner_timeout,
        "planner_timed_out": planner_timeout,
        "executability_valid": executability_valid,
        "feasibility_valid": feasibility_valid,
        "feasibility_log": feasibility_log,
        "interpretability_valid": interpretability_valid,
        "interpretability_log": interpretability_log,
        "semantic_soundness": semantic_soundness,
        "e2e_success": e2e_success,
        "plan_steps": plan_steps,
        "plan_length": plan_length,
        "plan_cost": plan_cost,
        "search_time": search_time,
        "search_time_sec": search_time,
        "raw_fd_log": raw_fd_log,
        "plan_text": "\n".join(plan_steps) if plan_steps else "",
        "eval_domain_file": eval_dom_file,
        "eval_problem_file": eval_prob_file,
        "eval_plan_file": eval_plan_file,
    }


def _collect_verification_errors(verif: Dict[str, Any], ref_dom_code: Optional[str], prob_label: str = "") -> List[str]:
    """Builds oracle verification error messages from a single-instance verification dict."""
    errors: List[str] = []
    prefix = f"[{prob_label}] " if prob_label else ""

    if not verif["is_syntax_valid"]:
        errors.append(prefix + "VAL Error: " + verif["syntax_log"])
        return errors

    is_translate_crash = False
    if not verif["is_solvable"]:
        fd_log = verif["raw_fd_log"]
        is_translate_crash = any(
            k in fd_log.lower()
            for k in ["translate exit code: 30", "translate exit code: 31", "undefined variable", "parsing error", "syntax error:"]
        )
        if verif["planner_timed_out"]:
            errors.append(prefix + "Planner Error: " + fd_log)
        elif is_translate_crash:
            errors.append(prefix + "Translator Syntax Error: " + fd_log)
        else:
            errors.append(prefix + "Planner Error: Could not find a plan. " + fd_log)
    else:
        if ref_dom_code and not verif["feasibility_valid"]:
            clean_log = extract_val_failure_trace(verif["feasibility_log"])
            errors.append(
                f"{prefix}Plan Feasibility Rejection on Standard Domain: The synthesized plan solved generated domain D_gen, "
                f"but failed execution when transferred to reference domain D_gold on problem P_gold! "
                f"VAL Oracle Diagnostic Trace: {clean_log}\n"
                f"Actions in D_gen are likely missing necessary preconditions "
                f"or producing effects that violate ground-truth domain invariants."
            )

    if (not is_translate_crash) and ref_dom_code and not verif["interpretability_valid"]:
        clean_interp = extract_val_failure_trace(verif["interpretability_log"])
        errors.append(
            f"{prefix}Plan Interpretability Rejection on Generated Domain: The standard reference plan pi_gold "
            f"failed execution on the generated domain D_gen! "
            f"VAL Oracle Diagnostic Trace: {clean_interp}\n"
            f"Actions in D_gen are likely over-constrained with extraneous preconditions "
            f"or missing required positive effects needed by reference plan operations."
        )

    return errors


def run_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node execution function for formal multi-criteria validation."""
    start_t = time.time()
    pddl_code = state.get("generated_domain_pddl", "")
    if not pddl_code and state.get("initial_domain_pddl"):
        pddl_code = state.get("initial_domain_pddl", "")
        state["generated_domain_pddl"] = pddl_code

    problem_pddl_code = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    if problem_pddl_code:
        state["generated_problem_pddl"] = problem_pddl_code

    # Ensure Domain AST representation exists
    if not state.get("pddl_domain_representation") and pddl_code:
        from nodes.pddl_to_ast_parser import parse_pddl_domain_to_representation
        state["pddl_domain_representation"] = parse_pddl_domain_to_representation(pddl_code)

    ref_dom_code = state.get("reference_domain_pddl") or state.get("ground_truth_domain_pddl")
    gold_plan_file = state.get("gold_reference_plan_file")
    ref_problems: List[str] = state.get("reference_problems") or []
    ref_gold_plans: List[str] = state.get("reference_gold_plans") or []
    ref_prob_names: List[str] = state.get("reference_problem_names") or []

    cur_iter = state.get("iteration_count", 0)
    d_name = state.get("pddl_domain_representation", {}).get("domain_name") or "domain"
    p_hash = abs(hash(problem_pddl_code)) % 100000 if problem_pddl_code else 0
    tag_str = f"{d_name}_{p_hash}_iter_{cur_iter}"

    verif = verify_pddl_candidate(
        generated_domain_pddl=pddl_code,
        generated_problem_pddl=problem_pddl_code,
        ground_truth_domain_pddl=ref_dom_code,
        ground_truth_problem_pddl=problem_pddl_code,
        ground_truth_plan_path=gold_plan_file,
        tag=tag_str
    )

    errors = _collect_verification_errors(verif, ref_dom_code)

    # Multi-problem check: if primary problem passes and a suite of ground-truth problems is provided,
    # verify Soundness and Completeness across all ground-truth problems.
    if not errors and ref_problems:
        for idx, extra_prob in enumerate(ref_problems):
            if not extra_prob or extra_prob.strip() == problem_pddl_code.strip():
                continue
            extra_gp = ref_gold_plans[idx] if idx < len(ref_gold_plans) and ref_gold_plans[idx] else None
            extra_name = ref_prob_names[idx] if idx < len(ref_prob_names) else f"problem_{idx + 1}"
            extra_verif = verify_pddl_candidate(
                generated_domain_pddl=pddl_code,
                generated_problem_pddl=extra_prob,
                ground_truth_domain_pddl=ref_dom_code,
                ground_truth_problem_pddl=extra_prob,
                ground_truth_plan_path=extra_gp,
                tag=f"{tag_str}_p{idx + 1}"
            )
            extra_errors = _collect_verification_errors(extra_verif, ref_dom_code, prob_label=extra_name)
            if extra_errors:
                verif = extra_verif
                errors = extra_errors
                state["initial_problem_pddl"] = extra_prob
                state["generated_problem_pddl"] = extra_prob
                if extra_gp:
                    state["gold_reference_plan_file"] = extra_gp
                break

    trace = {
        "val_ok": bool(verif["is_syntax_valid"]),
        "val_log": verif["syntax_log"],
        "fd_ran": bool(verif["is_syntax_valid"]),
        "fd_ok": bool(verif["is_solvable"]),
        "fd_timed_out": bool(verif["planner_timed_out"]),
        "fd_log": verif["raw_fd_log"],
        "plan_steps": verif["plan_steps"],
        "executability_valid": verif["executability_valid"],
        "feasibility_checked": bool(ref_dom_code and verif["is_solvable"]),
        "feasibility_valid": verif["feasibility_valid"],
        "feasibility_log": verif["feasibility_log"],
        "interpretability_checked": bool(ref_dom_code),
        "interpretability_valid": verif["interpretability_valid"],
        "interpretability_log": verif["interpretability_log"],
    }
    state["oracle_trace"] = trace
    state["generated_plan_result"] = {
        "is_solvable": verif["is_solvable"],
        "timed_out": verif["planner_timed_out"],
        "executability_valid": verif["executability_valid"],
        "feasibility_valid": verif["feasibility_valid"],
        "feasibility_log": verif["feasibility_log"],
        "interpretability_valid": verif["interpretability_valid"],
        "interpretability_log": verif["interpretability_log"],
        "plan_steps": verif["plan_steps"],
        "raw_fd_log": verif["raw_fd_log"],
    }

    print("\n" + "-" * 70, flush=True)
    print(f" [VALIDATION ORACLES - Iteration {cur_iter}]:", flush=True)
    print(f" * Syntax Valid (VAL)    : {verif['is_syntax_valid']}", flush=True)
    if not verif["is_syntax_valid"]:
        clean_syn = verif['syntax_log'].strip().replace('\n', ' ')[:120]
        print(f"   -> Syntax Error        : {clean_syn}", flush=True)
    else:
        print(f" * Plan Solvable (FD)    : {verif['is_solvable']}", flush=True)
        if verif["is_solvable"]:
            print(f" * Plan Length           : {len(verif['plan_steps'])} steps", flush=True)
            print(f" * Executability Valid   : {verif['executability_valid']}", flush=True)
            if ref_dom_code:
                print(f" * Soundness (Feasible)  : {verif['feasibility_valid']}", flush=True)
                print(f" * Completeness (Interp) : {verif['interpretability_valid']}", flush=True)
        else:
            clean_fd = verif['raw_fd_log'].strip().replace('\n', ' ')[:120]
            print(f"   -> Planner Failure     : {clean_fd}", flush=True)
            if ref_dom_code:
                print(f" * Completeness (Interp) : {verif['interpretability_valid']}", flush=True)
    print("-" * 70, flush=True)

    if errors:
        state["verification_errors"] = errors
        if not state.get("initial_verification_errors"):
            state["initial_verification_errors"] = list(errors)
    else:
        state["verification_errors"] = []
        state["diagnostic_reports"] = []
        state["formatted_diagnostic_feedback"] = ""

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["validate"] = round(latencies.get("validate", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies
    return state
