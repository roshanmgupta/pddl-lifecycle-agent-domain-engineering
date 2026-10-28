import json
import re
import time
from schemas.pddl_blueprint import DomainBlueprint
from config.model_config import get_phase_model, invoke_structured_llm_with_telemetry
from config.pddl_standards import STANDARD_CLASSICAL_PDDL_RULES
from tools.blueprint_parser import extract_pddl_problem_metadata


def run_elicitation_node(state: dict) -> dict:
    """
    Phase 1.2 / 2.1 Node: Parses natural language requirements and the fixed target problem
    contract (P_gold) into a formal PDDL DomainBlueprint (D_gen).
    """
    requirements_text = state.get("requirements", "")
    formatted_feedback = state.get("formatted_diagnostic_feedback", "")
    verification_errors = state.get("verification_errors", [])
    existing_domain_bp = state.get("pddl_domain_blueprint")
    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if problem_pddl else {}

    # Preserve pre-loaded faulty blueprint for synthetic fault repair tasks
    if existing_domain_bp and verification_errors and not formatted_feedback:
        print("[Elicitation Node]: Pre-loaded faulty domain blueprint detected for synthetic repair task. Preserving blueprint for validation & repair loop.")
        return {
            "pddl_domain_blueprint": existing_domain_bp
        }

    feedback_context = ""
    if formatted_feedback:
        feedback_context = f"\n{formatted_feedback}\nPlease resolve all listed diagnostic issues in your revised DomainBlueprint JSON.\n"
        print("Feedback Context for LLM (Fault Localization Format):\n", feedback_context)
    elif verification_errors:
        feedback_context = f"\nPrevious Diagnostic Feedback / Verification Errors to resolve:\n{verification_errors}\n"
        print("Feedback Context for LLM:\n", feedback_context)
    elif existing_domain_bp and existing_domain_bp.get("actions"):
        feedback_context = (
            f"\nBaseline / Reference Domain Blueprint to evolve or extend:\n```json\n"
            f"{json.dumps(existing_domain_bp, indent=2)}\n```\n"
            f"Extend the domain to satisfy the new requirements while preserving backward compatibility with the existing actions, types, and predicates.\n"
        )
        print("[Elicitation Node]: Baseline domain blueprint provided for domain evolution.")

    target_dname = prob_meta.get("domain_name", "generated_domain")

    # ==============================================================================
    # H1 Formulation: Ground-Truth Types, Predicates, and Action Signatures Provided
    # Constrains LLM generation strictly to :preconditions and :effects schemas
    # (Directly addresses professor's mandate to make generated and GT domains comparable)
    # ==============================================================================
    ref_dom_pddl = state.get("reference_domain_pddl") or state.get("ground_truth_domain_pddl")
    use_fixed_signatures = bool(ref_dom_pddl and ref_dom_pddl.strip())

    if use_fixed_signatures:
        from tools.blueprint_parser import parse_pddl_domain_to_blueprint
        from schemas.pddl_blueprint import DomainActionSemantics, PddlActionSchema

        ref_bp = parse_pddl_domain_to_blueprint(ref_dom_pddl)
        target_dname = ref_bp.get("domain_name") or target_dname
        fixed_types = ref_bp.get("types", {})
        fixed_constants = ref_bp.get("constants", {})
        fixed_predicates = ref_bp.get("predicates", [])
        fixed_actions = ref_bp.get("actions", [])
        fixed_reqs = ref_bp.get("requirements", [":strips", ":typing"])

        action_sigs_str = json.dumps([
            {"action_name": a["action_name"], "parameters": a["parameters"]}
            for a in fixed_actions
        ], indent=2)

        prompt = f"""
    You are an expert PDDL Knowledge Engineer.
    Your task is to analyze the following natural language domain requirements and synthesize the :precondition and :effect schemas for the given action signatures.

    THE DOMAIN VOCABULARY AND SIGNATURES ARE FIXED (DO NOT INVENT NEW TYPES, PREDICATES, OR PARAMETERS):
    - Domain Name: {target_dname}
    - Requirements: {fixed_reqs}
    - Types Hierarchy: {json.dumps(fixed_types)}
    - Constants: {json.dumps(fixed_constants)}
    - Formal Predicates: {json.dumps(fixed_predicates, indent=2)}
    - Action Signatures:
{action_sigs_str}

    Requirements Text:
    {requirements_text}
    {feedback_context}

    CRITICAL UNIVERSAL FORMAL SEMANTIC MODELING INVARIANTS:
    1. Exact Parameter Variable Scoping & Placeholder Mapping:
       - For every action, you MUST ONLY use the EXACT variable names declared in that action's parameter signature!
       - The requirements text often refers to entities using placeholder letters (e.g. 'rover A', 'lander B', 'waypoint C', 'waypoint D', 'waypoint E'). You MUST map these placeholders onto the declared parameters (e.g. ?r, ?l, ?p, ?x, ?y) according to their matching types and physical roles.
       - NEVER invent or use variable names (e.g. ?a, ?b, ?c, ?d, ?e) that are not in that specific action's parameter list.
       - Every parameter declared in an action's parameter list should be meaningfully utilized in the preconditions and/or effects.
    2. Predicate Signature & Argument Type Alignment:
       - Every atomic formula (pred ?v1 ?v2 ...) must strictly match a declared predicate symbol from Formal Predicates.
       - Do NOT include inline types (e.g. write '(at ?x ?y)', NEVER '(at ?x - rover ?y - waypoint)').
       - The type of each argument variable in the atomic formula MUST match or be a subtype of the declared predicate parameter type.
    3. Preconditions vs Effects Causal Directionality:
       - Preconditions specify what MUST be true BEFORE the action can execute (e.g. 'I can only ... if it is the case that ...' -> precondition).
       - Effects specify what CHANGES AFTER the action executes:
         * Positive additions: 'Once I ..., it is the case that ...' -> add effect '(pred ...)'.
         * Negative deletions: 'Once I ..., it is not the case anymore that ...' -> delete effect '(not (pred ...))'.
       - NEVER place the intended goal result of an action in its own preconditions.
    4. Monotonicity & Well-Formedness:
       - Do NOT use undeclared predicates, undeclared types, or unbound variables.

    Produce ONLY a valid JSON object matching the DomainActionSemantics schema:
    {{
      "actions": [
        {{
          "action_name": "...",
          "preconditions": ["(...)"],
          "effects": ["(...)"]
        }}
      ]
    }}
    """
        print(f"[Elicitation Node (H1 Fixed Signatures)]: Generating preconditions and effects for {len(fixed_actions)} action(s)...")
        start_t = time.time()
        action_semantics_obj, usage = invoke_structured_llm_with_telemetry(
            DomainActionSemantics, prompt, target_model=get_phase_model(1)
        )
        elapsed = time.time() - start_t

        # Merge generated preconditions and effects into the complete DomainBlueprint
        from tools.blueprint_parser import clean_blueprint_expression, alpha_convert_action_variables
        def _norm_token(s: str) -> str:
            clean = re.sub(r"^(domain\.)?(actions?|predicates?|types?)\.", "", str(s).strip("'\"` "), flags=re.IGNORECASE)
            return clean.lower().replace("-", "").replace("_", "")

        gen_actions_map = {
            _norm_token(a.action_name): a for a in action_semantics_obj.actions
        }
        completed_actions = []
        for fa in fixed_actions:
            aname = fa["action_name"]
            gen_sem = gen_actions_map.get(_norm_token(aname))
            raw_pre = [clean_blueprint_expression(p) for p in (gen_sem.preconditions if gen_sem else []) if clean_blueprint_expression(p)]
            raw_eff = [clean_blueprint_expression(p) for p in (gen_sem.effects if gen_sem else []) if clean_blueprint_expression(p)]
            # Universal Alpha-Conversion to align dummy variables to declared action parameters
            conv_pre, conv_eff = alpha_convert_action_variables(
                aname,
                fa["parameters"],
                raw_pre,
                raw_eff,
                fixed_predicates,
                types_hierarchy=fixed_types
            )
            completed_actions.append(PddlActionSchema(
                action_name=aname,
                parameters=fa["parameters"],
                preconditions=conv_pre,
                effects=conv_eff
            ))

        domain_blueprint_obj = DomainBlueprint(
            domain_name=target_dname,
            requirements=fixed_reqs,
            types=fixed_types,
            constants=fixed_constants,
            predicates=fixed_predicates,
            actions=completed_actions
        )
        dom_dict = domain_blueprint_obj.model_dump()
        state["pddl_domain_blueprint"] = dom_dict
        state["fixed_signatures"] = True

    else:
        # ==============================================================================
        # [PRESERVED OLD LOGIC]: Full Domain Elicitation from Scratch (Unconstrained)
        # Retained for backward-compatibility when no reference domain is provided.
        # ==============================================================================
        prompt = f"""
    You are an expert PDDL Knowledge Engineer. Your task is to analyze the following requirements text and construct a single, valid JSON object that strictly conforms to the DomainBlueprint schema (D_gen).
    You only need to generate the PDDL Domain model ("domain_name", "requirements", "types", "constants", "predicates", "actions").

    Here is an example of the required DomainBlueprint JSON structure:
    ```json
    {{
      "domain_name": "{target_dname}",
      "requirements": [":strips", ":typing"],
      "types": {{
        "physical_entity": "object",
        "location_site": "object",
        "mobile_unit": "physical_entity",
        "waypoint_area": "location_site"
      }},
      "constants": {{}},
      "predicates": ["(relational_state ?x - mobile_unit ?y - waypoint_area)"],
      "actions": [
        {{
          "action_name": "transition_action",
          "parameters": {{"?x": "mobile_unit", "?src": "waypoint_area", "?dst": "waypoint_area"}},
          "preconditions": ["(relational_state ?x ?src)"],
          "effects": ["(not (relational_state ?x ?src))", "(relational_state ?x ?dst)"]
        }}
      ]
    }}
    ```

    Requirements Text:
    {requirements_text}
    {feedback_context}

    CRITICAL INTERMEDIATE FLUENTS & ACTION CAUSAL FAITHFULNESS:
    Every distinct physical state, capability, or status described in the requirements (e.g. 'entity is calibrated', 'container is empty', 'item is clean', 'surface is painted') represents a distinct PDDL predicate!
    NEVER omit an intermediate state condition or substitute it with an already-existing predicate (e.g. substituting 'power_on' for 'calibrated', or 'at' for 'holding').
    Every action effect that establishes an intermediate condition described in the requirements must declare and assert that predicate in its positive effects, and every downstream action that requires that condition in its restrictions must include it in its preconditions!

    CRITICAL PREDICATE ARITY & ENTITY SEPARATION FAITHFULNESS:
    - Unary Status vs Binary Relations: When requirements state an entity has an intrinsic unary property or status (e.g. 'entity X is active' or 'container C is empty'), declare and use a unary predicate (e.g. '(is-active ?x)', '(empty ?c)'). Never conflate unary state properties with binary relations by inventing false shared bindings to unrelated variables.
    - Distinct Types with Distinct Conditions: When the text describes clearance, availability, or status for distinct entity categories (e.g. 'location L is clear' vs 'agent A is clear', or 'hand is empty' vs 'container is empty'), declare separate, strongly-typed predicates for each category (e.g. '(location-clear ?l - location)' and '(agent-clear ?a - agent)'). NEVER generalize a predicate to accept 'object' to conflate distinct entity types! Each category mentioned as having that status in the requirements MUST have its own dedicated predicate declared in 'predicates' typed strictly to that category.
    - Zero Unnecessary Action Parameters: Only declare parameters in an action that represent entities directly involved in that action. Do NOT invent unbound dummy parameters that are not physically manipulated by the action.

    CRITICAL TRANSITION EFFECT COMPLETENESS (POSITIVE & NEGATIVE):
    Inspect every 'Once I <action>, it is the case that ...' statement in the requirements text!
    Every stated positive effect MUST be faithfully included in the action's 'effects'!
    For example, when a mobile agent moves away from or vacates a location/tile B ('it is the case that B is clear'), or releases a tool/hand ('it is the case that hand is empty'), you MUST include that positive atom (e.g. '(clear ?from)', '(handempty ?h)') in the action's effects!
    Never drop or omit vacated location clearing or resource release effects explicitly described in the requirements text!

    CRITICAL STRIPS TRANSITION AXIOMS & NEGATIVE EFFECTS (DELETION INVARIANTS):
    In Classical STRIPS, state transitions are modeled by both positive additions AND negative deletions.
    Whenever the requirements state 'it is not the case anymore that ...', you MUST explicitly include the corresponding negative literal '(not (predicate ...))' in the action's 'effects'!
    For example, when an entity changes location, consumes a resource, dirties/fills/empties a container, or transitions between discrete levels/steps (from E to F), you MUST delete the previous condition (e.g. '(not (at ?x ?prev_loc))', '(not (clean ?c))', '(not (empty ?c))', '(not (level ?c ?prev_level))').
    Failing to delete outdated conditions causes entities to permanently retain obsolete states, enabling invalid shortcut plans that violate real-world causal physics!

    CRITICAL SUBTYPING HIERARCHY EXTRACTION:
    When requirements state that categories or entities are subtypes or kinds of other categories (e.g. 'Everything that is an A or B is also a C', or 'A is a C'), faithfully model this hierarchy in domain 'types' using the exact category names mentioned in the text (e.g. '{{"A": "C", "B": "C", "C": "object"}}'). Do NOT invent artificial prefixes (like 'supertype_' or 'subtype_') to type names. Do NOT flatten all types to 'object'.
    In action signatures, when the requirements specify that an action operates on general categories (e.g. 'from a location_site B to a location_site C'), use the exact declared supertype category name (e.g. '?p - location_site'), NOT a specific leaf subtype (like 'subtype_a'). Narrowing action parameters to a single leaf subtype breaks planning by preventing other valid subtypes (like 'subtype_b') from being used!

    CRITICAL DOMAIN SPECIFICATION:
    - Set 'domain_name' to '{target_dname}'.
    - Declare all entity types, state predicates, and action schemas faithfully according to the requirements text.

    CRITICAL MULTIPLE RESTRICTIONS & ACTION DISJUNCTION DECOMPOSITION:
    In Classical STRIPS (:strips :typing), disjunctive preconditions ('or') are strictly forbidden.
    When the requirements text specifies multiple capabilities or multiple restriction clauses for an action phrase (e.g. forward vs reverse movement, moving under condition C1 versus condition C2), EACH distinct restriction rule MUST be elicited as a SEPARATE, uniquely-named action schema (e.g. appending a descriptive suffix like '_1' and '_2', or '_up' and '_down')!
    Never collapse, ignore, or drop alternative restriction clauses into a single action.

    {STANDARD_CLASSICAL_PDDL_RULES}

    Produce ONLY the DomainBlueprint JSON object and nothing else.
    """

        start_t = time.time()
        domain_blueprint_obj, usage = invoke_structured_llm_with_telemetry(
            DomainBlueprint, prompt, target_model=get_phase_model(1)
        )
        elapsed = time.time() - start_t
        dom_dict = domain_blueprint_obj.model_dump()
        if prob_meta.get("domain_name"):
            dom_dict["domain_name"] = prob_meta["domain_name"]
        state["pddl_domain_blueprint"] = dom_dict

    # Update Telemetry Metrics
    state["total_prompt_tokens"] = state.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
    state["total_completion_tokens"] = state.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
    state["total_tokens"] = state.get("total_tokens", 0) + usage.get("total_tokens", 0)
    state["estimated_cost_usd"] = round(state.get("estimated_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0), 6)
    latencies = state.get("node_latencies", {})
    latencies["elicit"] = round(latencies.get("elicit", 0.0) + elapsed, 3)
    state["node_latencies"] = latencies
    return state
