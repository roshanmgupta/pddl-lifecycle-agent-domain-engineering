import json
import re
import time
from typing import Dict, Any, Set, List
from nodes.schemas.pddl_representation import DomainRepresentation
from nodes.schemas.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES, STANDARD_REPAIR_RULES
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from nodes.pddl_to_ast_parser import extract_pddl_problem_metadata
from tools.pddl_utils import norm_token


def run_repair_node(state: dict) -> dict:
    """Repairs the DomainRepresentation using diagnostic feedback."""
    requirements_text = state.get("requirements", "")
    domain_representation = state.get("pddl_domain_representation", {})
    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if problem_pddl else {}
    formatted_feedback = state.get("formatted_diagnostic_feedback", "")
    verification_errors = state.get("verification_errors", [])
    iteration = state.get("iteration_count", 0) + 1
    state["iteration_count"] = iteration

    feedback_context = formatted_feedback or ("Verification Errors:\n" + "\n".join(verification_errors) if verification_errors else "")

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
                + "\nNote: Do NOT repeat previously rejected modifications. Apply a globally consistent resolution.\n"
            )

    orig_action_map = {
        a.get("action_name"): a
        for a in domain_representation.get("actions", []) if isinstance(a, dict) and a.get("action_name")
    }
    known_action_names = {norm_token(aname): aname for aname in orig_action_map.keys()}
    known_type_names = {norm_token(t) for t in domain_representation.get("types", {}).keys() if t}
    known_pred_names = set()
    for p in domain_representation.get("predicates", []):
        if isinstance(p, str):
            toks = p.strip("() ").split()
            if toks:
                known_pred_names.add(norm_token(toks[0]))

    target_elements = set()
    for r in state.get("diagnostic_reports", []):
        fe = r.get("faulty_element") if isinstance(r, dict) else getattr(r, "faulty_element", "")
        if fe:
            target_elements.add(str(fe).strip())

    is_schema_fault = False
    flagged_predicates = set()
    target_actions = set()

    for t in target_elements:
        nt = norm_token(t)
        if nt in ("types", "predicates", "constants") or nt in known_type_names or nt in known_pred_names:
            is_schema_fault = True
        if nt in known_action_names:
            target_actions.add(known_action_names[nt])
        if nt in known_pred_names:
            flagged_predicates.add(nt)

    for r in state.get("diagnostic_reports", []):
        hint = (r.get("suggested_repair_hint") if isinstance(r, dict) else getattr(r, "suggested_repair_hint", "")) or ""
        log = (r.get("raw_log") if isinstance(r, dict) else getattr(r, "raw_log", "")) or ""
        text = (hint + " " + log).lower()
        if "predicate" in text and ("not found" in text or "missing" in text or "undeclared" in text):
            is_schema_fault = True
        if "type" in text and ("unknown" in text or "missing" in text or "undeclared" in text):
            is_schema_fault = True
        for nt, orig_a in known_action_names.items():
            if orig_a.lower() in text or nt in text:
                target_actions.add(orig_a)

    raw_err_text = " ".join(str(e) for e in verification_errors).lower()
    if any(kw in raw_err_text for kw in ("unknown type", "type problem", "type-checking", "type signature", "syntax error", "undeclared")):
        is_schema_fault = True

    if flagged_predicates:
        for aname, a in orig_action_map.items():
            conds = a.get("preconditions", []) + a.get("effects", [])
            for c in conds:
                tokens = {norm_token(tok) for tok in re.findall(r'[a-zA-Z0-9_\-]+', str(c))}
                if tokens.intersection(flagged_predicates):
                    target_actions.add(aname)
                    break

    target_guidance = ""
    if is_schema_fault:
        schema_symbols = ", ".join(sorted(t for t in target_elements if t)) or "global type / predicate signatures"
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
    All other actions in the domain representation are already verified and correct.
    Do NOT modify, alter, add, or delete any preconditions or effects in actions other than {target_list_str}!
    Copy all other actions EXACTLY as they appear in the CURRENT DOMAIN REPRESENTATION.
    """

    fixed_contract_guidance = ""
    if state.get("fixed_signatures") or (state.get("reference_domain_pddl") and not state.get("is_synthetic_repair")):
        fixed_contract_guidance = (
            "\n    FIXED SIGNATURE & CONTRACT INVARIANT:\n"
            "    - The domain types hierarchy, constants, predicates, and action parameter signatures are FIXED CONTRACTS.\n"
            "    - Do NOT add, remove, or modify types, constants, predicates, or action parameter signatures.\n"
            "    - Repair ONLY the :precondition and :effect lists of the actions using ONLY declared variables.\n"
        )

    prompt = f"""
    You are an expert PDDL Knowledge Engineer specializing in formal domain model repair.
    Your task is to repair the existing PDDL Domain representation (D_gen) to resolve the diagnostic errors reported by symbolic oracles against the fixed ground-truth problem instance (P_gold).
    Because the problem instance is held fixed for formal verification, you must ONLY repair and output the DomainRepresentation JSON object ("domain_name", "requirements", "types", "constants", "predicates", "actions").
    Treat the provided domain representation as a working draft to surgically edit, not as disposable context.
    Preserve all elements that are already correct and apply the smallest set of changes needed to satisfy oracle feedback.
    {target_guidance}
    {fixed_contract_guidance}

    Original Requirements Text & Fixed Problem Contract:
    {requirements_text}

    CURRENT DOMAIN REPRESENTATION (D_gen — TO REPAIR):
    ```json
    {json.dumps(domain_representation, indent=2)}
    ```

    FIXED READ-ONLY TARGET PROBLEM PDDL (P_target — DO NOT MODIFY):
    ```pddl
    {problem_pddl.strip()}
    ```

    {feedback_context}
    {causal_context}
    {history_context}

    {STANDARD_CLASSICAL_PDDL_RULES}
    {STANDARD_REPAIR_RULES}

    Produce ONLY the updated valid JSON object conforming to the DomainRepresentation schema.
    """

    print("[Repair Node]: Executing domain representation repair based on diagnostic feedback...")

    # Observability: record exactly what feedback is handed to the repair LLM this iteration
    feedback_log = list(state.get("repair_feedback_log", []) or [])
    feedback_log.append({
        "iteration": iteration,
        "feedback_source": "raw_oracle_output" if state.get("skip_fault_localization") else "layered_fault_localization",
        "target_actions": sorted(target_actions),
        "is_schema_fault": is_schema_fault,
        "diagnostic_feedback": feedback_context,
        "causal_context": causal_context,
        "history_context": history_context,
        "full_prompt": prompt,
    })
    state["repair_feedback_log"] = feedback_log

    start_t = time.time()

    try:
        repaired_domain_representation, usage = invoke_structured_llm_with_telemetry(
            DomainRepresentation,
            prompt,
            target_model=get_phase_model(3)
        )
        dom_dict = repaired_domain_representation.model_dump()
        if prob_meta.get("domain_name"):
            dom_dict["domain_name"] = prob_meta["domain_name"]

        # Preserve non-target actions
        if target_actions and not is_schema_fault:
            norm_targets = {norm_token(t) for t in target_actions if t}
            preserved_actions = []
            for a in dom_dict.get("actions", []):
                aname = a.get("action_name", "") if isinstance(a, dict) else ""
                is_target = norm_token(aname) in norm_targets
                if aname and (not is_target) and aname in orig_action_map:
                    preserved_actions.append(orig_action_map[aname])
                else:
                    preserved_actions.append(a)
            dom_dict["actions"] = preserved_actions

        # Restore reference signatures if active (H1 fixed-signature elicitation only; never leak D_gold AST in H2 synthetic repair)
        if state.get("fixed_signatures") or (state.get("reference_domain_pddl") and not state.get("is_synthetic_repair")):
            ref_dom_pddl = state.get("reference_domain_pddl") or state.get("ground_truth_domain_pddl")
            if ref_dom_pddl:
                from nodes.pddl_to_ast_parser import parse_pddl_domain_to_representation, clean_representation_expression, alpha_convert_action_variables
                ref_bp = parse_pddl_domain_to_representation(ref_dom_pddl)
                dom_dict["types"] = ref_bp.get("types", {})
                dom_dict["constants"] = ref_bp.get("constants", {})
                dom_dict["predicates"] = ref_bp.get("predicates", [])
                canonical_actions = {
                    norm_token(a.get("action_name")): a
                    for a in ref_bp.get("actions", []) if isinstance(a, dict)
                }
                aligned_actions = []
                for act in dom_dict.get("actions", []):
                    nat = norm_token(act.get("action_name"))
                    if nat in canonical_actions:
                        canon_act = canonical_actions[nat]
                        act["action_name"] = canon_act["action_name"]
                        act["parameters"] = canon_act["parameters"]
                        raw_pre = [clean_representation_expression(p) for p in act.get("preconditions", []) if clean_representation_expression(p)]
                        raw_eff = [clean_representation_expression(p) for p in act.get("effects", []) if clean_representation_expression(p)]
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
                dom_dict["actions"] = aligned_actions

        state["pddl_domain_representation"] = dom_dict

        # Telemetry
        state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
        state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
        state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
        state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)
        
        # Terminal Observability: Compute and display repaired representation diff
        print("\n" + "=" * 80, flush=True)
        print(f" [REPAIR NODE]: Domain Representation AST Repaired (Iteration {iteration})", flush=True)
        print("=" * 80, flush=True)

        orig_acts = {
            a.get("action_name"): a
            for a in domain_representation.get("actions", [])
            if isinstance(a, dict) and a.get("action_name")
        }
        new_acts = {
            a.get("action_name"): a
            for a in dom_dict.get("actions", [])
            if isinstance(a, dict) and a.get("action_name")
        }

        modified_any = False
        for aname, n_act in new_acts.items():
            if aname not in orig_acts:
                print(f" * [+] Added Action Schema : '{aname}'", flush=True)
                modified_any = True
                continue
            o_act = orig_acts[aname]
            o_pre = set(o_act.get("preconditions", []))
            n_pre = set(n_act.get("preconditions", []))
            o_eff = set(o_act.get("effects", []))
            n_eff = set(n_act.get("effects", []))

            added_pre = n_pre - o_pre
            removed_pre = o_pre - n_pre
            added_eff = n_eff - o_eff
            removed_eff = o_eff - n_eff

            if added_pre or removed_pre or added_eff or removed_eff:
                modified_any = True
                print(f" * [ACTION REPAIRED] '{aname}':", flush=True)
                for p in sorted(removed_pre):
                    print(f"     [-] Removed Precondition : {p}", flush=True)
                for p in sorted(added_pre):
                    print(f"     [+] Added Precondition   : {p}", flush=True)
                for e in sorted(removed_eff):
                    print(f"     [-] Removed Effect       : {e}", flush=True)
                for e in sorted(added_eff):
                    print(f"     [+] Added Effect         : {e}", flush=True)

        for aname in orig_acts:
            if aname not in new_acts:
                print(f" * [-] Removed Action Schema : '{aname}'", flush=True)
                modified_any = True

        orig_preds = set(domain_representation.get("predicates", []))
        new_preds = set(dom_dict.get("predicates", []))
        if orig_preds != new_preds:
            added_p = new_preds - orig_preds
            removed_p = orig_preds - new_preds
            if added_p or removed_p:
                modified_any = True
                print(" * [PREDICATES REPAIRED]:", flush=True)
                for p in sorted(removed_p):
                    print(f"     [-] Removed Predicate    : {p}", flush=True)
                for p in sorted(added_p):
                    print(f"     [+] Added Predicate      : {p}", flush=True)

        if not modified_any:
            print(" * Action schemas and predicates preserved without changes.", flush=True)
        print("=" * 80 + "\n", flush=True)

    except Exception as llm_err:
        print(f"[Repair Node ERROR]: LLM structured repair invocation failed: {llm_err}", flush=True)
        state["verification_errors"] = [f"Repair LLM Exception: {llm_err}"]

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["repair"] = round(latencies.get("repair", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies
    return state
