import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from nodes.schemas.pddl_blueprint import DiagnosticReport, ErrorCategory, RepairOperationType
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES, STANDARD_DIAGNOSTIC_RULES
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from tools.causal_fault_analyzer import run_causal_fault_analysis
from nodes.pddl_to_ast_parser import extract_pddl_problem_metadata
from tools.pddl_utils import normalize_pddl_expression, normalize_atom, is_subtype


# Per-error character budget for raw (untriaged) oracle feedback. Matches the
# truncation applied by the UNSTRUCTURED_RETRY baseline in eval/baselines.py.
RAW_FEEDBACK_CHAR_LIMIT = 1500


class DiagnosticAnalysis(BaseModel):
    """Container for structured diagnostic reports produced by the Diagnostic LLM Agent."""
    reports: List[DiagnosticReport] = Field(
        default_factory=list,
        description="Ranked list of diagnostic reports localizing faults and suggesting repair operations"
    )


def check_system_oracle_binary_availability(raw_log: str, oracle_name: str) -> Optional[DiagnosticReport]:
    """Checks if an oracle error is caused by a missing system binary."""
    log_lower = raw_log.lower()
    binary_missing = (
        "binary not found" in log_lower
        or "executable not found" in log_lower
        or "failed to execute val binary" in log_lower
        or "failed to execute fast downward" in log_lower
        or "cannot find the file specified" in log_lower
    )
    if binary_missing:
        return DiagnosticReport(
            error_category=ErrorCategory.SYSTEM_ORACLE_ERROR,
            repair_operation_type=RepairOperationType.GENERAL_AST_REPAIR,
            faulty_element=f"{oracle_name} Binary",
            raw_log=raw_log.strip()[:300],
            suggested_repair_hint=f"Ensure {oracle_name} binary path is properly configured on system PATH or .env file."
        )
    return None


def compute_layered_fault_priority(report: DiagnosticReport) -> Tuple[int, int]:
    """Computes tier level and rank for a diagnostic report."""
    raw = (str(report.raw_log) + " " + str(report.suggested_repair_hint)).lower()
    cat = str(report.error_category).lower()
    elem = str(report.faulty_element).lower()

    if "syntax" in cat or "type_signature" in cat or "unknown type" in raw or "arity mismatch" in raw or elem in ("types", "predicates") or "not found" in raw or "missing" in raw:
        return (0, 0)

    if "absorbing deadlock" in raw or "permanently depletes" in raw:
        return (0, 1)

    if "empty parameter domain" in raw or "zero matching facts in p_gold :init" in raw or "ungroundable" in raw:
        return (1, 0)

    if "plan failed" in raw or "feasibility" in raw:
        return (1, 1)

    if "goal" in raw and ("unproduced" in raw or "not produced" in raw or "unreachable" in raw or "orphan" in raw):
        return (2, 0)

    if "contradictory" in raw or "missing transition" in raw or "self-blocking" in raw:
        return (3, 0)

    return (4, 0)


def prioritize_diagnostic_reports(reports: List[DiagnosticReport], max_items: int = 5) -> Tuple[List[DiagnosticReport], int]:
    """Selects the highest-priority causal tier of reports up to max_items."""
    if not reports:
        return [], 0

    filtered = []
    for r in reports:
        raw_r = (str(r.raw_log) + " " + str(r.suggested_repair_hint)).lower()
        if r.repair_operation_type == RepairOperationType.PRECONDITION_INSERTION and ("unsolvable" in raw_r or "deadlock" in raw_r or "could not find a plan" in raw_r):
            continue
        filtered.append(r)
    reports = filtered or reports

    scored = [(compute_layered_fault_priority(r), idx, r) for idx, r in enumerate(reports)]
    scored.sort(key=lambda x: (x[0], x[1]))
    min_tier = scored[0][0][0]
    return [r for _, _, r in scored[:max_items]], min_tier


