"""Static causal invariant and reachability checker for PDDL domains."""

from typing import Dict, List, Set, Tuple, Any, Optional
import re
from nodes.pddl_to_ast_parser import extract_pddl_problem_metadata
from tools.pddl_utils import normalize_atom, is_subtype


def normalize_atom_expression(expr: str) -> Tuple[str, bool]:
    """Normalizes a PDDL literal into ('(pred arg1 arg2)', is_positive)."""
    return normalize_atom(expr)


def _build_subtype_checker(dom_types_raw: Any):
    """Constructs a transitive subtyping checker."""
    parent_map: Dict[str, str] = {}
    if isinstance(dom_types_raw, dict):
        for child, parent in dom_types_raw.items():
            if child and parent:
                parent_map[str(child).lower()] = str(parent).lower()

    def checker(sub: str, super_t: str) -> bool:
        return is_subtype(sub, super_t, parent_map)

    return checker


def run_causal_fault_analysis(
    domain_bp: Any,
    problem_pddl: Any,
    raw_errors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Checks domain causal invariants against problem initial and goal states."""
    empty_result = {
        "orphaned_goals": [],
        "internal_contradictions": [],
        "ungroundable_preconditions": [],
        "missing_transition_deletes": [],
        "top_action": None,
        "diagnostic_summary": ""
    }

    if any("syntax error" in err.lower() or "parse error" in err.lower() for err in (raw_errors or [])):
        return empty_result

    actions = getattr(domain_bp, "actions", []) if hasattr(domain_bp, "actions") else (domain_bp.get("actions", []) if isinstance(domain_bp, dict) else [])
    if not actions:
        empty_result["diagnostic_summary"] = "Domain has zero actions."
        return empty_result

    prob_meta = extract_pddl_problem_metadata(problem_pddl) if isinstance(problem_pddl, str) else (problem_pddl if isinstance(problem_pddl, dict) else {})
    dom_types_raw = getattr(domain_bp, "types", {}) if hasattr(domain_bp, "types") else (domain_bp.get("types", {}) if isinstance(domain_bp, dict) else {})
    constants_raw = getattr(domain_bp, "constants", {}) if hasattr(domain_bp, "constants") else (domain_bp.get("constants", {}) if isinstance(domain_bp, dict) else {})
    objects_raw = prob_meta.get("objects", {})
    is_subtype = _build_subtype_checker(dom_types_raw)

    all_objs: Dict[str, str] = {}
    if isinstance(constants_raw, dict):
        for k, v in constants_raw.items():
            all_objs[str(k).lower()] = str(v).lower() if v else "object"
    if isinstance(objects_raw, dict):
        for k, v in objects_raw.items():
            all_objs[str(k).lower()] = str(v).lower() if v else "object"

    init_atoms = prob_meta.get("initial_state") or prob_meta.get("init", [])
    goal_atoms = prob_meta.get("goal_state") or prob_meta.get("goal", [])

    init_facts: Dict[str, List[List[str]]] = {}
    for a in init_atoms:
        canon, is_pos = normalize_atom_expression(a)
        if canon and is_pos:
            toks = canon.strip("() ").split()
            if toks:
                pname = toks[0].lower()
                init_facts.setdefault(pname, []).append([x.lower() for x in toks[1:]])

    produced_preds: Set[str] = set()
    deleted_preds: Set[str] = set()
    producers_by_pred: Dict[str, Set[str]] = {}
    internal_contradictions: List[Dict[str, Any]] = []
    ungroundable_preconditions: List[Dict[str, Any]] = []
    missing_transition_deletes: List[Dict[str, Any]] = []

    # Map producers and contradictory simultaneous effects
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        preconds = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])

        pos_preconds = set()
        for p in preconds:
            pcanon, pis_pos = normalize_atom_expression(p)
            if pcanon and pis_pos:
                pos_preconds.add(pcanon.lower())

        pos_effs: Set[str] = set()
        neg_effs: Set[str] = set()
        for eff in effs:
            canon, is_pos = normalize_atom_expression(eff)
            if not canon:
                continue
            toks = canon.strip("() ").split()
            p_name = toks[0].lower() if toks else ""
            if is_pos:
                pos_effs.add(canon.lower())
                produced_preds.add(p_name)
                producers_by_pred.setdefault(p_name, set()).add(act_name)
            else:
                neg_effs.add(canon.lower())
                deleted_preds.add(p_name)

        # Check for contradictory simultaneous effects
        for clash in sorted(pos_effs.intersection(neg_effs)):
            is_in_pre = clash in pos_preconds
            resolution = (
                f"Keep the delete effect '(not {clash})' and REMOVE positive effect '{clash}' (consumes fluent)."
                if is_in_pre else
                f"Keep positive effect '{clash}' and REMOVE delete effect '(not {clash})' (establishes fluent)."
            )
            internal_contradictions.append({
                "action_name": act_name,
                "atom": clash,
                "is_in_precond": is_in_pre,
                "description": f"Action '{act_name}' simultaneously adds and deletes '{clash}'. {resolution}"
            })

    # Check for unproduced goal predicates
    orphaned_goals: List[str] = []
    init_facts_lower = set(init_facts.keys())
    for g in goal_atoms:
        canon, is_pos = normalize_atom_expression(g)
        if canon and is_pos:
            toks = canon.strip("() ").split()
            if toks:
                gpred = toks[0].lower()
                if gpred not in produced_preds and gpred not in init_facts_lower:
                    orphaned_goals.append(gpred)

    # Check for irreversible resource depletion
    resource_depletions: List[Dict[str, Any]] = []
    required_precond_preds: Dict[str, Set[str]] = {}
    for act in actions:
        aname = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        for p in (getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])):
            pcanon, pis_pos = normalize_atom_expression(p)
            if pcanon and pis_pos:
                toks = pcanon.strip("() ").split()
                if toks:
                    required_precond_preds.setdefault(toks[0].lower(), set()).add(aname)

    for act in actions:
        aname = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        for eff in (getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])):
            canon, is_pos = normalize_atom_expression(eff)
            if canon and not is_pos:
                toks = canon.strip("() ").split()
                if toks:
                    pname = toks[0].lower()
                    if pname in required_precond_preds and pname not in produced_preds:
                        other_consumers = sorted(required_precond_preds[pname] - {aname})
                        if other_consumers:
                            resource_depletions.append({
                                "action_name": aname,
                                "atom": canon,
                                "is_in_precond": True,
                                "description": (
                                    f"In action '{aname}', delete effect '(not {canon})' permanently depletes fluent '{pname}', "
                                    f"which has ZERO producing actions in the domain and is required by other action(s) {other_consumers}. "
                                    f"This creates an irreversible absorbing deadlock. If this capability or resource is reusable, "
                                    f"assert positive '{canon}' in effects upon completion and omit '(not {canon})'."
                                )
                            })

    # Check parameter domains and precondition reachability
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {k if k.startswith("?") else f"?{k}": v for k, v in (params.items() if isinstance(params, dict) else [])}
        preconds = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])

        # Verify parameter types have matching objects
        for p_var, p_type in params.items():
            matching_objs = [obj for obj, o_type in all_objs.items() if is_subtype(o_type, str(p_type))]
            if not matching_objs and all_objs:
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": "parameters",
                    "expression": f"({p_var} - {p_type})",
                    "reason": f"Parameter '{p_var} - {p_type}' in action '{act_name}' has ZERO objects in the problem matching type '{p_type}'."
                })

        # Precondition reachability analysis
        pos_eff_tuples = []
        for eff in effs:
            c_eff, is_p = normalize_atom_expression(eff)
            if c_eff and is_p:
                toks_eff = c_eff.strip("() ").split()
                if toks_eff:
                    pos_eff_tuples.append((toks_eff[0].lower(), [x.lower() for x in toks_eff[1:]]))

        for p in preconds:
            pcanon, pis_pos = normalize_atom_expression(p)
            if not pcanon or not pis_pos:
                continue
            toks = pcanon.strip("() ").split()
            if not toks:
                continue
            pname = toks[0].lower()
            p_args = [x.lower() for x in toks[1:]]

            # Check unseeded or unproduced preconditions
            if pname not in produced_preds:
                if pname not in init_facts:
                    ungroundable_preconditions.append({
                        "action_name": act_name,
                        "predicate": pname,
                        "expression": pcanon,
                        "reason": (
                            f"Precondition '{pcanon}' in action '{act_name}' has ZERO matching facts in :init "
                            f"and is never produced by any action in the domain."
                        )
                    })
                else:
                    # Verify parameter types ground against initial facts
                    obj_types_norm = {str(k).lower(): str(v).lower() for k, v in prob_meta.get("objects", {}).items() if v}
                    init_tuples = init_facts[pname]
                    has_typed_grounding = False
                    for init_args in init_tuples:
                        if len(init_args) == len(p_args):
                            matches_all = True
                            for arg_idx, p_var in enumerate(p_args):
                                req_type = str(norm_params.get(p_var, "object")).lower()
                                obj_type = obj_types_norm.get(init_args[arg_idx], "object")
                                if not (is_subtype(obj_type, req_type) or is_subtype(req_type, obj_type)):
                                    matches_all = False
                                    break
                            if matches_all:
                                has_typed_grounding = True
                                break
                    if not has_typed_grounding and init_tuples:
                        expected_types = [obj_types_norm.get(init_tuples[0][i], "object") for i in range(len(init_tuples[0]))]
                        arg_types = [norm_params.get(v, "object") for v in p_args]
                        cand_pred = None
                        for cand_pname, cand_tuples in init_facts.items():
                            if cand_pname != pname and cand_tuples and len(cand_tuples[0]) == len(p_args):
                                if all(
                                    is_subtype(str(norm_params.get(p_args[i], "object")), obj_types_norm.get(cand_tuples[0][i], "object"))
                                    or is_subtype(obj_types_norm.get(cand_tuples[0][i], "object"), str(norm_params.get(p_args[i], "object")))
                                    for i in range(len(p_args))
                                ):
                                    cand_pred = cand_pname
                                    break
                        cand_hint = f" In :init, predicate '({cand_pred} ...)' accepts types {arg_types}." if cand_pred else ""
                        ungroundable_preconditions.append({
                            "action_name": act_name,
                            "predicate": pname,
                            "expression": pcanon,
                            "reason": (
                                f"Static precondition '{pcanon}' in action '{act_name}' has ZERO valid groundings in :init. "
                                f"Initial facts for '{pname}' require argument type(s) {expected_types}, but action arguments have type(s) "
                                f"{arg_types}.{cand_hint} Re-bind the precondition to matching action parameters or use the matching initial predicate."
                            )
                        })

            # Check for conflicting support and clearance preconditions
            toks = pcanon.strip("() ").split()
            SUPPORT_RELS = {"on", "in", "stacked_on", "loaded_in", "contains", "support", "supported"}
            CLEAR_PREDS = {"clear", "empty", "vacant"}
            if len(toks) == 3 and toks[0].lower() in SUPPORT_RELS:
                top_arg, base_arg = toks[1].lower(), toks[2].lower()
                for p2 in preconds:
                    p2canon, p2pos = normalize_atom_expression(p2)
                    if p2canon and p2pos:
                        toks2 = p2canon.strip("() ").split()
                        if len(toks2) == 2 and toks2[0].lower() in CLEAR_PREDS and toks2[1].lower() == base_arg:
                            clear_pred = toks2[0].lower()
                            ungroundable_preconditions.append({
                                "action_name": act_name,
                                "predicate": clear_pred,
                                "expression": p2canon,
                                "reason": (
                                    f"In action '{act_name}', precondition '{p2canon}' checks clearance of base '{base_arg}', "
                                    f"but precondition '{pcanon}' asserts that '{top_arg}' is occupying '{base_arg}'. "
                                    f"A base supporting an entity is occupied, not clear! "
                                    f"In action '{act_name}' preconditions, require clearance on the top entity '({clear_pred} {top_arg})' instead of '{p2canon}', "
                                    f"and in effects assert positive '({clear_pred} {base_arg})' upon vacating/lifting the entity."
                                )
                            })

        # Check that state transitions delete the previous state
        for p in preconds:
            pcanon, pis_pos = normalize_atom_expression(p)
            if not pcanon or not pis_pos:
                continue
            toks = pcanon.strip("() ").split()
            if len(toks) >= 3:
                pname = toks[0].lower()
                entity_arg = toks[1].lower()
                for eff_pname, eff_args in pos_eff_tuples:
                    if eff_pname == pname and len(eff_args) == len(toks[1:]) and eff_args[0] == entity_arg and eff_args != [x.lower() for x in toks[1:]]:
                        # Check if previous state is deleted
                        expected_del = f"(not {pcanon})"
                        del_found = any(
                            normalize_atom_expression(e)[0].lower() == pcanon.lower() and not normalize_atom_expression(e)[1]
                            for e in effs
                        )
                        if not del_found:
                            missing_transition_deletes.append({
                                "action_name": act_name,
                                "expression": pcanon,
                                "reason": (
                                    f"Action '{act_name}' transitions '{pname}' on '{entity_arg}' from '{pcanon}' "
                                    f"to positive effect '({eff_pname} {' '.join(eff_args)})', but omits the required "
                                    f"delete effect '{expected_del}'."
                                )
                            })

    summary_parts = []
    if orphaned_goals:
        summary_parts.append(f"Orphaned Goals (no producers): {sorted(set(orphaned_goals))}")
    if ungroundable_preconditions:
        summary_parts.append(f"Ungroundable/Self-blocking Preconditions: {len(ungroundable_preconditions)}")
    if internal_contradictions:
        summary_parts.append(f"Contradictory Simultaneous Effects: {len(internal_contradictions)}")
    if resource_depletions:
        summary_parts.append(f"Irreversible Absorbing Deadlocks: {len(resource_depletions)}")
    if missing_transition_deletes:
        summary_parts.append(f"Missing State-Transition Deletes: {len(missing_transition_deletes)}")

    top_act = None
    if resource_depletions:
        top_act = resource_depletions[0].get("action_name")
    elif ungroundable_preconditions:
        top_act = ungroundable_preconditions[0].get("action_name")
    elif missing_transition_deletes:
        top_act = missing_transition_deletes[0].get("action_name")
    elif internal_contradictions:
        top_act = internal_contradictions[0].get("action_name")

    return {
        "orphaned_goals": sorted(list(set(orphaned_goals))),
        "internal_contradictions": internal_contradictions,
        "resource_depletions": resource_depletions,
        "ungroundable_preconditions": ungroundable_preconditions,
        "missing_transition_deletes": missing_transition_deletes,
        "top_action": top_act,
        "diagnostic_summary": " | ".join(summary_parts) if summary_parts else "Causal dependencies and goal coverage valid."
    }
