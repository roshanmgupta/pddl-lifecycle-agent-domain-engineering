import json
import time
from schemas.pddl_blueprint import DomainBlueprint
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES, STANDARD_REPAIR_RULES
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from tools.blueprint_parser import extract_pddl_problem_metadata


def run_repair_node(state: dict) -> dict:
    """
    Phase 3.2 Repair Node: Performs targeted repair on the PDDL DomainBlueprint (D_gen)
    against the fixed ground-truth problem instance (P_gold) based on diagnostic reports
    from the triage node.
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

    target_elements = set()
    for r in state.get("diagnostic_reports", []):
        fe = r.get("faulty_element") if isinstance(r, dict) else getattr(r, "faulty_element", "")
        if fe:
            target_elements.add(str(fe).strip())
    
    target_guidance = ""
    if target_elements and not any(t.lower() in ("types", "predicates", "constants") for t in target_elements):
        target_list_str = ", ".join(sorted(target_elements))
        target_guidance = f"""
    CRITICAL SURGICAL EDITING INVARIANT (TARGET ACTION SCHEMA: {target_list_str}):
    Symbolic oracle diagnostics localized the fault strictly to: {target_list_str}.
    All other actions in the domain blueprint are already verified and correct.
    Do NOT modify, alter, add, or delete any preconditions or effects in actions other than {target_list_str}!
    Copy all other actions EXACTLY as they appear in the CURRENT DOMAIN BLUEPRINT.
    """

    prompt = f"""
    You are an expert PDDL Knowledge Engineer specializing in formal domain model repair.
    Your task is to repair the existing PDDL Domain blueprint (D_gen) to resolve the diagnostic errors reported by symbolic oracles against the fixed ground-truth problem instance (P_gold).
    Because the problem instance (P_gold) is held fixed for formal verification, you must ONLY repair and output the DomainBlueprint JSON object ("domain_name", "requirements", "types", "constants", "predicates", "actions").
    Treat the provided domain blueprint as a working draft to surgically edit, not as disposable context.
    Preserve all elements that are already correct and apply the smallest set of changes needed to satisfy oracle feedback.
    {target_guidance}

    Original Requirements Text & Fixed Problem Contract:
    {requirements_text}

    CURRENT DOMAIN BLUEPRINT (D_gen — TO REPAIR):
    ```json
    {json.dumps(domain_blueprint, indent=2)}
    ```

    FIXED READ-ONLY PROBLEM PDDL (P_gold — DO NOT MODIFY):
    ```pddl
    {problem_pddl.strip()}
    ```

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

        # Surgical Isolation: Preserve non-diagnosed actions against stochastic drift
        if target_elements and not any(t.lower() in ("types", "predicates", "constants") for t in target_elements):
            import re
            def _norm_action_token(s: str) -> str:
                clean = re.sub(r"^(domain\.)?actions?\.", "", str(s).strip("'\"` "), flags=re.IGNORECASE)
                return clean.lower().replace("-", "").replace("_", "")

            norm_targets = {_norm_action_token(t) for t in target_elements if t}
            orig_action_map = {
                (a.get("action_name") or a.get("name")): a 
                for a in domain_blueprint.get("actions", []) if isinstance(a, dict)
            }
            preserved_actions = []
            for a in dom_dict.get("actions", []):
                aname = a.get("action_name") or a.get("name") if isinstance(a, dict) else ""
                norm_aname = _norm_action_token(aname)
                is_target = any(norm_aname == nt or nt in norm_aname or norm_aname in nt for nt in norm_targets)
                if aname and (not is_target) and aname in orig_action_map:
                    preserved_actions.append(orig_action_map[aname])
                else:
                    preserved_actions.append(a)
            dom_dict["actions"] = preserved_actions

        state["pddl_domain_blueprint"] = dom_dict

        # Update Telemetry Metrics
        state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
        state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
        state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
        state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)
        print("[Repair Node]: LLM domain repair successfully completed.")
        orig_actions_dict = {
            (a.get("action_name") or a.get("name")): a 
            for a in domain_blueprint.get("actions", []) if isinstance(a, dict)
        }
        modified_actions = []
        preserved_actions_list = []
        for a in dom_dict.get("actions", []):
            aname = a.get("action_name") or a.get("name") if isinstance(a, dict) else ""
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
