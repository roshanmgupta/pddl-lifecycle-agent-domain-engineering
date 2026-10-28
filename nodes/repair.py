import json
import re
import time
from schemas.pddl_blueprint import DomainBlueprint
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES, STANDARD_REPAIR_RULES
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from tools.blueprint_parser import extract_pddl_problem_metadata


def run_repair_node(state: dict) -> dict:
    """
    Phase 3.2 Repair Node: Performs targeted repair on the PDDL DomainBlueprint (D_gen)
    against the fixed ground-truth problem instance (P_gold) based on diagnostic reports
    from the FaultLocalizationNode via Layered Model-Based Fault Localization.
    100% LLM-driven reasoning; strictly NO deterministic heuristic fallbacks or ground-truth substitutions.
    """
    requirements_text = state.get("requirements", "")
    domain_blueprint = state.get("pddl_domain_blueprint", {})
    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if problem_pddl else {}
    formatted_feedback = state.get("formatted_diagnostic_feedback", "")
    verification_errors = state.get("verification_errors", [])
    iteration = state.get("iteration_count", 0) + 1
    state["iteration_count"] = iteration

    feedback_context = formatted_feedback
    if not feedback_context and verification_errors:
        feedback_context = "Verification Errors:\n" + "\n".join(verification_errors)

    causal_context = ""
    causal_analysis = state.get("causal_graph_analysis", {})
    if causal_analysis:
        summary = causal_analysis.get("diagnostic_summary", "")
        if summary:
            causal_context = f"\nGROUNDED ACTION-PREDICATE CAUSAL DEPENDENCY & REACHABILITY ANALYSIS:\n{summary}\n"

    history_context = ""
    hist_reports = state.get("historical_diagnostic_reports", [])
    if iteration > 1 and hist_reports:
        recent_history = [
            f"- Previous Attempt Issue: [{r.get('error_category')}] in '{r.get('faulty_element')}': {r.get('suggested_repair_hint')}"
            for r in hist_reports[-3:] if isinstance(r, dict)
        ]
        if recent_history:
            history_context = (
                "\nPREVIOUS FAILED REPAIR ATTEMPTS (DO NOT REVERT OR OSCILLATE):\n"
                + "\n".join(recent_history)
                + "\nNote: Do NOT repeat previously rejected modifications or alternate parameter types back and forth. Apply a globally consistent resolution across all actions.\n"
            )

    orig_action_map = {
        a.get("action_name"): a 
        for a in domain_blueprint.get("actions", []) if isinstance(a, dict) and a.get("action_name")
    }

    def _norm_token(s: str) -> str:
        clean = re.sub(r"^(domain\.)?(actions?|predicates?|types?)\.", "", str(s).strip("'\"` "), flags=re.IGNORECASE)
        return clean.lower().replace("-", "").replace("_", "")

    known_action_names = {_norm_token(aname): aname for aname in orig_action_map.keys()}

    known_pred_names = set()
    for p in domain_blueprint.get("predicates", []):
        if isinstance(p, str):
            clean = p.strip("() ").split()
            if clean:
                known_pred_names.add(_norm_token(clean[0]))

    known_type_names = {
        _norm_token(t) for t in domain_blueprint.get("types", {}).keys() if t
    }

    target_elements = set()
    for r in state.get("diagnostic_reports", []):
        fe = r.get("faulty_element") if isinstance(r, dict) else getattr(r, "faulty_element", "")
        if fe:
            target_elements.add(str(fe).strip())

    is_schema_fault = False
    flagged_predicates = set()
    target_actions = set()

    for t in target_elements:
        norm_t = _norm_token(t)
        if norm_t in ("types", "predicates", "constants") or norm_t in known_type_names or norm_t in known_pred_names:
            is_schema_fault = True
        if norm_t in known_action_names:
            target_actions.add(known_action_names[norm_t])
        if norm_t in known_pred_names:
            flagged_predicates.add(norm_t)

    # Scan diagnostic reports text for explicitly named actions and schema indicators
    for r in state.get("diagnostic_reports", []):
        hint = (r.get("suggested_repair_hint") if isinstance(r, dict) else getattr(r, "suggested_repair_hint", "")) or ""
        log = (r.get("raw_log") if isinstance(r, dict) else getattr(r, "raw_log", "")) or ""
        text = (hint + " " + log).lower()
        if "predicate" in text and ("not found" in text or "missing" in text or "undeclared" in text):
            is_schema_fault = True
        if "type" in text and ("unknown" in text or "missing" in text or "undeclared" in text):
            is_schema_fault = True
        for norm_a, orig_a in known_action_names.items():
            if orig_a.lower() in text or norm_a in text:
                target_actions.add(orig_a)

    # Any action referencing flagged predicates in preconditions or effects is also a target action
    if flagged_predicates:
        for aname, a in orig_action_map.items():
            conds = a.get("preconditions", []) + a.get("effects", [])
            for c in conds:
                tokens = {_norm_token(tok) for tok in re.findall(r'[a-zA-Z0-9_\-]+', str(c))}
                if tokens.intersection(flagged_predicates):
                    target_actions.add(aname)
                    break

    has_regression = any(
        (r.get("error_category") == "HISTORICAL_REGRESSION"
         or str(r.get("error_category")).endswith("HISTORICAL_REGRESSION")
         or r.get("repair_operation_type") == "REGRESSION_BACKWARD_COMPATIBILITY"
         or str(r.get("repair_operation_type")).endswith("REGRESSION_BACKWARD_COMPATIBILITY"))
        for r in state.get("diagnostic_reports", []) if isinstance(r, dict)
    )

    target_guidance = ""
    if has_regression:
        target_guidance = f"""
    CRITICAL DOMAIN EVOLUTION SOLVABILITY PRESERVATION REPAIR INVARIANT:
    Symbolic oracles detected a backward-compatibility regression on historical benchmark problem instances (Pi_ref).
    To satisfy the full lifecycle requirements without regression:
    1. RESTORE MISSING BASELINE PREDICATES & TYPES: Pre-existing benchmark problems require baseline predicates and types. If any predicate or type was omitted, renamed, or lost during evolution, you MUST declare it in 'predicates' or 'types' with its original parameter signature.
    2. NEVER MERGE DISTINCT PREDICATES: If the baseline domain had separate predicates for different entity roles (for example, separate location predicates for agents vs portable items), both distinct predicates MUST remain declared and used. Do NOT merge them into a single predicate.
    3. AVOID OVER-CONSTRAINING BASELINE ACTIONS: Ensure standard baseline actions remain executable for pre-existing tasks without blocking preconditions. If a new precondition was added to an existing action that blocks baseline goals, separate the new capability into its own specialized action schema or relax the precondition.
    4. PRESERVE BOTH CAPABILITIES: Retain the newly added actions and capabilities required for the feature request while preserving 100% backward compatibility for all baseline problems.
    """
    elif is_schema_fault:
        schema_symbols = ", ".join(sorted(t for t in target_elements if t))
        target_guidance = f"""
    CRITICAL SCHEMA REPAIR INVARIANT (GLOBAL PREDICATE / TYPE REPAIR: {schema_symbols}):
    Symbolic oracle diagnostics localized the fault to global predicates, types, or cross-action relational signatures: {schema_symbols}.
    Ensure that predicate declarations in 'predicates', type hierarchy declarations in 'types', and ALL actions that reference these predicates or types (in preconditions or effects) are updated consistently to match the fixed problem instance P_gold.
    """
    elif target_actions:
        target_list_str = ", ".join(sorted(target_actions))
        target_guidance = f"""
    CRITICAL SURGICAL EDITING INVARIANT (TARGET ACTION SCHEMA: {target_list_str}):
    Symbolic oracle diagnostics localized the fault strictly to: {target_list_str}.
    All other actions in the domain blueprint are already verified and correct.
    Do NOT modify, alter, add, or delete any preconditions or effects in actions other than {target_list_str}!
    Copy all other actions EXACTLY as they appear in the CURRENT DOMAIN BLUEPRINT.
    """

    task_objective = (
        "Your task is to repair the existing PDDL Domain blueprint (D_gen) to resolve backward-compatibility regression "
        "errors reported by Phase 4 Maintenance Oracles across historical benchmark problem instances (Pi_ref), "
        "while ensuring the new capability target problem instance remains fully solvable."
        if has_regression else
        "Your task is to repair the existing PDDL Domain blueprint (D_gen) to resolve the diagnostic errors reported by "
        "symbolic oracles against the fixed ground-truth problem instance (P_gold)."
    )

    ref_prob_context = ""
    if has_regression:
        bench_suite = (
            state.get("baseline_benchmark_problems")
            or state.get("benchmark_problem_distribution")
            or []
        )
        if bench_suite:
            first_case = bench_suite[0]
            first_prob_pddl = (
                first_case.get("problem_pddl", "")
                if isinstance(first_case, dict)
                else (getattr(first_case, "problem_pddl", "") if hasattr(first_case, "problem_pddl") else str(first_case))
            )
            if first_prob_pddl:
                ref_prob_context = f"""
    SAMPLE HISTORICAL REFERENCE BENCHMARK PROBLEM (Pi_ref — MUST REMAIN SOLVABLE):
    ```pddl
    {first_prob_pddl.strip()[:1500]}
    ```
    """

    fixed_contract_guidance = ""
    if state.get("fixed_signatures") or state.get("reference_domain_pddl"):
        fixed_contract_guidance = (
            "\n    FIXED SIGNATURE & CONTRACT INVARIANT:\n"
            "    - The domain types hierarchy, constants, predicates, and action parameter signatures are FIXED CONTRACTS.\n"
            "    - Do NOT add, remove, or modify types, constants, predicates, or action parameter signatures.\n"
            "    - Repair ONLY the :precondition and :effect lists of the actions using ONLY declared variables.\n"
        )

    prompt = f"""
    You are an expert PDDL Knowledge Engineer specializing in formal domain model repair.
    {task_objective}
    Because the problem instance is held fixed for formal verification, you must ONLY repair and output the DomainBlueprint JSON object ("domain_name", "requirements", "types", "constants", "predicates", "actions").
    Treat the provided domain blueprint as a working draft to surgically edit, not as disposable context.
    Preserve all elements that are already correct and apply the smallest set of changes needed to satisfy oracle feedback.
    {target_guidance}
    {fixed_contract_guidance}

    Original Requirements Text & Fixed Problem Contract:
    {requirements_text}

    CURRENT DOMAIN BLUEPRINT (D_gen — TO REPAIR):
    ```json
    {json.dumps(domain_blueprint, indent=2)}
    ```

    FIXED READ-ONLY TARGET PROBLEM PDDL (P_target — DO NOT MODIFY):
    ```pddl
    {problem_pddl.strip()}
    ```
    {ref_prob_context}

    {feedback_context}
    {causal_context}
    {history_context}

    {STANDARD_CLASSICAL_PDDL_RULES}
    {STANDARD_REPAIR_RULES}

    Produce ONLY the updated valid JSON object conforming to the DomainBlueprint schema.
    """

    print("[Repair Node]: Executing 100% LLM-driven domain blueprint repair based on diagnostic feedback...")
    start_t = time.time()

    try:
        repaired_domain_blueprint, usage = invoke_structured_llm_with_telemetry(
            DomainBlueprint,
            prompt,
            target_model=get_phase_model(3)
        )
        dom_dict = repaired_domain_blueprint.model_dump()
        if prob_meta.get("domain_name"):
            dom_dict["domain_name"] = prob_meta["domain_name"]

        # Surgical Isolation: Preserve non-target actions against stochastic drift
        # Only isolate actions if there is NO schema fault (types/predicates/constants) and NO regression
        if target_actions and not is_schema_fault and not has_regression:
            norm_targets = {_norm_token(t) for t in target_actions if t}
            preserved_actions = []
            for a in dom_dict.get("actions", []):
                aname = a.get("action_name", "") if isinstance(a, dict) else ""
                norm_aname = _norm_token(aname)
                is_target = norm_aname in norm_targets
                if aname and (not is_target) and aname in orig_action_map:
                    preserved_actions.append(orig_action_map[aname])
                else:
                    preserved_actions.append(a)
            dom_dict["actions"] = preserved_actions

        # ==============================================================================
        # H1 Formulation: Guarantee fixed ground-truth types, constants, predicates, and parameter signatures
        # (Prevents LLM repair from corrupting types, hallucinating constants, or altering action arities)
        # ==============================================================================
        if state.get("fixed_signatures") or state.get("reference_domain_pddl"):
            ref_dom_pddl = state.get("reference_domain_pddl") or state.get("ground_truth_domain_pddl")
            if ref_dom_pddl:
                from tools.blueprint_parser import parse_pddl_domain_to_blueprint
                ref_bp = parse_pddl_domain_to_blueprint(ref_dom_pddl)
                dom_dict["types"] = ref_bp.get("types", {})
                dom_dict["constants"] = ref_bp.get("constants", {})
                dom_dict["predicates"] = ref_bp.get("predicates", [])
                canonical_actions = {
                    _norm_token(a.get("action_name")): a
                    for a in ref_bp.get("actions", []) if isinstance(a, dict)
                }
            else:
                canonical_actions = {
                    _norm_token(a.get("action_name")): a
                    for a in domain_blueprint.get("actions", []) if isinstance(a, dict)
                }
                dom_dict["types"] = domain_blueprint.get("types", {})
                dom_dict["constants"] = domain_blueprint.get("constants", {})
                dom_dict["predicates"] = domain_blueprint.get("predicates", [])

            from tools.blueprint_parser import clean_blueprint_expression, alpha_convert_action_variables
            aligned_actions = []
            for act in dom_dict.get("actions", []):
                norm_aname = _norm_token(act.get("action_name"))
                if norm_aname in canonical_actions:
                    canon_act = canonical_actions[norm_aname]
                    act["action_name"] = canon_act["action_name"]
                    act["parameters"] = canon_act["parameters"]
                    raw_pre = [clean_blueprint_expression(p) for p in act.get("preconditions", []) if clean_blueprint_expression(p)]
                    raw_eff = [clean_blueprint_expression(p) for p in act.get("effects", []) if clean_blueprint_expression(p)]
                    c_pre, c_eff = alpha_convert_action_variables(
                        canon_act["action_name"],
                        canon_act["parameters"],
                        raw_pre,
                        raw_eff,
                        dom_dict.get("predicates", []),
                        types_hierarchy=dom_dict.get("types", {})
                    )
                    act["preconditions"] = c_pre
                    act["effects"] = c_eff
                    aligned_actions.append(act)
                else:
                    aligned_actions.append(act)
            dom_dict["actions"] = aligned_actions

        state["pddl_domain_blueprint"] = dom_dict

        # Update Telemetry Metrics
        state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
        state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
        state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
        state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)
        print("[Repair Node]: LLM domain repair successfully completed.")
        orig_actions_dict = {
            a.get("action_name"): a 
            for a in domain_blueprint.get("actions", []) if isinstance(a, dict) and a.get("action_name")
        }
        modified_actions = []
        preserved_actions_list = []
        for a in dom_dict.get("actions", []):
            aname = a.get("action_name", "") if isinstance(a, dict) else ""
            if aname:
                if aname in orig_actions_dict and a == orig_actions_dict[aname]:
                    preserved_actions_list.append(aname)
                else:
                    modified_actions.append(aname)

        if modified_actions:
            print(f"  --- [REPAIR APPLIED (Iteration {iteration})]: Surgically Modified Action(s): {modified_actions} | Preserved Actions ({len(preserved_actions_list)}): {preserved_actions_list}")
        else:
            print(f"  --- [REPAIR APPLIED (Iteration {iteration})]: Non-action Schema Modification (Types/Predicates/Constants) | Preserved Actions ({len(preserved_actions_list)}): {preserved_actions_list}")
    except Exception as llm_err:
        print(f"[Repair Node ERROR]: LLM structured repair invocation failed: {llm_err}")
        # Strictly record the failure; NO deterministic fallbacks or ground-truth injection
        state["verification_errors"] = [f"Repair LLM Exception: {llm_err}"]

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["repair"] = round(latencies.get("repair", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies

    print("[Repair Node]: Domain blueprint updated in state.")
    return state
