"""
nodes/evolution.py
Phase 4: Classical PDDL 2.1 Domain Model Evolution & Action Model Refinement.

Grounding in Classical Automated Planning (Fox & Long 2003; Haslum et al. 2019;
McCluskey, Vaquero, & Vallati 2017; Silva, Silva, & Vaquero 2020; Georgievski 2023):
Domain Evolution is the formal process of extending an existing baseline state-transition
model Sigma = (S, A, gamma) to incorporate new operational capabilities (action schemas,
predicates, types) while strictly preserving plan reachability (solvability preservation)
across the canonical benchmark problem distribution.
"""

import json
import time
from typing import Dict, Any, List, Optional
from schemas.pddl_blueprint import DomainBlueprint, PddlActionSchema
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES
from tools.blueprint_parser import (
    extract_pddl_problem_metadata,
    parse_pddl_domain_to_blueprint
)


def run_evolution_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 4 Domain Evolution Node:
    Synthesizes an extended action model (DomainBlueprint) by performing an additive
    AST delta over a baseline domain schema to satisfy new operational requirements
    while preserving the baseline transition corridor for benchmark problems.
    """
    start_t = time.time()
    requirements_text = state.get("requirements", "")
    baseline_domain_pddl = state.get("initial_domain_pddl") or state.get("reference_domain_pddl") or ""
    existing_domain_bp = state.get("pddl_domain_blueprint")
    target_problem_pddl = (
        state.get("evolution_target_problem_pddl")
        or state.get("generated_problem_pddl")
        or state.get("initial_problem_pddl")
        or ""
    )
    formatted_feedback = state.get("formatted_diagnostic_feedback", "")
    verification_errors = state.get("verification_errors", [])

    # Step 1: Ensure Baseline DomainBlueprint AST is available
    if not existing_domain_bp and baseline_domain_pddl:
        print("[Evolution Node]: Parsing baseline domain PDDL into baseline DomainBlueprint AST...")
        existing_domain_bp = parse_pddl_domain_to_blueprint(baseline_domain_pddl)
        state["pddl_domain_blueprint"] = existing_domain_bp

    if not state.get("initial_pddl_domain_blueprint") and existing_domain_bp:
        state["initial_pddl_domain_blueprint"] = existing_domain_bp

    target_meta = extract_pddl_problem_metadata(target_problem_pddl) if target_problem_pddl else {}
    target_dname = (
        (existing_domain_bp.get("domain_name") if isinstance(existing_domain_bp, dict) else getattr(existing_domain_bp, "domain_name", None))
        or target_meta.get("domain_name")
        or "evolved_domain"
    )

    baseline_json = json.dumps(
        existing_domain_bp if isinstance(existing_domain_bp, dict) else (existing_domain_bp.model_dump() if hasattr(existing_domain_bp, "model_dump") else {}),
        indent=2
    ) if existing_domain_bp else "{}"

    # Step 2: Format Diagnostic Feedback context (if re-entering during closed-loop refinement)
    feedback_context = ""
    if formatted_feedback:
        feedback_context = f"\nDiagnostic Feedback from Oracles (Fault Localization Findings to Resolve):\n{formatted_feedback}\n"
    elif verification_errors:
        feedback_context = f"\nVerification Errors from Symbolic Oracles to Resolve:\n{verification_errors}\n"

    objects_str = json.dumps(target_meta.get("objects", {}))
    init_str = json.dumps(target_meta.get("initial_state", []))
    goal_str = json.dumps(target_meta.get("goal_state", []))

    # Step 3: Construct Classical Planning Action Model Evolution Prompt
    prompt = f"""You are an expert AI Planning Knowledge Engineer specialized in Classical PDDL 2.1 Action Model Evolution and Refinement (Fox & Long 2003, Haslum et al. 2019, McCluskey et al. 2017, Silva et al. 2020).

Your task is to evolve an existing baseline planning domain model (Sigma_base) into an extended domain model (Sigma_evolved) conforming strictly to the DomainBlueprint JSON schema.

=== BASELINE DOMAIN BLUEPRINT (D_base) ===
```json
{baseline_json}
```

=== CAPABILITY EXTENSION REQUIREMENTS (Delta Specification) ===
{requirements_text}

=== TARGET PLANNING TASK CONTRACT (P_target) ===
Domain Name: {target_dname}
Target Problem Objects: {objects_str}
Target Problem Initial State: {init_str}
Target Problem Goal State: {goal_str}
{feedback_context}

=== FORMAL CLASSICAL PLANNING EVOLUTION PRINCIPLES (MANDATORY) ===
1. ADDITIVE SCHEMA & PREDICATE EXTENSION (CONSERVATIVE EXTENSION):
   - Output action count MUST equal or exceed the baseline input action count ({len(existing_domain_bp.get('actions', [])) if isinstance(existing_domain_bp, dict) else 0}).
   - You MUST retain all valid baseline action schemas from D_base. NEVER drop, delete, or rename baseline actions.
   - You MUST retain all baseline predicate declarations from D_base with their exact parameter signatures and types. NEVER drop, delete, rename, or merge existing baseline predicates. (For example, if the baseline domain defines separate predicates for different object roles, such as agent locations vs item locations, both distinct predicates MUST remain present).
   - Synthesize the new action schemas required to enable the new capability described in the requirements.
   - Add all new relational predicate signatures required by the new capability to domain 'predicates' with strongly typed parameters.
   - If new categories are introduced, declare their supertype inheritance under domain 'types' (rooted under 'object' or an existing domain supertype).