def format_diagnostic_feedback(reports: List[DiagnosticReport], active_tier: Optional[int] = None) -> str:
    """Formats structured DiagnosticReports into prescriptive feedback."""
    if not reports:
        return ""

    tier_desc = {
        0: "Tier 0 (Type Hierarchy & Formal AST Well-Formedness)",
        1: "Tier 1 (Initial State Groundability & Seed Preconditions)",
        2: "Tier 2 (Goal Producer Reachability & Causal Alignment)",
        3: "Tier 3 (State Transition Completeness & Mutex Conservation)",
        4: "Tier 4 (Precondition & Effect Refinements)",
    }
    t_str = tier_desc.get(active_tier, f"Tier {active_tier}") if active_tier is not None else "Root Causal Blockers"

    feedback_lines = [
        f"### Diagnostic Failure Analysis Report (Layered Fault Localization Priority: {t_str}):",
        "CRITICAL GUIDANCE: Focus repairs strictly on resolving these top-priority causal blockers before modifying unrelated actions.\n"
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


def FaultLocalizationNode(state: Dict[str, Any]) -> Dict[str, Any]:
    """Localizes domain faults using causal analysis and diagnostics."""
    start_t = time.time()
    raw_errors = state.get("verification_errors", [])

    if not raw_errors:
        state["diagnostic_reports"] = []
        state["formatted_diagnostic_feedback"] = ""
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    # ABLATION_NO_TRIAGE: bypass layered fault localization entirely.
    # The repair node receives only the raw, unparsed oracle output (no causal analysis,
    # no diagnostic LLM, no action targeting), truncated with the same per-error limit
    # used by the UNSTRUCTURED_RETRY baseline.
    if state.get("skip_fault_localization"):
        raw_chunks = [
            str(e).encode("ascii", "ignore").decode("ascii")[:RAW_FEEDBACK_CHAR_LIMIT]
            for e in raw_errors
        ]
        state["diagnostic_reports"] = []
        state["causal_graph_analysis"] = {}
        state["formatted_diagnostic_feedback"] = (
            "RAW ORACLE ERROR OUTPUT (unstructured, no fault localization):\n"
            + "\n\n".join(raw_chunks)
        )
        latencies = state.get("node_latencies", {})
        latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    # Check system oracle binary
    for err in raw_errors:
        rep = check_system_oracle_binary_availability(err, "Oracle")
        if rep:
            state["diagnostic_reports"] = [rep.model_dump()]
            state["formatted_diagnostic_feedback"] = format_diagnostic_feedback([rep])
            return state

    domain_bp = state.get("pddl_domain_blueprint", {})
    if (not domain_bp or not domain_bp.get("actions")) and state.get("generated_domain_pddl"):
        from nodes.pddl_to_ast_parser import parse_pddl_domain_to_blueprint
        domain_bp = parse_pddl_domain_to_blueprint(state["generated_domain_pddl"])
        state["pddl_domain_blueprint"] = domain_bp

    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if problem_pddl else {}
    requirements_text = state.get("requirements", "")
    error_traces_str = "\n".join(raw_errors)

    # Causal dependency analysis
    causal_analysis = run_causal_fault_analysis(
        domain_bp,
        problem_pddl,
        raw_errors
    )
    state["causal_graph_analysis"] = causal_analysis
    causal_summary = causal_analysis.get("diagnostic_summary", "")

    # Collect causal reports
    deterministic_reports: List[DiagnosticReport] = []

    # Unproduced Goals
    for og in causal_analysis.get("orphaned_goals", []):
        deterministic_reports.append(DiagnosticReport(
            error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
            repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
            faulty_element="domain.actions",
            raw_log=f"Goal atom '{og}' has zero producing actions in the domain.",
            suggested_repair_hint=f"In domain 'actions', add positive effect '({og} ...)' to the appropriate goal-achieving action."
        ))

    # Ungroundable Preconditions
    for up in causal_analysis.get("ungroundable_preconditions", []):
        act = up.get("action_name", "") or "domain.actions"
        hint = up.get("reason", "")
        op_type = RepairOperationType.PRECONDITION_RELAXATION if ("self-blocking" in hint.lower() or "remove" in hint.lower()) else RepairOperationType.TYPE_ARITY_ALIGNMENT
        deterministic_reports.append(DiagnosticReport(
            error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
            repair_operation_type=op_type,
            faulty_element=act,
            raw_log=hint,
            suggested_repair_hint=hint
        ))

    # Missing Transition Deletes
    for mtd in causal_analysis.get("missing_transition_deletes", []):
        act_k = mtd.get("action_name", "") or "domain.actions"
        mtd_hint = mtd.get("reason", "")
        deterministic_reports.append(DiagnosticReport(
            error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
            repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
            faulty_element=act_k,
            raw_log=mtd_hint,
            suggested_repair_hint=mtd_hint
        ))

    # Contradictory Simultaneous Effects
    for ic in causal_analysis.get("internal_contradictions", []):
        act_target = ic.get("action_name", "")
        clash_atom = ic.get("atom", "")
        resolution = ic.get("description") or (
            f"In action '{act_target}', contradictory simultaneous effects '{clash_atom}' and '(not {clash_atom})' violate Classical STRIPS. "
            f"Resolve the conflict by keeping the intended direction."
        )
        deterministic_reports.append(DiagnosticReport(
            error_category=ErrorCategory.SYNTAX_PARSE,
            repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
            faulty_element=act_target,
            raw_log=f"Contradictory simultaneous effects in '{act_target}': {clash_atom} and (not {clash_atom})",
            suggested_repair_hint=resolution
        ))

    # Irreversible resource depletions
    for rd in causal_analysis.get("resource_depletions", []):
        act_target = rd.get("action_name", "")
        clash_atom = rd.get("atom", "")
        deterministic_reports.append(DiagnosticReport(
            error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
            repair_operation_type=RepairOperationType.EFFECT_ALIGNMENT,
            faulty_element=act_target,
            raw_log=f"Irreversible resource depletion in '{act_target}': (not {clash_atom})",
            suggested_repair_hint=rd.get("description", "")
        ))

    # Plan feasibility failure
    if "Plan Feasibility Rejection" in error_traces_str or "Plan failed" in error_traces_str:
        m_pf = re.search(r"(?:Plan failed because of unsatisfied precondition in|operator)\s*:\s*\(([a-zA-Z0-9_\-]+)\s*([^)]*)\)", error_traces_str, re.IGNORECASE)
        if not m_pf:
            m_pf = re.search(r"\(([a-zA-Z0-9_\-]+)\s+([^)]*)\)\s+has an unsatisfied precondition", error_traces_str, re.IGNORECASE)
        if m_pf:
            act_sym = m_pf.group(1)
            act_args = m_pf.group(2).strip().split()
            
            # Universal First-Order Logic Lifting: Ground VAL Trace -> Lifted Formal Parameters
            lifted_advice = []
            is_alignment = False
            old_atom = ""
            matching_act = next((a for a in domain_bp.get("actions", []) if a.get("action_name", "").lower() == act_sym.lower()), None)
            if matching_act:
                formal_params = [p if p.startswith("?") else f"?{p}" for p in matching_act.get("parameters", {}).keys()]
                ground_to_formal = {ground_arg.lower(): formal_param for ground_arg, formal_param in zip(act_args, formal_params)}
                
                advice_matches = re.findall(r"Set\s+\(([a-zA-Z0-9_\-]+)\s+([^)]*)\)\s+to\s+(true|false)", error_traces_str, re.IGNORECASE)
                for p_sym, p_args_str, val_bool in advice_matches:
                    p_ground_args = p_args_str.strip().split()
                    if all(g.lower() in ground_to_formal for g in p_ground_args):
                        pargs = " ".join(ground_to_formal[g.lower()] for g in p_ground_args)
                        lifted_atom = f"({p_sym} {pargs})"
                        if val_bool.lower() == "true":
                            # Check if relation symbol is already present with different variable order (argument permutation)
                            existing_same_pred = []
                            for pre in matching_act.get("preconditions", []):
                                pre_clean = pre.strip("() ").split()
                                if pre_clean and pre_clean[0].lower() == p_sym.lower():
                                    existing_same_pred.append(pre.strip())
                            
                            if existing_same_pred:
                                old_atom = existing_same_pred[0]
                                if old_atom.lower() != lifted_atom.lower():
                                    is_alignment = True
                                    lifted_advice.append(f"replace precondition '{old_atom}' with '{lifted_atom}' (correct relational argument permutation)")
                                else:
                                    lifted_advice.append(f"require precondition '{lifted_atom}'")
                            else:
                                lifted_advice.append(f"require precondition '{lifted_atom}'")
                        else:
                            lifted_advice.append(f"do not require '{lifted_atom}'")
            
            lifted_hint = f" Specifically, {'; '.join(lifted_advice)}." if lifted_advice else ""
            raw_act_str = f"({act_sym} {' '.join(act_args)})"
            
            if is_alignment:
                op_type = RepairOperationType.PRECONDITION_ALIGNMENT
                repair_hint = (
                    f"Plan feasibility failed on reference domain D_gold at step '{raw_act_str}'.{lifted_hint} "
                    f"In action '{act_sym}', replace the inverted relational precondition '{old_atom}' with '{lifted_atom}' "
                    f"so parameter variable arguments match the physical relation orientation. Do NOT keep both! "
                    f"Also ensure any conjugate/inverse actions referencing predicate '{p_sym}' use consistent opposing orientation."
                )
                deterministic_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                    repair_operation_type=RepairOperationType.PRECONDITION_ALIGNMENT,
                    faulty_element=p_sym,
                    raw_log=f"Relational argument permutation inverted for predicate '({p_sym} ...)' in action '{act_sym}'.",
                    suggested_repair_hint=f"Align parameter variable ordering for predicate '{p_sym}' across action '{act_sym}' and related conjugate actions to preserve reachability."
                ))
            else:
                op_type = RepairOperationType.PRECONDITION_INSERTION
                repair_hint = (
                    f"Plan feasibility failed on reference domain D_gold at step '{raw_act_str}'.{lifted_hint} "
                    f"In action '{act_sym}', check parameter variable ordering, ensure required preconditions match physical invariants, "
                    f"and ensure preceding actions assert required preconditions so the generated plan executes soundly on D_gold."
                )
            
            deterministic_reports.append(DiagnosticReport(
                error_category=ErrorCategory.GROUNDING_UNSOLVABILITY,
                repair_operation_type=op_type,
                faulty_element=act_sym,
                raw_log=f"Plan failed on D_gold at operator {raw_act_str}.{lifted_hint}",
                suggested_repair_hint=repair_hint
            ))

    # Parse VAL Syntax / Type Checking Directives
    val_has_error = any("VAL Error:" in err or "Translator Syntax Error:" in err for err in raw_errors)
    if val_has_error:
        for line in error_traces_str.splitlines():
            # Missing Predicate
            m_pnf = re.search(r"Predicate\s+([a-zA-Z0-9_\-]+)\s+not found", line)
            if m_pnf:
                p_sym = m_pnf.group(1)
                deterministic_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.TYPE_SIGNATURE,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element=p_sym,
                    raw_log=line.strip(),
                    suggested_repair_hint=f"In domain 'predicates', declare predicate '({p_sym} ...)' with parameter types matching problem P_gold ':init'/':goal'."
                ))

            # Arity Mismatch
            m_arity = re.search(r"Problem with proposition\s*\(([a-zA-Z0-9_\-]+).*?\)\s*-\s*too\s+(few|many)\s+parameters", line)
            if m_arity:
                p_sym = m_arity.group(1)
                deterministic_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.TYPE_SIGNATURE,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element=p_sym,
                    raw_log=line.strip(),
                    suggested_repair_hint=f"In domain 'predicates', align predicate '({p_sym} ...)' arity and parameter types to match problem P_gold facts."
                ))

            # Unknown Type
            m_unk = re.search(r"Object with unknown type:\s*([a-zA-Z0-9_\-]+)", line)
            if m_unk:
                t_sym = m_unk.group(1)
                deterministic_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.TYPE_SIGNATURE,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element="types",
                    raw_log=line.strip(),
                    suggested_repair_hint=f"In domain 'types', declare type '{t_sym}': 'object' (or its appropriate supertype)."
                ))

            # Parameter Type Mismatch
            m_pm = re.search(r"Type problem with proposition \(([a-zA-Z0-9_\-]+)\s+([^)]+)\)\s*-\s*parameter\s*(\d+)\s*is incorrectly typed", line)
            if m_pm:
                p_name = m_pm.group(1)
                p_idx = int(m_pm.group(3))
                deterministic_reports.append(DiagnosticReport(
                    error_category=ErrorCategory.TYPE_SIGNATURE,
                    repair_operation_type=RepairOperationType.TYPE_ARITY_ALIGNMENT,
                    faulty_element=p_name,
                    raw_log=line.strip(),
                    suggested_repair_hint=(
                        f"In domain 'predicates', check parameter {p_idx} of predicate '{p_name}'. "
                        f"Either declare subtype inheritance in domain 'types', or generalize parameter {p_idx} to the common supertype."
                    )
                ))

    # LLM fault localization if needed
    diagnostic_reports: List[DiagnosticReport] = list(deterministic_reports)

    if not deterministic_reports or len(deterministic_reports) < 2:
        prompt = f"""You are an expert PDDL Diagnostic & Fault Localization Oracle.
Your task is to analyze oracle failure signals against the current PDDL Domain blueprint and fixed Problem instance (P_gold), localize root-cause faults, and produce structured DiagnosticReports.

NATURAL LANGUAGE REQUIREMENTS:
{requirements_text}

CURRENT DOMAIN BLUEPRINT:
```json
{json.dumps(domain_bp, indent=2)}
```

FIXED GROUND-TRUTH PROBLEM PDDL (P_gold — READ-ONLY):
```pddl
{problem_pddl.strip()}
```

RAW ORACLE VERIFICATION ERRORS:
{error_traces_str}

CAUSAL ANALYSIS SUMMARY:
{causal_summary}

{STANDARD_CLASSICAL_PDDL_RULES}
{STANDARD_DIAGNOSTIC_RULES}

Return a valid JSON object strictly matching the DiagnosticAnalysis schema.
"""
        print("[FaultLocalizationNode]: Invoking Diagnostic LLM Agent for fault localization...")
        try:
            analysis, usage = invoke_structured_llm_with_telemetry(
                DiagnosticAnalysis,
                prompt,
                target_model=get_phase_model(3)
            )
            state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
            state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
            state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
            state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)

            for rep in analysis.reports:
                if not any(d.faulty_element == rep.faulty_element and d.error_category == rep.error_category for d in diagnostic_reports):
                    diagnostic_reports.append(rep)
        except Exception as llm_err:
            print(f"[FaultLocalizationNode]: Diagnostic LLM call failed: {llm_err}")

    # Prioritize diagnostic reports
    prioritized_reports, active_tier = prioritize_diagnostic_reports(diagnostic_reports, max_items=5)
    
    # Terminal Observability: Clear structured diagnostic summary
    print("\n" + "=" * 80, flush=True)
    print(f" [FAULT LOCALIZATION]: Layered Diagnosis Prioritized {len(prioritized_reports)} Item(s) (Active Tier: {active_tier})", flush=True)
    print("=" * 80, flush=True)
    if error_traces_str:
        first_err_line = next((l.strip() for l in error_traces_str.splitlines() if l.strip()), "")
        if first_err_line:
            print(f" * Triggering Oracle Signal : {first_err_line[:120]}", flush=True)
    for idx, rep in enumerate(prioritized_reports, 1):
        fe = getattr(rep, "faulty_element", "") or str(rep.get("faulty_element", "") if isinstance(rep, dict) else "")
        cat = getattr(rep, "error_category", "") or str(rep.get("error_category", "") if isinstance(rep, dict) else "")
        op = getattr(rep, "repair_operation_type", "") or str(rep.get("repair_operation_type", "") if isinstance(rep, dict) else "")
        hint = getattr(rep, "suggested_repair_hint", "") or str(rep.get("suggested_repair_hint", "") if isinstance(rep, dict) else "")
        raw_log = getattr(rep, "raw_log", "") or str(rep.get("raw_log", "") if isinstance(rep, dict) else "")
        print(f" * Defect #{idx} | Faulty Target : {fe}", flush=True)
        print(f"     Error Category       : {cat} (Recommended Op: {op})", flush=True)
        if raw_log:
            print(f"     Oracle Evidence      : {raw_log[:140]}", flush=True)
        if hint:
            print(f"     Repair Guidance Hint : {hint}", flush=True)
    print("=" * 80 + "\n", flush=True)

    dumped_prioritized = [r.model_dump() for r in prioritized_reports]
    state["diagnostic_reports"] = dumped_prioritized
    state["formatted_diagnostic_feedback"] = format_diagnostic_feedback(prioritized_reports, active_tier)

    hist_reports = state.get("historical_diagnostic_reports", [])
    for dr in dumped_prioritized:
        if dr not in hist_reports:
            hist_reports.append(dr)
    state["historical_diagnostic_reports"] = hist_reports

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["fault_localization"] = round(latencies.get("fault_localization", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies
    return state
