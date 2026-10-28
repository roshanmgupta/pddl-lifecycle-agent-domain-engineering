import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from schemas.pddl_blueprint import DiagnosticReport, ErrorCategory, RepairOperationType
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES, STANDARD_DIAGNOSTIC_RULES
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from tools.causal_fault_analyzer import run_causal_fault_analysis, normalize_atom_expression
from tools.blueprint_parser import extract_pddl_problem_metadata

class DiagnosticAnalysis(BaseModel):
    """Container for structured diagnostic reports produced by the Diagnostic LLM Agent."""
    reports: List[DiagnosticReport] = Field(
        default_factory=list,
        description="Ranked list of diagnostic reports localizing faults and suggesting repair operations"
    )

def check_system_oracle_binary_availability(raw_log: str, oracle_name: str) -> Optional[DiagnosticReport]:
    """
    Checks if an oracle error is caused by a missing system binary (VAL or Fast Downward)
    rather than a domain modeling defect.
    """
    log_lower = raw_log.lower()
    binary_missing = (
        "binary not found" in log_lower
        or "executable not found" in log_lower
        or "failed to execute val binary" in log_lower
        or "failed to execute fast downward" in log_lower
        or "cannot find the file specified" in log_lower
        or ("not found at" in log_lower and ("val" in log_lower or "downward" in log_lower))
    )
    if binary_missing:
        binary_label = "VAL Oracle Binary" if oracle_name == "VAL" else "Fast Downward Binary"
        hint = (
            "Ensure VAL executable path is properly configured via 'VAL_PATH' in your .env file or available on system PATH."
            if oracle_name == "VAL"
            else "Ensure Fast Downward path is properly configured via 'FAST_DOWNWARD_PATH' in your .env file or available on system PATH."
        )
        return DiagnosticReport(
            error_category=ErrorCategory.SYSTEM_ORACLE_ERROR,
            repair_operation_type=RepairOperationType.GENERAL_AST_REPAIR,
            faulty_element=binary_label,
            raw_log=raw_log.strip()[:300],
            suggested_repair_hint=hint
        )
    return None

def parse_val_log(val_log: str) -> List[DiagnosticReport]:
    """Backward-compatible wrapper checking VAL binary availability."""
    rep = check_system_oracle_binary_availability(val_log, "VAL")
    return [rep] if rep else []

def parse_fast_downward_log(fd_log: str, causal_analysis: Optional[Dict[str, Any]] = None) -> List[DiagnosticReport]:
    """Backward-compatible wrapper checking Fast Downward binary availability."""
    rep = check_system_oracle_binary_availability(fd_log, "Fast Downward")
    return [rep] if rep else []

def compute_layered_fault_priority(report: DiagnosticReport) -> Tuple[int, int]:
    """
    Computes (tier_level, sub_rank) for a DiagnosticReport based on the Layered Model-Based Fault Localization Hierarchy (Lin, Grastien, & Bercher AAAI 2023).
    Lower tier_level indicates strictly higher priority:
      Tier 0: Syntax, Type Hierarchy, Signature Arity, Undeclared Constants (Blocks Grounding)
      Tier 1: Static / Seed Initial State Ungroundability (Blocks Step 0 Transitions)
      Tier 2: Goal Relevance, Goal Producers, Causal Parameter Aliasing (Blocks Goal Path)
      Tier 3: Dynamic Mutex, Absorbing State Lockout, Irreversible Depletion (Blocks Search Convergence)
      Tier 4: General Precondition Relaxation & Effect Tuning
    """
    raw = (str(report.raw_log) + " " + str(report.suggested_repair_hint)).lower()
    cat = str(report.error_category).lower()
    op = str(report.repair_operation_type).lower()
    elem = str(report.faulty_element).lower()

    # Tier 0: Type hierarchy, signature arity, syntax, undeclared types/predicates/constants
    if (
        "syntax" in cat 
        or "type_signature" in cat 
        or "unknown type" in raw 
        or "arity mismatch" in raw 
        or "type problem" in raw
        or elem in ("types", "predicates")
        or "undeclared" in raw
        or "not found" in raw
        or "missing" in raw
    ):
        return (0, 0)
    if "type_arity_alignment" in op and ("types" in elem or "predicates" in elem or "mismatch" in raw):
        return (0, 1)

    # Tier 1: Static / Initial Seed Grounding Deadlocks (Zero facts in init)
    if (
        "zero matching facts in p_gold :init" in raw 
        or "zero facts in p_gold :init" in raw 
        or "requires argument types" in raw
        or "empty parameter domain" in raw
        or "unreachable: predicate" in raw
    ):
        return (1, 0)
    if "grounding_unsolvability" in cat and "goal" not in raw:
        return (1, 1)

    # Tier 2: Goal Reachability, Missing Goal Producers, Parameter Aliasing on Goals
    if (
        "goal" in raw and (
            "unproduced" in raw 
            or "not produced" in raw 
            or "unreachable" in raw 
            or "orphan" in raw
            or "co-indexed" in raw
            or "aliased" in raw
        )
    ):
        return (2, 0)

    # Tier 3: Absorbing Lockout, Irreversible Depletion, Contradictory Effects, Mutex
    if (
        "absorbing" in raw 
        or "irreversible" in raw 
        or "contradictory" in raw 
        or "lockout" in raw
        or "simultaneously adds" in raw
    ):
        return (3, 0)

    # Tier 4: General Precondition / Effect Alignment
    return (4, 0)

def prioritize_diagnostic_reports(reports: List[DiagnosticReport], max_items: int = 4) -> Tuple[List[DiagnosticReport], int]:
    """
    Selects the highest-priority causal tier of reports up to max_items.
    Prevents cognitive overload and attention fragmentation in the LLM repair agent.
    Returns (prioritized_reports, active_tier).
    """
    if not reports:
        return [], 0

    # Monotonicity of Reachability filter:
    # In classical planning, adding new preconditions to actions when a planner failed with unsolvability/deadlock
    # strictly reduces the reachable state space and cannot resolve reachability failures.
    filtered_reports = []
    for r in reports:
        raw_r = (str(r.raw_log) + " " + str(r.suggested_repair_hint)).lower()
        if r.repair_operation_type == RepairOperationType.PRECONDITION_INSERTION and ("could not find a plan" in raw_r or "unsolvable" in raw_r or "deadlock" in raw_r):
            continue

        # First-Order Schema Invariant: In Classical PDDL, action schemas are parameterized over variables (?var)
        # or declared domain constants. If a report proposes inserting a precondition or effect containing ONLY
        # concrete problem-instance objects without any parameterized schema variable (?var), reject it.
        if r.repair_operation_type in (RepairOperationType.PRECONDITION_INSERTION, RepairOperationType.EFFECT_ALIGNMENT):
            hint_str = str(r.suggested_repair_hint)
            has_schema_atom = bool(re.search(r"\([a-zA-Z0-9_\-]+(?:\s+\?[a-zA-Z0-9_\-]+)+\)", hint_str))
            if not has_schema_atom and re.search(r"'\([a-zA-Z0-9_\-]+(?:\s+[a-zA-Z0-9_\-]+)+\)'", hint_str):
                continue

        filtered_reports.append(r)
    reports = filtered_reports or reports

    scored = [(compute_layered_fault_priority(r), idx, r) for idx, r in enumerate(reports)]
    scored.sort(key=lambda x: (x[0], x[1]))
    min_tier = scored[0][0][0]
    selected = [r for _, _, r in scored[:max_items]]
    return selected, min_tier

def format_diagnostic_feedback(reports: List[DiagnosticReport], active_tier: Optional[int] = None) -> str:
    """
    Formats structured DiagnosticReports into a clear, literature-grounded feedback block
    (following Smirnov et al. 2024; Chen et al. 2024):
    [ERROR TYPE], [TARGET AST OPERATION], [LOCATION], and [SUGGESTION FOR REPAIR].
    """
    if not reports:
        return ""
        
    tier_desc = {
        0: "Tier 0 (Type Hierarchy & Formal AST Well-Formedness)",
        1: "Tier 1 (Initial State Groundability & Seed Precondition Invariants)",
        2: "Tier 2 (Goal Producer Reachability & Causal Parameter Alignment)",
        3: "Tier 3 (State Transition Mutex & Absorbing Lockout Restorations)",
        4: "Tier 4 (Precondition & Effect Refinements)"
    }
    t_str = tier_desc.get(active_tier, f"Tier {active_tier}") if active_tier is not None else "Root Causal Blockers"

    feedback_lines = [
        f"### Diagnostic Failure Analysis Report (Layered Model-Based Fault Localization Priority: {t_str}):",
        f"CRITICAL GUIDANCE: To prevent cascading regressions across operators, focus repairs strictly on resolving these top-priority causal blockers before modifying unrelated actions.\n"
    ]
    for idx, report in enumerate(reports, 1):
        cat = report.error_category.value if hasattr(report.error_category, "value") else str(report.error_category)
        op = report.repair_operation_type.value if hasattr(report.repair_operation_type, "value") else str(report.repair_operation_type)
        feedback_lines.append(f"\nIssue #{idx}:")
        feedback_lines.append(f"  - [ERROR TYPE]: {cat}")
        feedback_lines.append(f"  - [TARGET AST OPERATION]: {op}")
        if report.faulty_element:
            feedback_lines.append(f"  - [LOCATION / COMPONENT]: {report.faulty_element}")
        feedback_lines.append(f"  - [DESCRIPTION / RAW TRACE]: {report.raw_log}")
        feedback_lines.append(f"  - [SUGGESTION FOR REPAIR]: {report.suggested_repair_hint}")
        
    return "\n".join(feedback_lines)

def is_subtype(child: str, parent: str, types_map: dict) -> bool:
    """Checks whether child inherits directly or indirectly from parent in the type hierarchy."""
    if not child or not parent or not types_map or not isinstance(types_map, dict):
        return False
    norm_types = {str(k).strip().lower(): str(v).strip().lower() if v else "object" for k, v in types_map.items()}
    curr = str(child).strip().lower()
    target = str(parent).strip().lower()
    if curr == target or target == "object":
        return True
    seen = set()
    while curr and curr in norm_types and curr not in seen:
        seen.add(curr)
        p_str = norm_types[curr]
        if not p_str:
            break
        if p_str == target:
            return True
        curr = p_str
    return False