2. SOLVABILITY PRESERVATION ACROSS REFERENCE PROBLEM SUITE:
   - In Classical Planning, adding preconditions strictly shrinks the reachable state space.
   - NEVER add new restrictive preconditions to existing baseline actions if those conditions are absent from baseline problem instances (doing so causes reachability deadlock on all benchmark problems).
   - If the new requirement specifies that certain conditions apply only to a new capability (e.g., specialized tools, express vehicles, or heavy items):
     a) Implement the capability as a DEDICATED NEW ACTION SCHEMA (e.g. '<action_name>_express' or '<action_name>_specialized'), OR
     b) Specialize parameter types on the new action, leaving the baseline general action intact for standard tasks.

3. FIRST-ORDER STRIPS WELL-FORMEDNESS:
   - Requirement flags MUST remain strictly [":strips", ":typing"].
   - Every parameter variable name in action preconditions and effects MUST start with '?' and be declared in action 'parameters'.
   - PROHIBITION OF DUMMY LITERALS: Never write '(true)' or '(false)' in preconditions or effects.
   - NO NEGATIVE PRECONDITIONS: In classical STRIPS, negative literals like '(not (...))' are strictly forbidden in preconditions.
   - Symmetric State Transitions: When an action consumes a state, assert '(not (P ...))'; when an action establishes a state, assert '(P ...)'.

Return a single, valid JSON object conforming strictly to the DomainBlueprint schema.
"""

    model_name = get_phase_model(4)
    print(f"[Evolution Node]: Invoking Phase 4 Model '{model_name}' for Action Model Evolution...")
    evolved_bp, usage = invoke_structured_llm_with_telemetry(
        schema=DomainBlueprint,
        prompt=prompt,
        target_model=model_name
    )

    # Step 4: Guard - Baseline Action & Predicate Preservation Check
    base_actions = (
        existing_domain_bp.get("actions", [])
        if isinstance(existing_domain_bp, dict)
        else getattr(existing_domain_bp, "actions", [])
    )
    evolved_actions = evolved_bp.actions or []

    # Map existing action names
    base_act_map = {
        (a.get("action_name") if isinstance(a, dict) else getattr(a, "action_name", "")): a
        for a in base_actions
    }
    evolved_act_names = {a.action_name for a in evolved_actions}

    # If the LLM omitted any baseline action, restore it to guarantee action preservation invariant
    missing_actions = []
    for b_name, b_schema in base_act_map.items():
        if b_name and b_name not in evolved_act_names:
            missing_actions.append(b_schema)

    if missing_actions:
        print(f"[Evolution Node Warning]: LLM omitted {len(missing_actions)} baseline action(s): {[a.get('action_name') if isinstance(a, dict) else getattr(a, 'action_name') for a in missing_actions]}. Restoring them to enforce action preservation invariant.")
        for ma in missing_actions:
            if isinstance(ma, dict):
                evolved_bp.actions.append(PddlActionSchema(**ma))
            else:
                evolved_bp.actions.append(ma)

    # Guard - Baseline Predicate Preservation Check (Conservative Extension)
    base_predicates = (
        existing_domain_bp.get("predicates", [])
        if isinstance(existing_domain_bp, dict)
        else getattr(existing_domain_bp, "predicates", [])
    )
    evolved_predicates = evolved_bp.predicates or []

    def _extract_pred_symbol(p_item):
        if isinstance(p_item, str):
            clean = p_item.strip("() ").split()
            return clean[0].lower() if clean else ""
        if hasattr(p_item, "name"):
            return getattr(p_item, "name", "").lower()
        if isinstance(p_item, dict):
            return p_item.get("name", "").lower()
        return ""

    evolved_pred_symbols = {_extract_pred_symbol(p) for p in evolved_predicates if _extract_pred_symbol(p)}
    missing_predicates = []
    for bp in base_predicates:
        sym = _extract_pred_symbol(bp)
        if sym and sym not in evolved_pred_symbols:
            missing_predicates.append(bp)

    if missing_predicates:
        missing_names = [_extract_pred_symbol(p) for p in missing_predicates]
        print(f"[Evolution Node Warning]: LLM omitted {len(missing_predicates)} baseline predicate(s): {missing_names}. Restoring them to enforce predicate preservation invariant.")
        for mp in missing_predicates:
            evolved_bp.predicates.append(mp)

    elapsed = time.time() - start_t
    latencies = state.get("node_latencies", {})
    latencies["evolution"] = round(latencies.get("evolution", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies

    # Accumulate token usage
    state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
    state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
    state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
    state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("cost_usd", 0.0), 6)

    evolved_dict = evolved_bp.model_dump()
    state["pddl_domain_blueprint"] = evolved_dict
    state["evolution_iteration_count"] = state.get("evolution_iteration_count", 0) + 1

    print(f"[Evolution Node]: Successfully synthesized Evolved Domain Blueprint '{evolved_dict.get('domain_name')}' with {len(evolved_dict.get('actions', []))} action(s) in {round(elapsed, 2)}s.")
    return state
