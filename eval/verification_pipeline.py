"""Canonical re-export from nodes.validation for unified verification."""

from nodes.validation import (
    PRICE_PROMPT_PER_M,
    PRICE_COMPLETION_PER_M,
    calculate_llm_cost,
    extract_val_failure_trace,
    verify_pddl_candidate,
    run_validation_node,
)

def extract_hmgfl_diagnostics(
    diagnostic_reports = None,
    gold_fault_element = None
):
    """Extracts fault elements and repair operations from diagnostic reports."""
    res = {
        "top1_element": "NONE",
        "top1_repair_op": "NONE",
        "all_elements": [],
        "all_repair_ops": []
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
    return res


def classify_behavioral_outcome(
    is_syntax_valid: bool,
    is_solvable: bool,
    executability_valid: bool,
    feasibility_valid: bool,
    interpretability_valid: bool,
    macro_f1: float = 0.0,
    iters: int = 1,
    max_retries: int = 5,
    planner_timed_out: bool = False
):
    """Classifies domain generation/repair outcome into standardized defect/success taxonomy."""
    if not is_syntax_valid:
        return "SYNTAX_ERROR", "A.1_SYNTACTIC_INVALIDITY"
    if planner_timed_out:
        return "PLANNER_TIMEOUT", "A.2_SEARCH_BUDGET_EXHAUSTED"
    if not is_solvable:
        return "UNSOLVABLE", "B_CAUSAL_UNSOLVABILITY"
    if not executability_valid:
        return "EXEC_FAILURE", "C_INTERNAL_INCONSISTENCY"
    if not feasibility_valid:
        return "INFEASIBLE", "D_FORWARD_UNSOUNDNESS"
    if not interpretability_valid:
        return "UNINTERPRETABLE", "E_INVERSE_INCOMPLETENESS"
    if iters > 1:
        return "REPAIRED_PASS", "F_REPAIRED_SUCCESS"
    return "ZERO_SHOT_PASS", "G_IMMEDIATE_SUCCESS"