def FaultLocalizationNode(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 3.1 Layered Model-Based Fault Localization Node: Invokes the Diagnostic LLM Agent to reason about oracle failures,
    localize faulty actions/predicates, and generate structured DiagnosticReports (Lin, Grastien, & Bercher AAAI 2023).
    """
    start_t = time.time()
    raw_errors = state.get("verification_errors", [])
    
    if not raw_errors:
        state["diagnostic_reports"] = []
        state["formatted_diagnostic_feedback"] = ""
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    if state.get("skip_fault_localization"):
        raw_msg = "\n".join(raw_errors)
        state["diagnostic_reports"] = []
        state["formatted_diagnostic_feedback"] = "Raw Oracle Verification Errors (Unstructured Feedback):\n" + raw_msg
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    # Pre-flight Check: Detect instant System Oracle / Executable binary errors
    system_reports: List[DiagnosticReport] = []
    for err in raw_errors:
        err_lower = err.lower()
        if "binary not found" in err_lower or "failed to execute" in err_lower or "system warning" in err_lower:
            if err.startswith("VAL Error:"):
                rep = check_system_oracle_binary_availability(err[len("VAL Error:"):].strip(), "VAL")
                if rep:
                    system_reports.append(rep)
            elif err.startswith("Planner Error:"):
                rep = check_system_oracle_binary_availability(err[len("Planner Error:"):].strip(), "Fast Downward")
                if rep:
                    system_reports.append(rep)

    if any(r.error_category == ErrorCategory.SYSTEM_ORACLE_ERROR for r in system_reports):
        print("[FaultLocalizationNode]: Detected System Oracle executable binary issue. Bypassing LLM fault localization.")
        dumped_reports = [r.model_dump() for r in system_reports]
        state["diagnostic_reports"] = dumped_reports
        state["formatted_diagnostic_feedback"] = format_diagnostic_feedback(system_reports)
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    # Phase 4 Solvability Preservation (Regression) Check:
    # If errors originate from Phase 4 Maintenance suite verification across historical benchmark instances (Pi_ref),
    # the symbolic oracles (VAL / Fast Downward) have already concretely isolated the exact breaking predicate,
    # arity, or reachability deadlock on the historical problems.
    is_regression_breakage = any("[SOLVABILITY_PRESERVATION_BREAKAGE]" in str(err) for err in raw_errors)
    existing_reports = state.get("diagnostic_reports", [])
    has_existing_regression_reports = any(
        (getattr(r, "error_category", None) == ErrorCategory.HISTORICAL_REGRESSION
         or (isinstance(r, dict) and r.get("error_category") in ("HISTORICAL_REGRESSION", ErrorCategory.HISTORICAL_REGRESSION)))
        for r in existing_reports
    )

    if is_regression_breakage and has_existing_regression_reports:
        print("[FaultLocalizationNode]: Detected Phase 4 Solvability Preservation regression directly from Maintenance oracles.")
        norm_reports = []
        for r in existing_reports:
            if isinstance(r, DiagnosticReport):
                norm_reports.append(r)
            elif isinstance(r, dict):
                norm_reports.append(DiagnosticReport(**r))
        prioritized_reports, active_tier = prioritize_diagnostic_reports(norm_reports, max_items=4)
        dumped_prioritized = [r.model_dump() for r in prioritized_reports]
        state["diagnostic_reports"] = dumped_prioritized
        state["formatted_diagnostic_feedback"] = format_diagnostic_feedback(prioritized_reports, active_tier)

        hist_reports = state.get("historical_diagnostic_reports", [])
        for dr in dumped_prioritized:
            if dr not in hist_reports:
                hist_reports.append(dr)
        state["historical_diagnostic_reports"] = hist_reports

        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    domain_bp = state.get("pddl_domain_blueprint", {})
    if (not domain_bp or not domain_bp.get("actions")) and state.get("generated_domain_pddl"):
        from tools.blueprint_parser import parse_pddl_domain_to_blueprint
        domain_bp = parse_pddl_domain_to_blueprint(state["generated_domain_pddl"])
        state["pddl_domain_blueprint"] = domain_bp
    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if problem_pddl else {}
    requirements_text = state.get("requirements", "")
    error_traces_str = "\n".join(raw_errors)

    # print("\n" + "=" * 75)
    # print("[FaultLocalizationNode]: Raw Oracle Feedback Received for Fault Localization Analysis:")
    # print(error_traces_str.strip()[:1500])
    # print("=" * 75 + "\n", flush=True)

    # Classical Action-Predicate Causal Dependency Graph & Reachability Fault Analysis
    causal_analysis = run_causal_fault_analysis(
        domain_bp,
        problem_pddl,
        raw_errors,
        state.get("historical_test_results", [])
    )
    state["causal_graph_analysis"] = causal_analysis
    causal_summary = causal_analysis.get("diagnostic_summary", "")

    val_syntax_or_type_error = any("VAL Error:" in err or "Translator Syntax Error:" in err for err in raw_errors)
    focus_guidance = ""
    if val_syntax_or_type_error:
        val_type_diagnostics = []
        type_mismatch_entries = []
        unknown_type_entries = []
        current_val_action = None
        for err in raw_errors:
            # Check multi-line Fast Downward translator syntax errors
            m_undef_multi = re.search(r"Undefined variable\s+Got:\s*(\?[a-zA-Z0-9_\-]+)", err, re.DOTALL)
            if m_undef_multi:
                undef_var = m_undef_multi.group(1)
                m_act_fd = re.search(r"Parsing action '([a-zA-Z0-9_\-]+)'", err)
                act_hint = m_act_fd.group(1) if m_act_fd else current_val_action
                target_act_hint = f"In action '{act_hint}'" if act_hint else "In the action schema using it"
                val_type_diagnostics.append(
                    f"  * Fast Downward Translator Error: 'Undefined variable Got: {undef_var}'.\n"
                    f"    CRITICAL ROOT CAUSE: {target_act_hint}, variable '{undef_var}' is referenced in preconditions/effects but is not declared in :parameters.\n"
                    f"    MANDATORY REPAIR ACTION: {target_act_hint}, add parameter '{undef_var}': 'object' (or its appropriate declared type) to its parameters."
                )

            for line in err.splitlines():
                if "...action passes type checking" in line or "Type-checking initial state" in line or "Type-checking goal state" in line or "Type problem in problem specification" in line:
                    current_val_action = None
                m_act = re.search(r"Type-checking\s+([a-zA-Z0-9_\-]+)", line) or re.search(r"Parsing action '([a-zA-Z0-9_\-]+)'", line)
                if m_act:
                    current_val_action = m_act.group(1)

                m_pred_nf = re.search(r"Predicate\s+([a-zA-Z0-9_\-]+)\s+not found", line)
                if m_pred_nf:
                    missing_pred = m_pred_nf.group(1)
                    val_type_diagnostics.append(
                        f"  * VAL Error: 'Predicate {missing_pred} not found'.\n"
                        f"    CRITICAL ROOT CAUSE: The fixed problem instance (P_gold) or an action schema uses predicate '{missing_pred}', but '{missing_pred}' is missing from domain 'predicates'.\n"
                        f"    MANDATORY REPAIR ACTION: In domain 'predicates', declare predicate '({missing_pred} ...)' with its typed parameter signature matching its arguments in P_gold ':init'/':goal' and domain 'actions' (do NOT modify P_gold)."
                    )

                m_arity = re.search(r"Problem with proposition\s*\(([a-zA-Z0-9_\-]+).*?\)\s*-\s*too\s+(few|many)\s+parameters", line)
                if m_arity:
                    pred_sym = m_arity.group(1)
                    arity_issue = m_arity.group(2)
                    exact_prob_facts = [
                        normalize_atom_expression(a)[0].strip("() ").split()
                        for a in (prob_meta.get("initial_state", []) + prob_meta.get("goal_state", []))
                        if normalize_atom_expression(a)[0].strip("() ").split() and normalize_atom_expression(a)[0].strip("() ").split()[0].lower() == pred_sym.lower()
                    ]
                    if exact_prob_facts:
                        expected_arity = len(exact_prob_facts[0]) - 1
                        prob_args = exact_prob_facts[0][1:]
                        sample_usage = f"({pred_sym}" + (" " + " ".join(prob_args) if expected_arity > 0 else "") + ")"
                        val_type_diagnostics.append(
                            f"  * VAL Error: 'Problem with proposition ({pred_sym}) - too {arity_issue} parameters'.\n"
                            f"    CRITICAL ROOT CAUSE: In P_gold ':init'/':goal', predicate '{pred_sym}' is used with exactly {expected_arity} parameter(s) (e.g. '{sample_usage}'), but was declared in domain 'predicates' with a different parameter count.\n"
                            f"    MANDATORY REPAIR ACTION: In domain 'predicates', declare '({pred_sym} ...)' with exactly {expected_arity} parameter(s) matching '{sample_usage}'. In all domain 'actions', use '{pred_sym}' with exactly {expected_arity} argument(s). Do NOT modify P_gold."
                        )
                        first_arg = prob_args[0] if prob_args else ""
                        first_arg_type = prob_meta.get("objects", {}).get(first_arg, "object") if first_arg else "object"
                        type_mismatch_entries.append({
                            "pred_name": pred_sym,
                            "args": prob_args,
                            "faulty_arg": first_arg,
                            "arg_type": first_arg_type,
                            "expected_type": "object",
                            "current_parent": "object",
                            "param_idx": 0,
                            "declared_param_count": 0,
                            "is_arity_mismatch": True,
                            "current_val_action": None,
                            "raw_log": line.strip()
                        })
                    else:
                        val_type_diagnostics.append(
                            f"  * VAL Error: 'Problem with proposition ({pred_sym}) - too {arity_issue} parameters'.\n"
                            f"    CRITICAL ROOT CAUSE: Predicate '{pred_sym}' is declared in domain 'predicates' with an arity that does not match its usage in the problem instance (P_gold).\n"
                            f"    MANDATORY REPAIR ACTION: Check P_gold ':init' / ':goal' facts for '{pred_sym}' and align predicate '({pred_sym} ...)' in domain 'predicates' and all domain 'actions' to match the exact parameter count and types in P_gold."
                        )

                m_unk = re.search(r"Object with unknown type:\s*([a-zA-Z0-9_\-]+)", line)
                if m_unk:
                    unk_symbol = m_unk.group(1)
                    dom_constants = domain_bp.get("constants", {}) if isinstance(domain_bp, dict) else {}
                    prob_objects = prob_meta.get("objects", {})
                    obj_types_set = set(prob_objects.values())

                    act_params = {}
                    for a in domain_bp.get("actions", []) if isinstance(domain_bp, dict) else []:
                        if a.get("action_name") == current_val_action or a.get("name") == current_val_action:
                            act_params = a.get("parameters", {})
                            break
                    param_types = set(act_params.values()) if isinstance(act_params, dict) else set()

                    if unk_symbol == "object":
                        hint = (
                            "VAL Error: 'Object with unknown type: object'. 'object' is the universal root type in Classical PDDL 2.1. "
                            "Ensure all types in domain 'types' inherit directly or indirectly from 'object'. Do NOT declare 'object' as a child of another type or declare 'object: object'."
                        )
                        target_elem = "types"
                    elif current_val_action:
                        if unk_symbol in dom_constants:
                            hint = (
                                f"Constant '{unk_symbol}' in domain 'constants' is missing a valid type in domain 'types'. "
                                f"In domain 'constants', declare '{unk_symbol}: <type>' and ensure '<type>' is declared in domain 'types'."
                            )
                            target_elem = "constants"
                        elif unk_symbol in param_types:
                            if unk_symbol in obj_types_set:
                                hint = (
                                    f"Action '{current_val_action}' parameter requires type '{unk_symbol}', which exists in fixed problem ':objects' but is missing from domain 'types'. "
                                    f"In domain 'types', declare '{unk_symbol}': 'object' (or its appropriate supertype)."
                                )
                                target_elem = "types"
                            else:
                                hint = (
                                    f"Action '{current_val_action}' declares a parameter with unknown type '{unk_symbol}', which has ZERO objects in fixed problem ':objects'. "
                                    f"Either declare '{unk_symbol}' as a supertype of the relevant object types in domain 'types' if specified by the requirements, or replace/remove parameter '?p - {unk_symbol}' in action '{current_val_action}'."
                                )
                                target_elem = current_val_action or "types"
                        else:
                            hint = (
                                f"Symbol '{unk_symbol}' referenced in domain action '{current_val_action}' is treated as an undeclared constant. "
                                f"Either: 1) Declare '{unk_symbol}: <type>' in domain 'constants', "
                                f"2) Declare it as a '?var' action parameter in '{current_val_action}', or "
                                f"3) Model the condition as a state predicate over existing action parameters."
                            )
                            target_elem = current_val_action
                    else:
                        if unk_symbol in obj_types_set:
                            hint = (
                                f"Type '{unk_symbol}' used in fixed problem ':objects' is missing from domain 'types'. "
                                f"In domain 'types', declare '{unk_symbol}': 'object' (or its appropriate parent supertype)."
                            )
                            target_elem = "types"
                        else:
                            hint = (
                                f"Unbound constant symbol '{unk_symbol}' used in fixed problem ':init' or ':goal' is missing from domain 'constants'. "
                                f"In domain 'constants', declare '{unk_symbol}: <type>' with its appropriate domain type."
                            )
                            target_elem = "constants"

                    unknown_type_entries.append({
                        "action_name": current_val_action,
                        "unknown_symbol": unk_symbol,
                        "target_element": target_elem,
                        "hint": hint,
                        "raw_log": line.strip()
                    })
                    val_type_diagnostics.append(f"  * {hint}")

                m_arity = re.search(r"Type problem with proposition \(([a-zA-Z0-9_\-]+)[^)]*\)\s*-\s*too\s+(few|many)\s+parameters", line, re.IGNORECASE)
                if m_arity:
                    pred_name = m_arity.group(1)
                    problem_kind = m_arity.group(2).lower()
                    decl_str = ""
                    for p_decl in domain_bp.get("predicates", []):
                        clean_p = str(p_decl).strip('() ')
                        toks = clean_p.split()
                        if toks and toks[0] == pred_name:
                            decl_str = f"'{p_decl}'"
                            break
                    val_type_diagnostics.append(
                        f"  * Proposition in action '{current_val_action or 'problem_state'}' uses predicate '{pred_name}' with too {problem_kind} arguments compared to its declared signature {decl_str or f'for {pred_name}'}.\n"
                        f"    DIAGNOSIS & MANDATORY ACTION (PREDICATE OVERLOADING STRICTLY FORBIDDEN IN CLASSICAL PDDL):\n"
                        f"    In Classical PDDL 2.1, predicate symbols CANNOT be overloaded with different arities or multiple meanings. "
                        f"    Ensure '{pred_name}' in domain 'predicates' matches the exact arity used in fixed problem ':init'/':goal', and if an action requires a relation of a different arity, declare a separate, dedicated predicate symbol in domain 'predicates' and use it in domain 'actions'."
                    )

                m = re.search(r"Type problem with proposition \(([a-zA-Z0-9_\-]+)\s+([^)]+)\)\s*-\s*parameter\s*(\d+)\s*is incorrectly typed", line)
                if m:
                    pred_name = m.group(1)
                    args = m.group(2).split()
                    param_idx = int(m.group(3)) - 1
                    faulty_arg = args[param_idx] if param_idx < len(args) else "unknown"
                    arg_type = None
                    obj_types = prob_meta.get("objects", {})
                    dom_consts = domain_bp.get("constants", {}) if isinstance(domain_bp, dict) else {}
                    if faulty_arg in obj_types:
                        arg_type = obj_types[faulty_arg]
                    elif faulty_arg in dom_consts:
                        arg_type = dom_consts[faulty_arg]
                    elif current_val_action:
                        for act in domain_bp.get("actions", []):
                            act_name = act.get("action_name") if isinstance(act, dict) else getattr(act, "action_name", None)
                            if act_name == current_val_action:
                                act_params = act.get("parameters", {}) if isinstance(act, dict) else getattr(act, "parameters", {})
                                if isinstance(act_params, dict):
                                    for p_name, p_type in act_params.items():
                                        if p_name.lstrip("?") == faulty_arg.lstrip("?"):
                                            arg_type = p_type
                                            break
                                break
                    if not arg_type:
                        arg_type = "object"
                    
                    declared_param_count = 0
                    expected_type = "object"
                    for p_decl in domain_bp.get("predicates", []):
                        clean_p = str(p_decl).strip('() ')
                        toks = clean_p.split()
                        if toks and toks[0] == pred_name:
                            p_vars = [t for t in toks[1:] if t.startswith("?")]
                            matches = re.findall(r"\?\w+\s*-\s*([a-zA-Z0-9_\-]+)", clean_p)
                            declared_param_count = len(p_vars) if p_vars else len(matches)
                            if param_idx < len(matches):
                                expected_type = matches[param_idx]
                                break
                                
                    dom_types = domain_bp.get("types", {})
                    norm_dom_types = {str(k).lower(): str(v).lower() if v else "object" for k, v in (dom_types.items() if isinstance(dom_types, dict) else [])}
                    current_parent = norm_dom_types.get(str(arg_type).lower(), "object")
                    is_arity_mismatch = (declared_param_count > 0 and len(args) != declared_param_count)
                    
                    type_mismatch_entries.append({
                        "pred_name": pred_name,
                        "args": args,
                        "faulty_arg": faulty_arg,
                        "arg_type": arg_type,
                        "expected_type": expected_type,
                        "current_parent": current_parent,
                        "param_idx": param_idx,
                        "declared_param_count": declared_param_count,
                        "is_arity_mismatch": is_arity_mismatch,
                        "current_val_action": current_val_action,
                        "raw_log": line.strip()
                    })
                    
                    if is_arity_mismatch:
                        val_type_diagnostics.append(
                            f"  * Proposition '({pred_name} {' '.join(args)})' has an ARITY MISMATCH: provided {len(args)} argument(s), but predicate '{pred_name}' is declared with {declared_param_count} parameter(s).\n"
                            f"    DIAGNOSIS & MANDATORY ACTION: In domain 'actions' or domain 'predicates', align the predicate signature and action usage so all {len(args)} arguments match. Do NOT change domain 'types' to resolve an arity mismatch!"
                        )
                    elif is_subtype(expected_type, arg_type, dom_types) and expected_type.lower() != arg_type.lower():
                        val_type_diagnostics.append(
                            f"  * Proposition '({pred_name} {' '.join(args)})' (parameter {param_idx + 1}): Argument '{faulty_arg}' has declared type '{arg_type}', but predicate '{pred_name}' parameter {param_idx + 1} was declared too narrowly expecting subtype '{expected_type}' (which already inherits from '{arg_type}').\n"
                            f"    DIAGNOSIS & MANDATORY ACTION:\n"
                            f"    1) In domain 'predicates', generalize parameter {param_idx + 1} of predicate '{pred_name}' to supertype '{arg_type}' (e.g. '({pred_name} ... ?x - {arg_type} ...)'), OR\n"
                            f"    2) If '{faulty_arg}' is an action parameter in '{current_val_action}', specialize parameter '{faulty_arg}' to '{expected_type}' in action '{current_val_action}'.\n"
                            f"    Do NOT declare '{arg_type}' as a subtype of '{expected_type}' in domain 'types' (subtyping cannot be inverted)."
                        )
                    elif is_subtype(arg_type, expected_type, dom_types):
                        val_type_diagnostics.append(
                            f"  * Action '{current_val_action}' proposition '({pred_name} {' '.join(args)})' (parameter {param_idx + 1}): Parameter '{faulty_arg}' has type '{arg_type}' (inheriting from '{current_parent}').\n"
                            f"    VAL failed type-checking against expected type '{expected_type}' because intermediate supertype '{current_parent}' is not declared as inheriting from '{expected_type}' in domain 'types'.\n"
                            f"    DIAGNOSIS & MANDATORY ACTION: In domain 'types', ensure '{current_parent}': '{expected_type}' is declared. NEVER declare 'object': 'object'."
                        )
                    else:
                        matching_alt_preds = []
                        for p_decl in domain_bp.get("predicates", []):
                            clean_p = str(p_decl).strip('() ')
                            toks = clean_p.split()
                            if toks and toks[0] != pred_name:
                                matches = re.findall(r"\?\w+\s*-\s*([a-zA-Z0-9_\-]+)", clean_p)
                                if len(matches) == declared_param_count and param_idx < len(matches):
                                    if is_subtype(arg_type, matches[param_idx], dom_types):
                                        matching_alt_preds.append((toks[0], p_decl))
                        
                        alt_advice = ""
                        if matching_alt_preds:
                            alt_names = [m[0] for m in matching_alt_preds]
                            alt_advice = (
                                f"\n    CRITICAL PREDICATE SUBSTITUTION: In domain 'predicates', dedicated predicate(s) {alt_names} already accept type '{arg_type}'! "
                                f"In action '{current_val_action or 'action'}', replace '{pred_name}' with the matching predicate '{alt_names[0]}' for argument '{faulty_arg}'! "
                                f"DO NOT generalize '{pred_name}' to 'object' when a dedicated predicate already exists!"
                            )

                        val_type_diagnostics.append(
                            f"  * Proposition '({pred_name} {' '.join(args)})' (parameter {param_idx + 1}): Parameter/object '{faulty_arg}' has type '{arg_type}', but predicate '{pred_name}' parameter {param_idx + 1} expects type '{expected_type}'.{alt_advice}\n"
                            f"    DIAGNOSIS & MANDATORY ACTION:\n"
                            f"    1) Check if the proposition used the wrong predicate name: if another predicate in domain 'predicates' accepts '{arg_type}', update the action to use that predicate.\n"
                            f"    2) Check the Natural Language Requirements: if '{arg_type}' is conceptually a subtype of '{expected_type}', declare '{arg_type}': '{expected_type}' in domain 'types'.\n"
                            f"    3) If '{arg_type}' and '{expected_type}' share a common supertype (or both can participate in '{pred_name}'), generalize parameter {param_idx + 1} of '{pred_name}' in domain 'predicates' to their common supertype.\n"
                            f"    4) If this action is checking a distinct physical state for a disjoint entity type '{arg_type}', declare a dedicated predicate symbol in domain 'predicates' for '{arg_type}' and update the action in domain 'actions' to use it."
                        )

        type_diag_str = "\n".join(val_type_diagnostics) if val_type_diagnostics else ""
        if type_diag_str:
            type_diag_section = f"\nGROUNDED TYPE HIERARCHY MISMATCH TRACE:\n{type_diag_str}\n"
        else:
            type_diag_section = ""

        focus_guidance = f"""
CRITICAL FAULT LOCALIZATION FOCUS:
The primary error is a strict syntax or type-checking violation detected by VAL.
Focus strictly on localizing and resolving the syntax or type/arity mismatch in the indicated domain action/predicate schema or domain types/constants hierarchy.
Do NOT report speculative state-reachability, cycle, or goal-distance issues when the domain has an active type or syntax defect.
{type_diag_section}
MANDATORY TYPE-CHECKING & SUBTYPING HIERARCHY RULES:
When VAL reports: "Type problem with proposition (p ...) - parameter N is incorrectly typed":
1. Check the type of the argument being passed versus the declared parameter type of predicate 'p' in 'predicates'.
2. CASE 0 — MISSING SUBTYPE DECLARATION IN 'types':
   - If the object/argument's type is conceptually a subtype of the expected parameter type according to the requirements (e.g., child type 'subtype_entity' is a subtype of parent type 'supertype_entity'), the domain 'types' is missing the subtype inheritance!
   - The MANDATORY repair hint is: "In domain 'types', declare the child type as inheriting from the parent type (e.g., declare 'child_type': 'parent_type'). Set faulty_element to 'types' (NOT the predicate name!). Do NOT modify the predicate declaration if it already expects the correct parent type!"
3. CASE A — COMMON SUPERTYPE GENERALIZATION (Inheritance & Subtyping):
   - Check if the passed argument type and the declared predicate parameter type share a common supertype in domain 'types' (e.g., both 'subtype_a' and 'subtype_b' inherit from 'supertype_t').
   - If they share a supertype, the predicate was declared TOO NARROWLY!
   - The MANDATORY repair hint is: "Generalize parameter N of predicate 'p' in domain 'predicates' to the common supertype (e.g., declare '(contains ?c - container ?s - substance)' instead of narrowing to a leaf subtype)."
   - CRITICAL ANTI-PATTERN: NEVER invent narrow ad-hoc predicates restricted to one leaf subtype and then advise an action with a sister subtype parameter to use it! In PDDL, an argument's type MUST be an instance or subtype of the declared parameter type.
4. CASE B — DISJOINT PHYSICAL STATES (e.g., Manipulator Emptiness vs Receptacle Emptiness):
   - If the types are completely disjoint (e.g., 'manipulator' and 'receptacle' both inherit directly from 'object' with no common subtype):
   - Natural language requirements often use the same English word for two distinct physical states (e.g., "manipulator D is empty" and "receptacle A is empty").
   - Since PDDL predicates cannot be overloaded, declare distinct predicates for the disjoint entities in domain 'predicates' and update domain 'actions' accordingly.
   - Similarly, if an action establishes a state for entity x while deleting a resource on host y, declare separate predicates for entity x and host y. NEVER advise substituting x with y to produce contradictory effects '(and (p y) (not (p y)))'.
5. CASE C — OVERLOADED RELATIONS:
   - If a relation symbol is used between two locations and also between a target entity and a location:
   - In PDDL, predicate signatures cannot be overloaded with different types.
   - Declare a distinct predicate symbol for the second relation in domain 'predicates', OR generalize the predicate parameter to their common supertype.
6. ANTI-OSCILLATION & DOMAIN-WIDE CONSISTENCY:
   - NEVER alternate a predicate declaration back and forth between incompatible types across repair iterations.
   - Verify that the proposed predicate signature satisfies fixed problem P_gold and all actions across the domain simultaneously.
"""
    orphaned_goals = causal_analysis.get("orphaned_goals", [])
    if orphaned_goals and not val_syntax_or_type_error:
        focus_guidance += f"""
CRITICAL UNREACHABILITY / ORPHANED GOAL DETECTED:
The goal specification requires predicate(s): {', '.join(orphaned_goals)}, but NO action in the domain produces them in its positive effects!
MANDATORY ORPHANED GOAL REPAIR GUIDANCE:
1. Review the Natural Language Requirements for the action that establishes this relationship (e.g. the action that drops, places, stacks, loads, or delivers the object).
2. Add the missing positive effect (e.g. '({orphaned_goals[0]} ...)') to that action's effect schema in domain 'actions'!
3. NEVER advise removing the delete effect from actions that legitimately delete this predicate (such as lifting or removing an object)!
"""

    ungroundable_preconditions = causal_analysis.get("ungroundable_preconditions", [])
    if ungroundable_preconditions and not val_syntax_or_type_error:
        dead_list = "\n".join([f"- Action '{u['action_name']}': {u['reason']}" for u in ungroundable_preconditions])
        focus_guidance += f"""
CRITICAL DEAD / UNGROUNDABLE PRECONDITIONS DETECTED:
The planner found NO relaxed solution because action preconditions or parameter types cannot be grounded against fixed problem P_gold:
{dead_list}
MANDATORY REPAIR GUIDANCE (TARGET DOMAIN BLUEPRINT ONLY — DO NOT MODIFY PROBLEM P_gold):
1. EMPTY PARAMETER DOMAINS (0 Objects Inheriting from Parameter Type):
   - If an action parameter requires supertype 'T', check if the object types in fixed problem ':objects' are subtypes of 'T' according to the requirements (e.g. 'Everything that is an A or B is also a T'). If so, update domain 'types' so those object types inherit from 'T'!
2. SPATIAL / RELATIONAL MEDIATED BINDING:
   - Did the action check a spatial relation directly against an entity rather than its location?
   - When an entity is stationed at a location, actions communicating or interacting with it must declare the station location parameter (e.g. '?loc - location'), bind the entity via '(at ?entity ?loc)', and assert spatial relations between the locations.
   - Did the action mistakenly repeat a variable reflexively (e.g. '(at ?l ?l)')? Use distinct variables for distinct entities and locations!
3. INVERTED ARGUMENT ORDER IN STATIC RELATIONS:
   - If a static relation (e.g. '(rel ?x ?y)') has ZERO matching facts in :init because the argument types are reversed compared to declared initial facts:
   - Swap the arguments in the action precondition in domain 'actions' to match the declared relation signature in problem :init.
4. MUTUALLY EXCLUSIVE PRECONDITIONS (SUPPORT/CONTAINER VS ITEM CLEARANCE):
   - When an action precondition checks both a support relation (e.g. '(on ?item ?support)') and a clearance condition (e.g. '(clear ?support)'):
   - The entity that must be clear (unobstructed) to be lifted/manipulated is the ITEM '?item', NOT the supporting surface underneath it!
   - In the action precondition, bind '(clear ?item)' to the item parameter already present in the action.
"""

    directional_traps = causal_analysis.get("directional_traps", [])
    if directional_traps and not val_syntax_or_type_error:
        traps_list = "\n".join([f"- {dt['reason']}" for dt in directional_traps])
        focus_guidance += f"""
CRITICAL DIRECTIONAL ASYMMETRY / MISSING INVERSE TRANSITION ACTIONS (CLASSICAL STRIPS INVARIANT):
The planner found NO valid plan because movement/transition is only modeled in one direction along an asymmetric static relation:
{traps_list}
MANDATORY STRIPS ACTION REPAIR GUIDANCE:
1. In Classical STRIPS (:strips :typing), disjunction ('or') in preconditions is strictly unsupported.
2. When requirements specify that entities can move/transition under multiple conditions or in both directions (e.g. forward and backward, or 'B is above C' and 'C is above B'):
   EACH distinct condition MUST be declared as a SEPARATE, uniquely-named action schema (e.g. adding suffix '_reverse', '_up', or '_2').
3. Add the missing inverse action schema to domain 'actions' with its parameters, preconditions (asserting the reverse relation atom), and transition effects matching the requirements!
"""

    bilateral_mutex_faults = causal_analysis.get("bilateral_mutex_faults", [])
    if bilateral_mutex_faults and not val_syntax_or_type_error:
        bm_list = "\n".join([f"- {bm['reason']}" for bm in bilateral_mutex_faults])
        focus_guidance += f"""
CRITICAL BILATERAL MUTEX CLEARANCE CONSERVATION FAULT:
The planner found NO valid plan because vacating an entity/location failed to assert the reciprocal clearance condition:
{bm_list}
MANDATORY MUTEX REPAIR GUIDANCE:
1. In Classical STRIPS, moving away from a location or releasing a held item vacates that resource.
2. In the indicated action's effects, add the missing clearance/vacancy positive effect as indicated above.
"""

    internal_contradictions = causal_analysis.get("internal_contradictions", [])
    if internal_contradictions and not val_syntax_or_type_error:
        ic_list = "\n".join([f"- {ic['description']}" for ic in internal_contradictions])
        focus_guidance += f"""
CRITICAL CONTRADICTORY SIMULTANEOUS ACTION EFFECTS:
An action schema simultaneously asserts both a positive atom and its negation:
{ic_list}
MANDATORY RESOLUTION GUIDANCE:
1. In Classical STRIPS, an action effect cannot contain both (P ...) and (not (P ...)).
2. If (P ...) was required in the action preconditions, the action consumes it: keep (not (P ...)) and remove (P ...).
3. If (P ...) was NOT in the action preconditions, the action establishes it: keep (P ...) and remove (not (P ...)).
"""
    planner_unsolvability = any("Could not find a plan" in err or "Search stopped without finding a solution" in err for err in raw_errors)
    planner_timeout = any("Planner Timeout" in err for err in raw_errors)
    if planner_timeout and not planner_unsolvability and not val_syntax_or_type_error:
        focus_guidance += """
PLANNER SEARCH TIMEOUT (UNSOLVABILITY NOT PROVEN):
Fast Downward grounded the task but its search did not terminate within the time budget.
A timeout is NOT evidence that the goal is unreachable, so reasoning reserved for proven unsolvability
(relaxing or removing preconditions to "open" the reachable state space) does not apply here.
Report only defects that are directly evidenced by the domain/problem structure or the causal analysis above.
"""
    has_feasibility_rejection = any("Plan Feasibility Rejection" in err or "Plan Transfer Rejection" in err for err in raw_errors)
    has_interpretability_rejection = any("Plan Interpretability Rejection" in err for err in raw_errors)
    if has_feasibility_rejection and not val_syntax_or_type_error:
        focus_guidance += """
CRITICAL PLAN FEASIBILITY REJECTION (PHYSICAL SOUNDNESS FAILURE):
The synthesized plan solved the generated domain D_gen, but VAL failed execution on reference domain D_gold.
Action schemas in D_gen are UNDER-CONSTRAINED (trivial model trap) or producing invalid state transitions:
1. Missing Preconditions: Add necessary physical preconditions (resource capacity, containment, clearance).
2. Inverted Effects: An action transition mutated the state incorrectly.
MANDATORY: Action schemas must use variables starting with '?', NEVER hardcode concrete problem objects.
"""
    if has_interpretability_rejection and not val_syntax_or_type_error:
        focus_guidance += """
CRITICAL PLAN INTERPRETABILITY REJECTION (EXPRESSIVE COMPLETENESS FAILURE):
The standard reference gold plan pi_gold failed execution on the generated domain D_gen.
Action schemas in D_gen are OVER-CONSTRAINED or have mismatched parameter signatures:
1. Extraneous Preconditions: Relax or remove extraneous preconditions that block standard reference transitions.
2. Operator Arity / Name Divergence: Align parameter signatures to match the reference task dynamics.
"""

    has_deterministic_causal_fault = bool(ungroundable_preconditions or orphaned_goals or internal_contradictions or directional_traps or bilateral_mutex_faults)
    if planner_unsolvability and not val_syntax_or_type_error:
        if has_deterministic_causal_fault:
            focus_guidance += """
CRITICAL DETERMINISTIC GROUNDING / REACHABILITY FAULT LOCALIZATION:
The Grounded Causal Dependency & Reachability Analysis above has mathematically identified the exact ungroundable parameters, preconditions, or effect contradictions preventing Fast Downward from finding a plan.
Report ONLY the repairs required to fix those identified defects above. Do NOT invent speculative effect additions or precondition modifications on other actions!
"""
        else:
            focus_guidance += f"""
CRITICAL PLANNER REACHABILITY / GOAL UNSOLVABILITY:
Fast Downward executed SAS+ translation and heuristic search, but found NO valid plan to reach the goal state.
MANDATORY DIAGNOSTIC SEQUENCE:
1. REACHABILITY-GUIDED PRECONDITION INSPECTION & RELAXATION:
   - When Fast Downward completely explores the state space without finding a solution (deadlock), the reachable state space is over-constrained.
   - Inspect action preconditions: check if any action contains an overly restrictive, unseeded, or non-goal precondition (such as requiring a resource/passenger count when none exists, or requiring a condition that cannot be established prior to the action).
   - If a precondition over-constrains reachability and is not physically required by the requirements to fire the action, RELAX or REMOVE that precondition to open the reachable solution corridor!
   - PRECONDITION PRESERVATION: NEVER relax, remove, or delete a precondition that is physically required by the action or explicitly stated in the requirements (e.g. requiring an entity to be clear, on a surface, inside a container, or held/lifted by an agent before loading/dropping). Legitimate preconditions must be preserved; reachability deadlocks are typically resolved by restoring missing positive effects on releasing/vacating actions, NOT by gutting preconditions!
   - PROHIBITION OF TAUTOLOGICAL / DUMMY LITERALS: Never propose or write '(true)', '(false)', or tautological disjunctions in preconditions or effects. In Classical PDDL 2.1 (:strips :typing), relaxing a precondition strictly means removing the unneeded atom from the '(and ...)' conjunction. Writing '(or ... (true))' is an invalid syntax construct.
   - MONOTONICITY OF REACHABILITY: Adding new preconditions strictly shrinks the state space. NEVER propose PRECONDITION_INSERTION when the solver is already in reachability deadlock!
2. UNUSABLE OBJECTS & OVERLY NARROW ACTION PARAMETERS:
   - Check if any objects in fixed problem ':objects' have types that cannot be accepted by any action parameter in the domain (e.g. an action parameter requires a leaf subtype instead of the common supertype, or domain 'types' omitted the supertype link).
   - If objects of a valid subtype cannot be used in any action, advise declaring the common supertype inheritance in domain 'types' and generalizing action parameters to that common supertype in domain 'actions'.
3. RESOURCE RELEASE VS OCCUPANCY (FAITHFULNESS TO NATURAL LANGUAGE EFFECTS):
   - CRITICAL MUTEX INVARIANT CHECK: An agent or device that is holding, lifting, carrying, or transporting an object is OCCUPIED, NOT AVAILABLE!
     If the requirements explicitly state: 'Once I lift/pick-up/unload... it is NOT the case anymore that agent A is available/free', NEVER advise asserting availability on that lifting/unloading action! The agent/device only becomes available again when it DROPS, PUTS DOWN, or LOADS the object.
   - VACATED LOCATIONS / SUPPORTS / RECEPTACLES CLEARING:
     When an action moves an agent or entity away from a location/tile L ('move', 'drive', 'depart'), or lifts/unstacks an entity from a support S:
     Did the movement or departure action omit the positive clearing effect explicitly described in the requirements (e.g. 'Once I move ... from B to C, it is the case that B is clear' -> '(clear ?from)')?
     If a movement action departs a location L without asserting that L is clear, locations remain permanently occupied, trapping the agent and causing planner reachability deadlock (heuristic = infinity)!
     Check the requirements carefully to see which action ACTUALLY performed the departure or unstacking, and add the positive '(clear ...)' atom to THAT departing action! Never add '(clear ?t)' to an action where the text explicitly states 'it is NOT the case anymore that B is clear'!
   - CONTRADICTORY SIMULTANEOUS EFFECTS:
     If an action simultaneously asserts both '(pred ?x)' and '(not (pred ?x))':
     Consult the Natural Language Requirements! Check whether the text says 'it is the case that ...' (keep the positive atom) or 'it is NOT the case anymore that ...' (keep the negative atom). NEVER advise adding a positive effect that directly contradicts an explicit negative effect in the text.
   - INSPECT EVERY ACTION INDIVIDUALLY: Inspect the CURRENT domain blueprint carefully. Compare each action's positive effects against the 'Once I ... it is the case that ...' statements in the text. Find the specific action that is ACTUALLY missing a positive transition effect described in the requirements!
"""

    locked_problem_notice = """
    CRITICAL FIXED PROBLEM INSTANCE INVARIANT (P_gold IS READ-ONLY):
    The Problem Blueprint represents the fixed ground-truth problem instance (P_gold) and CANNOT be modified!
    All diagnostic reports and suggested_repair_hint directives MUST target the DOMAIN blueprint ('domain.types', 'domain.constants', 'domain.predicates', 'domain.actions').
    NEVER advise modifying 'problem.objects', 'problem.initial_state', or 'problem.goal_state'.
    If a predicate, type, or constant in P_gold fails type-checking or lookup in VAL, advise updating 'domain.predicates', 'domain.types', or 'domain.constants' so the domain accepts P_gold cleanly.
    """

    prompt = f"""You are an expert PDDL Diagnostic & Fault Localization Oracle.

Your task is to analyze the failure signals from symbolic oracles (VAL / Fast Downward / Regression Suite) against the current PDDL Domain blueprint and fixed ground-truth Problem instance (P_gold), localize the root-cause fault in the Domain blueprint, and produce structured DiagnosticReports.

NATURAL LANGUAGE REQUIREMENTS & FIXED PROBLEM CONTRACT:
{requirements_text}

CURRENT DOMAIN BLUEPRINT (D_gen):
```json
{json.dumps(domain_bp, indent=2)}
```

FIXED GROUND-TRUTH PROBLEM PDDL (P_gold — READ-ONLY):
```pddl
{problem_pddl.strip()}
```

RAW ORACLE VERIFICATION ERRORS:
{error_traces_str}

GROUNDED ACTION-PREDICATE CAUSAL DEPENDENCY & REACHABILITY ANALYSIS:
{causal_summary}

    {locked_problem_notice}
    {focus_guidance}
    {STANDARD_CLASSICAL_PDDL_RULES}
    {STANDARD_DIAGNOSTIC_RULES}

    For each identified issue, provide:
    - error_category: SYNTAX_PARSE, TYPE_SIGNATURE, GROUNDING_UNSOLVABILITY, or HISTORICAL_REGRESSION.
      CRITICAL CATEGORIZATION INVARIANT:
      SYSTEM_ORACLE_ERROR is strictly forbidden for domain AST defects, action precondition/effect errors, or planner solvability failures. SYSTEM_ORACLE_ERROR is reserved exclusively for missing host binary executables.
      Contradictory effects (e.g. simultaneously adding and deleting an atom) or invalid precondition syntax MUST be categorized under SYNTAX_PARSE or GROUNDING_UNSOLVABILITY with repair_operation_type EFFECT_ALIGNMENT or PRECONDITION_INSERTION/RELAXATION.
    - repair_operation_type: PRECONDITION_RELAXATION, PRECONDITION_INSERTION, EFFECT_ALIGNMENT, TYPE_ARITY_ALIGNMENT, ACTION_ADDITION, REGRESSION_BACKWARD_COMPATIBILITY, or GENERAL_AST_REPAIR
    - faulty_element: Exact PDDL symbol name of the specific domain action (e.g. 'pick-up'), predicate, 'types', or 'constants' (use the exact PDDL identifier, not dot notation)
    - raw_log: Exact or summarized log snippet from the oracle
    - suggested_repair_hint: CRITICAL PRESCRIPTIVE REPAIR DIRECTIVE:
      Do NOT merely restate what happened or describe the symptom. Provide exact, actionable instructions targeting ONLY the Domain Blueprint:
      1) The exact domain AST target to modify (e.g. action 'pick-up', 'types', 'constants', or predicate '<name>').
      2) The concrete operation (e.g. 'ADD subtype link in domain.types', 'ADD action schema <name>', 'REPLACE precondition <pred> with <pred>', 'ADD positive effect <pred>').
      3) The exact PDDL literal or signature to write, and why it resolves the oracle failure.

    Return a valid JSON object strictly matching the DiagnosticAnalysis schema.
    """

    print("[FaultLocalizationNode]: Invoking Diagnostic LLM Agent for Layered Model-Based Fault Localization...")
    diagnostic_reports: List[DiagnosticReport] = []

    try:
        analysis, usage = invoke_structured_llm_with_telemetry(
            DiagnosticAnalysis,
            prompt,
            target_model=get_phase_model(3)
        )
        diagnostic_reports = analysis.reports

        # Update Telemetry Metrics
        state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
        state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
        state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
        state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)
        print(f"[FaultLocalizationNode]: Diagnostic LLM Agent identified {len(diagnostic_reports)} diagnostic item(s).")

        # Grounded Type Hierarchy Alignment: If VAL reported a parameter type mismatch,
        # guide the repair based on formal subtyping relation:
        if val_syntax_or_type_error and 'type_mismatch_entries' in locals():
            for tm in type_mismatch_entries:
                p_idx = tm.get("param_idx", 0) + 1
                dom_types = domain_bp.get("types", {}) if isinstance(domain_bp, dict) else {}
                
                if tm.get("is_arity_mismatch"):
                    target_elem = tm["pred_name"]
                    p_args = tm.get("args", [])
                    expected_arity = len(p_args)
                    obj_types = prob_meta.get("objects", {})
                    arg_types = [obj_types.get(a, "object") for a in p_args]
                    sample_call = f"({tm['pred_name']} {' '.join(p_args)})"
                    sample_params = " ".join([f"?x{i+1} - {t}" for i, t in enumerate(arg_types)])
                    sample_decl = f"({tm['pred_name']}" + (f" {sample_params}" if sample_params else "") + ")"
                    hint = (
                        f"CRITICAL GROUND TRUTH ARITY MISMATCH: Proposition '{sample_call}' in problem P_gold has exactly {expected_arity} argument(s) with types {arg_types}, "
                        f"but predicate '{tm['pred_name']}' was declared with {tm.get('declared_param_count', 0)} parameter(s) in domain 'predicates'. "
                        f"Fixed problem P_gold is read-only and cannot be changed. "
                        f"In domain 'predicates', declare predicate '{sample_decl}' with exactly {expected_arity} parameter(s) matching problem facts. "
                        f"In all domain 'actions', use '{tm['pred_name']}' with exactly {expected_arity} argument(s). "
                        f"Do NOT declare extra parameters or invent imaginary entity types (such as agent parameters) when problem facts provide only {expected_arity} argument(s)."
                    )
                elif is_subtype(tm["expected_type"], tm["arg_type"], dom_types) and tm["expected_type"].lower() != tm["arg_type"].lower():
                    target_elem = tm["pred_name"]
                    hint = (
                        f"Type mismatch on proposition '({tm['pred_name']} {tm['faulty_arg']} ...)': Argument '{tm['faulty_arg']}' has declared type '{tm['arg_type']}', but predicate '{tm['pred_name']}' was declared too narrowly expecting subtype '{tm['expected_type']}' (which already inherits from '{tm['arg_type']}'). "
                        f"In domain 'predicates', generalize parameter {p_idx} of predicate '{tm['pred_name']}' to supertype '{tm['arg_type']}' (e.g. '({tm['pred_name']} ... ?x - {tm['arg_type']} ...)'), OR if '{tm['faulty_arg']}' is an action parameter in '{tm.get('current_val_action')}', specialize '{tm['faulty_arg']}' to '{tm['expected_type']}' in domain 'actions'. "
                        f"Do NOT invert domain 'types' by declaring '{tm['arg_type']}' as a subtype of '{tm['expected_type']}'."
                    )
                elif is_subtype(tm["arg_type"], tm["expected_type"], dom_types):
                    target_elem = "types"
                    hint = (
                        f"In domain 'types', ensure '{tm['arg_type']}': '{tm['expected_type']}' "
                        f"(currently inheriting from '{tm['current_parent']}'). Object/parameter '{tm['faulty_arg']}' has type '{tm['arg_type']}' "
                        f"and must inherit from '{tm['expected_type']}' to satisfy predicate '{tm['pred_name']}'. "
                        f"Do NOT declare 'object': 'object'."
                    )
                else:
                    target_elem = tm["pred_name"]
                    hint = (
                        f"Type mismatch on proposition '({tm['pred_name']} {tm['faulty_arg']} ...)': Argument '{tm['faulty_arg']}' has type '{tm['arg_type']}', but predicate '{tm['pred_name']}' parameter {p_idx} expects type '{tm['expected_type']}'. "
                        f"In the Domain Blueprint (do NOT modify P_gold): "
                        f"1) If '{tm['arg_type']}' is conceptually a subtype of '{tm['expected_type']}' according to the requirements, declare '{tm['arg_type']}': '{tm['expected_type']}' in domain 'types'; "
                        f"2) If both types share a common supertype, generalize parameter {p_idx} of '{tm['pred_name']}' in domain 'predicates' to their common supertype; OR "
                        f"3) If they represent distinct states of disjoint entity types, declare a separate dedicated predicate for '{tm['arg_type']}' in domain 'predicates' and use it in domain 'actions'."
                    )
                
                if tm.get("is_arity_mismatch"):
                    # Purge any contradictory LLM reports that falsely suggest a different arity or parameters for this predicate
                    purged_reports = []
                    for rep in diagnostic_reports:
                        is_target_rep = (
                            rep.faulty_element.lower() in [tm["pred_name"].lower(), target_elem.lower()]
                            or (rep.faulty_element.lower() in ["predicates", "domain.predicates", "types"] and tm["pred_name"].lower() in (rep.suggested_repair_hint.lower() + " " + rep.raw_log.lower()))
                        )
                        if not is_target_rep:
                            purged_reports.append(rep)
                    diagnostic_reports = purged_reports
                    diagnostic_reports.append(DiagnosticReport(
                        error_category=ErrorCategory.TYPE_SIGNATURE,
                        repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                        faulty_element=target_elem,
                        raw_log=tm["raw_log"],
                        suggested_repair_hint=hint
                    ))
                else:
                    matched = False
                    for rep in diagnostic_reports:
                        is_target_rep = (
                            rep.faulty_element.lower() in [tm["pred_name"].lower(), "types", tm["arg_type"].lower(), target_elem.lower()]
                            or (rep.faulty_element.lower() in ["predicates", "domain.predicates", "types"] and tm["pred_name"].lower() in (rep.suggested_repair_hint.lower() + " " + rep.raw_log.lower()))
                        )
                        if rep.error_category == ErrorCategory.TYPE_SIGNATURE and is_target_rep:
                            rep.faulty_element = target_elem
                            rep.repair_operation_type = RepairOperationType.TYPE_ARITY_ALIGNMENT
                            rep.suggested_repair_hint = hint
                            matched = True
                            break
                    if not matched:
                        diagnostic_reports.append(DiagnosticReport(
                            error_category=ErrorCategory.TYPE_SIGNATURE,
                            repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                            faulty_element=target_elem,
                            raw_log=tm["raw_log"],
                            suggested_repair_hint=hint
                        ))

        if val_syntax_or_type_error and 'unknown_type_entries' in locals():
            for ute in unknown_type_entries:
                act = ute["action_name"] or "types"
                target_elem = ute["target_element"]
                hint = ute["hint"]
                sym = ute["unknown_symbol"]

                matched = False
                for rep in diagnostic_reports:
                    if rep.error_category == ErrorCategory.TYPE_SIGNATURE and (rep.faulty_element in [target_elem, act, "types", sym]):
                        rep.faulty_element = target_elem
                        rep.repair_operation_type = RepairOperationType.TYPE_ARITY_ALIGNMENT
                        rep.suggested_repair_hint = hint
                        matched = True
                        break
                if not matched:
                    diagnostic_reports.append(DiagnosticReport(
                        error_category=ErrorCategory.TYPE_SIGNATURE,
                        repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                        faulty_element=target_elem,
                        raw_log=ute["raw_log"],
                        suggested_repair_hint=hint
                    ))

        # When VAL certified that syntax and types are 100% valid (0 errors), LLM reports that were
        # miscategorized as SYNTAX_PARSE or TYPE_SIGNATURE are reclassified to semantic/grounding flaws
        # so they do not suppress reachability/deadlock blockers or starve the Repair node when causal analysis is silent.
        if not val_syntax_or_type_error:
            for r in diagnostic_reports:
                if r.error_category in (ErrorCategory.SYNTAX_PARSE, ErrorCategory.TYPE_SIGNATURE):
                    r.error_category = ErrorCategory.GROUNDING_UNSOLVABILITY
                    r.repair_operation_type = RepairOperationType.GENERAL_AST_REPAIR

        deterministic_causal_reports: List[DiagnosticReport] = []

        # 0. Plan Transfer Arity Mismatch Alignment (from Oracle 3 Feasibility or Oracle 4 Interpretability)
        is_fixed_mode = bool(state.get("fixed_signatures") or state.get("reference_domain_pddl"))
        m_arity = re.search(
            r"Plan Transfer Arity Mismatch:\s*Operator\s*'([^']+)'\s*in translated plan has\s*(\d+)\s*argument\(s\),\s*but ground-truth action requires\s*(\d+)\s*parameter\(s\)",
            error_traces_str,
            re.IGNORECASE
        )
        if m_arity and not is_fixed_mode:
            op_matched = m_arity.group(1)
            n_args = int(m_arity.group(2))
            m_params = int(m_arity.group(3))
            is_interp_excess = "Plan Interpretability Rejection" in error_traces_str and m_params > n_args
            is_feas_excess = "Plan Feasibility Rejection" in error_traces_str and n_args > m_params
            is_feas_deficit = "Plan Feasibility Rejection" in error_traces_str and n_args < m_params
            if is_interp_excess or is_feas_excess:
                gen_arity = m_params if is_interp_excess else n_args
                ref_arity = n_args if is_interp_excess else m_params
                bp_acts = domain_bp.get("actions", []) if isinstance(domain_bp, dict) else getattr(domain_bp, "actions", [])
                extra_hint = f"remove {gen_arity - ref_arity} extraneous parameter(s)"
                for b_act in bp_acts:
                    b_name = b_act.get("action_name", "") if isinstance(b_act, dict) else getattr(b_act, "action_name", "")
                    if b_name.lower().replace("-", "_") == op_matched.lower().replace("-", "_"):
                        op_matched = b_name
                        b_params = b_act.get("parameters", {}) if isinstance(b_act, dict) else getattr(b_act, "parameters", {})
                        b_precs = b_act.get("preconditions", []) if isinstance(b_act, dict) else getattr(b_act, "preconditions", [])
                        b_effs = b_act.get("effects", []) if isinstance(b_act, dict) else getattr(b_act, "effects", [])
                        used_v = set(re.findall(r"\?[a-zA-Z0-9_\-]+", " ".join([str(x) for x in list(b_precs) + list(b_effs)])))
                        unused_p = [k for k in b_params.keys() if (k if k.startswith("?") else f"?{k}") not in used_v]
                        if unused_p:
                            extra_hint = f"remove unreferenced parameter(s) {unused_p} from action '{op_matched}' parameters"
                        else:
                            extra_hint = f"remove the {gen_arity - ref_arity} extraneous parameter(s) from action '{op_matched}' parameters ({list(b_params.keys())}) and any extraneous precondition referencing them"
                        break
                deterministic_causal_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element=op_matched,
                    raw_log=m_arity.group(0),
                    suggested_repair_hint=(
                        f"Action '{op_matched}' declares {gen_arity} parameter(s), but the reference plan operation provides {ref_arity} argument(s). "
                        f"In domain 'actions', {extra_hint} so action '{op_matched}' has exactly {ref_arity} parameter(s)."
                    )
                ))
            elif is_feas_deficit:
                missing_count = m_params - n_args
                bp_acts = domain_bp.get("actions", []) if isinstance(domain_bp, dict) else getattr(domain_bp, "actions", [])
                for b_act in bp_acts:
                    b_name = b_act.get("action_name", "") if isinstance(b_act, dict) else getattr(b_act, "action_name", "")
                    if b_name.lower().replace("-", "_") == op_matched.lower().replace("-", "_"):
                        op_matched = b_name
                        break
                deterministic_causal_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element=op_matched,
                    raw_log=m_arity.group(0),
                    suggested_repair_hint=(
                        f"Action '{op_matched}' declares {n_args} parameter(s), but ground-truth action transfer requires {m_params} parameter(s) "
                        f"(missing {missing_count} parameter(s)). In action '{op_matched}' parameters, add the missing parameter(s) "
                        f"(such as intermediate context or target location variables required by preconditions) so action '{op_matched}' has exactly {m_params} parameter(s)."
                    )
                ))

        # 0b. Deterministic VAL Plan Validation Unsatisfied Precondition Localization (Oracle 3 Feasibility & Oracle 4 Interpretability)
        m_val_prec = re.search(
            r"Plan failed because of unsatisfied precondition in:\s*\(([a-zA-Z0-9_\-]+)((?:\s+[a-zA-Z0-9_\-]+)*)\).*?\(Set\s+\(([a-zA-Z0-9_\-]+)((?:\s+[a-zA-Z0-9_\-]+)*)\)\s+to true\)",
            error_traces_str,
            re.IGNORECASE | re.DOTALL
        )
        if m_val_prec:
            failed_op_raw = m_val_prec.group(1).strip()
            failed_op_args = [x.strip().lower() for x in m_val_prec.group(2).strip().split() if x.strip()]
            failed_pred = m_val_prec.group(3).strip()
            failed_pred_args = [x.strip().lower() for x in m_val_prec.group(4).strip().split() if x.strip()]
            bp_acts = domain_bp.get("actions", []) if isinstance(domain_bp, dict) else getattr(domain_bp, "actions", [])
            init_set_norm = {
                normalize_atom_expression(a)[0].lower()
                for a in prob_meta.get("initial_state", [])
                if normalize_atom_expression(a)[0]
            }
            matched_b_act = None
            for b_act in bp_acts:
                b_name = b_act.get("action_name", "") if isinstance(b_act, dict) else getattr(b_act, "action_name", "")
                if b_name.lower().replace("-", "_") == failed_op_raw.lower().replace("-", "_"):
                    matched_b_act = b_act
                    failed_op_raw = b_name
                    break
            if matched_b_act is not None:
                b_params = matched_b_act.get("parameters", {}) if isinstance(matched_b_act, dict) else getattr(matched_b_act, "parameters", {})
                b_param_vars = [k if str(k).startswith("?") else f"?{k}" for k in (b_params.keys() if isinstance(b_params, dict) else [])]
                b_precs = matched_b_act.get("preconditions", []) if isinstance(matched_b_act, dict) else getattr(matched_b_act, "preconditions", [])
                if len(b_param_vars) == len(failed_op_args):
                    var_to_ground = {b_param_vars[i].lower(): failed_op_args[i] for i in range(len(b_param_vars))}
                    ground_to_var = {failed_op_args[i]: b_param_vars[i] for i in range(len(b_param_vars))}
                    matching_schema_prec = None
                    for bp in b_precs:
                        bp_c, bp_pos = normalize_atom_expression(bp)
                        if bp_c and bp_pos:
                            bp_toks = bp_c.strip("() ").split()
                            if bp_toks and bp_toks[0].lower() == failed_pred.lower() and len(bp_toks[1:]) == len(failed_pred_args):
                                inst_args = [var_to_ground.get(v.lower(), v.lower()) for v in bp_toks[1:]]
                                if inst_args == failed_pred_args:
                                    matching_schema_prec = bp_c
                                    break
                    if "Plan Interpretability Rejection" in error_traces_str and matching_schema_prec:
                        bp_toks = matching_schema_prec.strip("() ").split()
                        if len(failed_pred_args) == 2:
                            rev_ground = f"({failed_pred.lower()} {failed_pred_args[1]} {failed_pred_args[0]})"
                            fwd_ground = f"({failed_pred.lower()} {failed_pred_args[0]} {failed_pred_args[1]})"
                            if rev_ground in init_set_norm and fwd_ground not in init_set_norm:
                                swapped_schema = f"({bp_toks[0]} {bp_toks[2]} {bp_toks[1]})"
                                val_hint = (
                                    f"Plan Interpretability Validation Failed in action '{failed_op_raw}': precondition '{matching_schema_prec}' "
                                    f"evaluated to false on ground instance '{fwd_ground}', whereas the reversed fact '{rev_ground}' holds in P_gold :init! "
                                    f"In action '{failed_op_raw}' preconditions, swap the argument order of '{matching_schema_prec}' to '{swapped_schema}'."
                                )
                                deterministic_causal_reports.append(DiagnosticReport(
                                    error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                                    faulty_element=failed_op_raw,
                                    raw_log=m_val_prec.group(0)[:300],
                                    suggested_repair_hint=val_hint
                                ))
                    elif "Plan Feasibility Rejection" in error_traces_str and not matching_schema_prec:
                        if all(ga in ground_to_var for ga in failed_pred_args):
                            schema_vars = [ground_to_var[ga] for ga in failed_pred_args]
                            missing_schema_prec = f"({failed_pred} {' '.join(schema_vars)})"
                            val_hint = (
                                f"Plan Feasibility Validation Failed in action '{failed_op_raw}': ground precondition "
                                f"'({failed_pred} {' '.join(failed_pred_args)})' was unsatisfied during plan execution! "
                                f"In action '{failed_op_raw}' preconditions, add '{missing_schema_prec}'."
                            )
                            deterministic_causal_reports.append(DiagnosticReport(
                                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                                repair_operation_type=RepairOperationType.PRECONDITION_INSERTION,
                                faulty_element=failed_op_raw,
                                raw_log=m_val_prec.group(0)[:300],
                                suggested_repair_hint=val_hint
                            ))

        # 1. Grounded Action Reachability Alignment (Consolidated across actions sharing the same predicate replacement)
        ungroundable_list = causal_analysis.get("ungroundable_preconditions", [])
        consolidated_ungroundable: List[Dict[str, Any]] = []
        grouped_by_sym_match: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        grouped_by_act_rebind: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}

        for up in ungroundable_list:
            pred_k = str(up.get("predicate") or "").strip().lower()
            bm_k = up.get("best_match")
            act_k = str(up.get("action_name") or "").strip()
            if pred_k and bm_k and not str(bm_k).startswith("(") and not str(bm_k).startswith("REMOVE_"):
                key = (pred_k, str(bm_k).strip().lower())
                grouped_by_sym_match.setdefault(key, []).append(up)
            elif act_k and pred_k and bm_k and str(bm_k).startswith("(") and "never produced for" in str(up.get("reason", "")).lower():
                r_key = (act_k.lower(), pred_k)
                grouped_by_act_rebind.setdefault(r_key, []).append(up)
            else:
                consolidated_ungroundable.append(up)

        for (pred_k, _), items in grouped_by_sym_match.items():
            if len(items) == 1:
                consolidated_ungroundable.append(items[0])
            else:
                act_list = list(dict.fromkeys([it.get("action_name", "") for it in items if it.get("action_name")]))
                first_act = act_list[0] if act_list else "domain.actions"
                bm_orig = items[0].get("best_match")
                base_hint = items[0].get("reason", "")
                if len(act_list) == 1:
                    expr_list = list(dict.fromkeys([it.get("expression", "") for it in items if it.get("expression")]))
                    c_hint = f"For all occurrences {expr_list} in action '{first_act}': {base_hint}"
                else:
                    c_hint = (
                        f"Across ALL affected actions {act_list} and domain 'predicates', "
                        f"replace '{items[0].get('predicate')}' with '{bm_orig}'. Detail: {base_hint}"
                    )
                consolidated_ungroundable.append({
                    "action_name": first_act,
                    "predicate": items[0].get("predicate"),
                    "reason": c_hint
                })

        for (act_k, pred_k), items in grouped_by_act_rebind.items():
            if len(items) == 1:
                consolidated_ungroundable.append(items[0])
            else:
                first_act = items[0].get("action_name", "")
                combined_reasons = " Also: ".join([it.get("reason", "") for it in items])
                consolidated_ungroundable.append({
                    "action_name": first_act,
                    "predicate": items[0].get("predicate"),
                    "reason": combined_reasons
                })

        by_action_final: Dict[str, List[Dict[str, Any]]] = {}
        final_ungroundable: List[Dict[str, Any]] = []
        for up_item in consolidated_ungroundable:
            a_key = str(up_item.get("action_name") or "").strip()
            if a_key and a_key.lower() not in ("types", "predicates", "domain.actions"):
                by_action_final.setdefault(a_key, []).append(up_item)
            else:
                final_ungroundable.append(up_item)
        for a_key, a_items in by_action_final.items():
            if len(a_items) == 1:
                final_ungroundable.append(a_items[0])
            else:
                combined_r = " Also: ".join(dict.fromkeys([it.get("reason", "") for it in a_items if it.get("reason")]))
                final_ungroundable.append({
                    "action_name": a_key,
                    "predicate": a_items[0].get("predicate"),
                    "reason": combined_r
                })
        consolidated_ungroundable = final_ungroundable

        for up in consolidated_ungroundable:
            act = up.get("action_name", "")
            hint = up.get("reason", "")
            target_f = "types" if "ZERO objects" in hint else (act or "domain.actions")
            if "eliminate" in hint.lower() or "extraneous" in hint.lower() or "unreachable" in hint.lower() or "remove the" in hint.lower():
                op_type = RepairOperationType.PRECONDITION_RELAXATION
            elif "action effects" in hint.lower() or "positive effect" in hint.lower():
                op_type = RepairOperationType.EFFECT_ALIGNMENT
            else:
                op_type = RepairOperationType.TYPE_ARITY_ALIGNMENT
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=op_type,
                faulty_element=target_f,
                raw_log=hint,
                suggested_repair_hint=hint
            ))

        # 2. Bilateral State-Transition Mutex Faults (Consolidated across actions by vacated clearance predicate)
        bilateral_mutex_list = causal_analysis.get("bilateral_mutex_faults", [])
        grouped_bm: Dict[str, List[Dict[str, Any]]] = {}
        for bm in bilateral_mutex_list:
            p_k = str(bm.get("predicate") or "").strip().lower()
            grouped_bm.setdefault(p_k, []).append(bm)
        for p_k, bm_items in grouped_bm.items():
            act_list = list(dict.fromkeys([it.get("action_name", "") for it in bm_items if it.get("action_name")]))
            first_act = act_list[0] if act_list else "domain.actions"
            if len(bm_items) == 1:
                bm_hint = bm_items[0].get("reason", "")
            else:
                per_act = " | ".join([it.get("reason", "") for it in bm_items])
                bm_hint = f"Across ALL affected actions {act_list}, restore clearance/vacancy predicate '{bm_items[0].get('predicate')}': {per_act}"
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
                faulty_element=first_act,
                raw_log=bm_hint,
                suggested_repair_hint=bm_hint
            ))

        # 2b. Irreversible Resource Depletion / Absorbing State Lockout (Consolidated across actions by predicate)
        irrev_locks_list = causal_analysis.get("irreversible_locks", [])
        grouped_il: Dict[str, List[Dict[str, Any]]] = {}
        for il in irrev_locks_list:
            p_k = str(il.get("predicate") or "").strip().lower()
            grouped_il.setdefault(p_k, []).append(il)
        for p_k, il_items in grouped_il.items():
            act_list = list(dict.fromkeys([it.get("action_name", "") for it in il_items if it.get("action_name")]))
            first_act = act_list[0] if act_list else "domain.actions"
            if len(il_items) == 1:
                il_hint = il_items[0].get("reason", "")
            else:
                per_act = " | ".join([it.get("reason", "") for it in il_items])
                il_hint = f"Across ALL affected actions {act_list} on predicate '{il_items[0].get('predicate')}': {per_act}"
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
                faulty_element=first_act,
                raw_log=il_hint,
                suggested_repair_hint=il_hint
            ))

        # 2c. SAS+ Functional & Mutex State-Transition Delete Completeness (Consolidated by action)
        missing_td_list = causal_analysis.get("missing_transition_deletes", [])
        grouped_mtd: Dict[str, List[Dict[str, Any]]] = {}
        for mtd in missing_td_list:
            act_k = str(mtd.get("action_name") or "").strip()
            grouped_mtd.setdefault(act_k, []).append(mtd)
        for act_k, mtd_items in grouped_mtd.items():
            if len(mtd_items) == 1:
                mtd_hint = mtd_items[0].get("reason", "")
            else:
                del_atoms = [f"(not {it.get('expression')})" for it in mtd_items if it.get("expression")]
                mtd_hint = (
                    f"In action '{act_k}' effects, add the missing state-transition delete effects {del_atoms} "
                    f"so stale precondition fluents do not persist after the state transition."
                )
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
                faulty_element=act_k or "domain.actions",
                raw_log=mtd_hint,
                suggested_repair_hint=mtd_hint
            ))

        # 3. Grounded Directional Asymmetry Alignment
        directional_traps = causal_analysis.get("directional_traps", [])
        for dt in directional_traps:
            f_acts = dt.get("forward_actions", [])
            act_target = f_acts[0] if f_acts else "domain.actions"
            hint = dt.get("reason", "")
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=RepairOperationType.ACTION_ADDITION,
                faulty_element=act_target,
                raw_log=f"Directional Asymmetry Deadlock: static relation '{dt.get('relation')}' is directed and missing inverse action.",
                suggested_repair_hint=hint
            ))

        # 4. Grounded Contradictory Simultaneous Effects Alignment
        for ic in internal_contradictions:
            act_target = ic.get("action_name", "")
            clash_atom = ic.get("atom", "")
            is_in_pre = ic.get("is_in_precond", False)
            if is_in_pre:
                hint = (
                    f"In action '{act_target}', REMOVE the contradictory positive effect '{clash_atom}' "
                    f"and retain the delete effect '(not {clash_atom})' because '{clash_atom}' is in preconditions."
                )
            else:
                hint = (
                    f"In action '{act_target}', RETAIN the positive effect '{clash_atom}' and "
                    f"REMOVE the contradictory delete effect '(not {clash_atom})' because '{clash_atom}' is NOT in preconditions."
                )
            deterministic_causal_reports.append(DiagnosticReport(
                error_category=ErrorCategory.SYNTAX_PARSE,
                repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
                faulty_element=act_target,
                raw_log=f"Contradictory simultaneous action effects in '{act_target}': {clash_atom} and (not {clash_atom})",
                suggested_repair_hint=hint
            ))

        if deterministic_causal_reports:
            if not val_syntax_or_type_error:
                # Place proven deterministic causal reports strictly ahead of speculative LLM reports
                # and exclude unverified LLM guesses when formal causal faults exist
                diagnostic_reports = deterministic_causal_reports
            else:
                diagnostic_reports.extend(deterministic_causal_reports)
    except Exception as fault_loc_err:
        print(f"[FaultLocalizationNode ERROR]: Diagnostic LLM call failed: {fault_loc_err}")
        # Strictly record the failure; NO deterministic heuristic fallbacks or ground-truth substitutions
        if not state.get("verification_errors"):
            state["verification_errors"] = [f"Fault Localization Diagnostic LLM Exception: {fault_loc_err}"]
        state["diagnostic_reports"] = []
        state["formatted_diagnostic_feedback"] = f"Diagnostic LLM Failure: {fault_loc_err}"
        elapsed = time.time() - start_t
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + elapsed, 3)
        state["node_latencies"] = latencies
        return state

    # Prioritize reports using Layered Model-Based Fault Localization
    prioritized_reports, active_tier = prioritize_diagnostic_reports(diagnostic_reports, max_items=6)
    print(f"[FaultLocalizationNode]: Layered Model-Based Fault Localization prioritized {len(prioritized_reports)} of {len(diagnostic_reports)} diagnostic item(s) (Active Tier: {active_tier}).")
    print(f"  --- [FAULT LOCALIZATION & REPAIR HINTS (Tier {active_tier})] ---")
    for r_idx, rep in enumerate(prioritized_reports, 1):
        elem = rep.faulty_element or "domain"
        cat = rep.error_category.value if hasattr(rep.error_category, "value") else str(rep.error_category)
        hint = rep.suggested_repair_hint
        print(f"   -> Flaw #{r_idx} [{elem} | {cat}]:")
        print(f"      Hint: {hint}")
    print(f"  --------------------------------------------------")

    # Store prioritized reports and formatted feedback in state for the repair agent
    dumped_prioritized = [r.model_dump() for r in prioritized_reports]
    state["diagnostic_reports"] = dumped_prioritized
    state["formatted_diagnostic_feedback"] = format_diagnostic_feedback(prioritized_reports, active_tier)

    # Accumulate all historical reports for comprehensive evaluation metrics
    dumped_all = [r.model_dump() for r in diagnostic_reports]
    hist_reports = state.get("historical_diagnostic_reports", [])
    for dr in dumped_all:
        if dr not in hist_reports:
            hist_reports.append(dr)
    state["historical_diagnostic_reports"] = hist_reports

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies

    return state
