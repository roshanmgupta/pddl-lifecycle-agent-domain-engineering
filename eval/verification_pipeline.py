"""
eval/verification_pipeline.py
Canonical, literature-grounded verification pipeline for PDDL domain synthesis, repair, and evolution.
Derives from Classical PDDL 2.1 Formal Semantics (Fox & Long 2003) and Symbolic Oracles (VAL + Fast Downward).

Eliminates code duplication across benchmark runners by providing unified functions for:
- Multi-Stage Decoupled Verification (SVR -> Solvability -> Executability -> Feasibility -> Interpretability -> E2E)
- Hierarchical Multi-Granular Fault Localization (H-MGFL) extraction (Level 1 AST & Level 2 Causal Components)
- Literature-Grounded Behavioral Outcome Classification (A.1 to G)
- LLM Token Cost Accounting
"""

import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from config.paths import get_temp_dir
from eval.action_reconstruction import evaluate_action_reconstruction
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness
)

# OpenRouter / OpenAI Pricing (gpt-4o-mini: $0.15 / $0.60 per 1M tokens)
PRICE_PROMPT_PER_M = 0.15
PRICE_COMPLETION_PER_M = 0.60

def calculate_llm_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Calculates LLM query cost in USD based on standard benchmark rates."""
    return round(
        (prompt_tokens * PRICE_PROMPT_PER_M / 1_000_000) +
        (completion_tokens * PRICE_COMPLETION_PER_M / 1_000_000), 
        6
    )

def extract_hmgfl_diagnostics(
    diagnostic_reports: Optional[List[Any]],
    gold_fault_element: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts Hierarchical Multi-Granular Fault Localization (H-MGFL) metrics from diagnostic reports:
    - Level 1: AST Element Granularity (Action Schemas, Type Hierarchy, Global Predicates)
    - Level 2: Causal Component Granularity (Repair Operation Types)
    - Formal ranking metrics: Top-1 Accuracy, Top-3 Accuracy, and Mean Reciprocal Rank (MRR).
    """
    res = {
        "top1_element": "NONE",
        "top1_repair_op": "NONE",
        "all_elements": [],
        "all_repair_ops": [],
        "fla_top1": False,
        "fla_top3": False,
        "fla_mrr": 0.0,
        "fla_correct": False
    }

    if not diagnostic_reports:
        return res

    elems = []
    ops = []
    for r in diagnostic_reports:
        elem = getattr(r, "faulty_element", "") if hasattr(r, "faulty_element") else str(r.get("faulty_element", "") if isinstance(r, dict) else "")
        op = getattr(r, "repair_operation_type", "") if hasattr(r, "repair_operation_type") else str(r.get("repair_operation_type", "") if isinstance(r, dict) else "")
        if elem and str(elem).strip():
            elems.append(str(elem).strip())
        if op and str(op).strip():
            ops.append(str(op).strip())

    res["all_elements"] = elems
    res["all_repair_ops"] = ops
    res["top1_element"] = elems[0] if elems else "NONE"
    res["top1_repair_op"] = ops[0] if ops else "NONE"

    if gold_fault_element and elems:
        g_clean = gold_fault_element.lower().replace("-", "").replace("_", "")
        clean_candidates = [
            re.sub(r"^(domain\.)?actions?\.", "", e, flags=re.IGNORECASE).lower().replace("-", "").replace("_", "")
            for e in elems
        ]

        def _match_elem(g: str, cand: str) -> bool:
            return bool(cand and (g == cand or g in cand or cand in g))

        res["fla_top1"] = _match_elem(g_clean, clean_candidates[0])
        res["fla_top3"] = any(_match_elem(g_clean, c) for c in clean_candidates[:3])
        for idx, c in enumerate(clean_candidates):
            if _match_elem(g_clean, c):
                res["fla_mrr"] = round(1.0 / (idx + 1), 4)
                break
        res["fla_correct"] = res["fla_top1"] or res["fla_top3"]

    return res

def classify_behavioral_outcome(
    is_syntax_valid: bool,
    is_solvable: bool,
    executability_valid: bool,
    feasibility_valid: bool,
    interpretability_valid: bool,
    macro_f1: float,
    iters: int,
    max_retries: int = 5,
    planner_timed_out: bool = False
) -> Tuple[str, str]:
    """
    Classifies benchmark results into canonical behavioral outcome codes (A.1 to G)
    and underlying defect classes conforming to literature (Chen et al. 2024; Lin et al. AAAI 2023).
    """
    is_sound = (feasibility_valid is True) and (interpretability_valid is True)
    e2e_ok = is_syntax_valid and is_solvable and executability_valid and is_sound

    if e2e_ok:
        if iters <= 1:
            return "A.1: First-Attempt Direct Success", "NONE"
        else:
            return "A.2: Refined Success via Feedback Loops", "RECOVERED"

    if not is_syntax_valid:
        return "B: Unparseable PDDL Syntax Failure", "SYNTAX_PARSE_ERROR"

    if is_syntax_valid and not is_solvable and planner_timed_out:
        return "C.T: Syntactically Valid but Planner Search Timeout (Unsolvability Not Proven)", "PLANNER_SEARCH_TIMEOUT"

    if is_syntax_valid and not is_solvable:
        return "C: Syntactically Valid but Planner Deadlock (Unsolvable)", "CAUSAL_REACHABILITY_DEADLOCK"

    if is_solvable and not executability_valid:
        return "D: Plan Generated but Fails VAL Executability Self-Certification", "ACTION_EFFECT_CONTRADICTION"

    if not feasibility_valid:
        return "E.1: Plan Feasibility Rejection on Standard Domain (Soundness Failure)", "PRECONDITION_MISALIGNMENT"

    if not interpretability_valid:
        return "E.2: Standard Plan Interpretability Rejection on Generated Domain (Completeness Failure)", "PRECONDITION_OVERCONSTRAINED"

    if iters >= max_retries:
        return "F: Iteration Budget Exhausted (Oscillation)", "UNRESOLVED_CONTRADICTION"

    return "G: Diagnostic Anomaly", "OTHER"

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
    Executes the Decoupled Multi-Stage Verification Pipeline across symbolic oracles:
      Stage 1: Syntactic Conformance (SVR)
      Stage 2a: Planner Solvability (PSR) & Timeouts
      Stage 2b: Internal Plan Executability (Self-Consistency)
      Stage 3a: Forward Soundness (Feasibility on D_gold)
      Stage 3b: Inverse Completeness (Interpretability of pi_gold on D_gen)
      Stage 3c: Strict Semantic Soundness
      Stage 4: Structural AST Reconstruction Conformance (ARE & Component F1s)
      Overall: Strict E2E Gate
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

    # Stage 1: VAL Syntax & Typing Parser (SVR)
    is_syntax_valid, val_syntax_log = run_val_validator(eval_dom_file, eval_prob_file)

    # Stage 2: Fast Downward Solvability & Internal Plan Executability
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

    # Stage 3: Semantic Transfer Soundness & Completeness
    feasibility_valid = False
    feasibility_log = ""
    interpretability_valid = False
    interpretability_log = ""

    if is_solvable and executability_valid and has_gt:
        # 3a. Forward Soundness: VAL(D_gold, P_gold, pi_gen)
        if os.path.exists(eval_plan_file) and os.path.exists(ref_dom_file):
            feasibility_valid, feasibility_log = validate_plan_semantic_soundness(
                ground_truth_domain_path=ref_dom_file,
                problem_path=eval_prob_file,
                plan_path=eval_plan_file,
                generated_domain_path=eval_dom_file
            )

        # 3b. Inverse Completeness: VAL(D_gen, P_gold, pi_gold)
        gold_plan_file = ground_truth_plan_path or str(temp_dir / f"gold_{tag}_plan.txt")
        if not os.path.exists(gold_plan_file) or os.path.getsize(gold_plan_file) == 0:
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
        # In pure unreferenced evaluation, internal self-consistency is certified
        feasibility_valid = executability_valid
        interpretability_valid = executability_valid

    semantic_soundness = bool(feasibility_valid and interpretability_valid)
    e2e_success = bool(is_syntax_valid and is_solvable and executability_valid and semantic_soundness)

    # Stage 4: Kuhn-Munkres AST Operator Reconstruction Alignment
    macro_f1 = 0.0
    pre_f1 = 0.0
    add_f1 = 0.0
    del_f1 = 0.0
    action_f1 = 0.0
    param_arity_match = 1.0 if not generated_domain_pddl else 0.0
    action_map = {}

    if has_gt and generated_domain_pddl:
        are_res = evaluate_action_reconstruction(ground_truth_domain_pddl, generated_domain_pddl)
        macro_f1 = are_res.get("macro_structural_f1", 0.0)
        pre_f1 = are_res.get("mean_precondition_f1", 0.0)
        add_f1 = are_res.get("mean_add_effect_f1", 0.0)
        del_f1 = are_res.get("mean_delete_effect_f1", 0.0)
        action_f1 = are_res.get("action_f1", 0.0)
        param_arity_match = are_res.get("mean_arity_match", 0.0)
        action_map = are_res.get("action_mapping", {})

    return {
        "is_syntax_valid": is_syntax_valid,
        "is_solvable": is_solvable,
        "planner_timeout": planner_timeout,
        "executability_valid": executability_valid,
        "feasibility_valid": feasibility_valid,
        "interpretability_valid": interpretability_valid,
        "semantic_soundness": semantic_soundness,
        "e2e_success": e2e_success,
        "macro_structural_f1": macro_f1,
        "precondition_f1": pre_f1,
        "add_effect_f1": add_f1,
        "delete_effect_f1": del_f1,
        "action_f1": action_f1,
        "parameter_arity_match": param_arity_match,
        "action_mapping": action_map,
        "plan_steps": plan_steps,
        "plan_length": plan_length,
        "plan_cost": plan_cost,
        "search_time_sec": search_time,
        "val_syntax_log": val_syntax_log,
        "raw_fd_log": raw_fd_log,
        "feasibility_log": feasibility_log,
        "interpretability_log": interpretability_log,
        "plan_text": "\n".join(plan_steps) if plan_steps else ""
    }
