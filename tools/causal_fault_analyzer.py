"""
Lightweight Static Domain-to-Problem Grounding & Effect Completeness Checker.

Evaluates a generated PDDL 2.1 (:strips :typing) DomainBlueprint (D_gen) against the
fixed ground-truth problem PDDL (P_gold) ONLY when VAL syntax/type checking passes
and Fast Downward reports planner unsolvability.

Checks 4 formal Classical PDDL 2.1 invariants (Fox & Long 2003; Helmert 2006):
1. Empty Action Parameter Domains (0 groundings in P_gold :objects / D_gen :constants).
2. Unproduced Goal / Precondition Predicates (missing positive action effects).
3. Contradictory Simultaneous Action Effects ((P ?x) and (not (P ?x)) in the same action).
4. Static :init Signature Mismatch & Directional Asymmetry (missing reverse STRIPS action).
"""

from typing import Dict, List, Set, Tuple, Any, Optional
import difflib
import itertools
import re
from tools.blueprint_parser import extract_pddl_problem_metadata


def find_best_symbol_match(target: str, candidates: List[str]) -> Optional[str]:
    """
    Finds the closest matching symbol from candidates under classical identifier
    normalizations (hyphen vs underscore variation, common prefix variations).
    Strictly prevents false matches between distinct semantic symbols (e.g. 'rock' vs 'soil').
    Domain-agnostic and universally applicable to any PDDL vocabulary.
    """
    if not target or not candidates:
        return None
    target_clean = target.strip("() ").lower()
    t_sep_norm = target_clean.replace("-", "_")

    # 1. Exact match under separator normalization (kebab-case <-> snake_case)
    # E.g. 'can-traverse' <-> 'can_traverse' or 'communicated-soil-data' <-> 'communicated_soil_data'
    for c in candidates:
        c_clean = str(c).strip("() ").lower()
        if t_sep_norm == c_clean.replace("-", "_"):
            return c

    # 2. Morphological abbreviation / token prefix match
    # E.g. 'power_available' <-> 'power_avail', 'position' <-> 'pos'
    t_toks = [t for t in t_sep_norm.split("_") if t]
    for c in candidates:
        c_clean = str(c).strip("() ").lower().replace("-", "_")
        c_toks = [t for t in c_clean.split("_") if t]
        if len(t_toks) == len(c_toks) and len(t_toks) > 0:
            if all(t1 == t2 or t1.startswith(t2) or t2.startswith(t1) for t1, t2 in zip(t_toks, c_toks)):
                return c

    # 3. Exact match after stripping common prefix (is-, has-, can-)
    for prefix in ["is_", "has_", "can_"]:
        if t_sep_norm.startswith(prefix):
            sub = t_sep_norm[len(prefix):]
            for c in candidates:
                c_clean = str(c).strip("() ").lower().replace("-", "_")
                if sub == c_clean or sub == c_clean.replace(prefix, ""):
                    return c

    # 4. Separator-free concatenation match (e.g. 'on_table' <-> 'ontable')
    t_no_sep = t_sep_norm.replace("_", "")
    for c in candidates:
        c_no_sep = str(c).strip("() ").lower().replace("-", "").replace("_", "")
        if t_no_sep == c_no_sep:
            return c

    # 5. Core root token affix match (e.g. 'visible' <-> 'visible_from')
    affix_matches = []
    for c in candidates:
        c_clean = str(c).strip("() ").lower().replace("-", "_")
        c_toks = [t for t in c_clean.split("_") if t]
        if len(t_toks) == 1 and t_toks[0] in c_toks:
            affix_matches.append(c)
        elif len(c_toks) == 1 and c_toks[0] in t_toks:
            affix_matches.append(c)
    if len(affix_matches) == 1:
        return affix_matches[0]

    return None


def normalize_atom_expression(expr: str) -> Tuple[str, bool]:
    """Normalizes a PDDL literal into ('(pred arg1 arg2)', is_positive)."""
    s = str(expr).strip()
    while s.startswith("(") and s.endswith(")"):
        inner = s[1:-1].strip()
        depth = 0
        balanced = True
        for ch in inner:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    balanced = False
                    break
        if balanced and depth == 0:
            s = inner
        else:
            break

    is_pos = True
    while s.lower().startswith("not ") or s.lower().startswith("not("):
        is_pos = not is_pos
        s = s[3:].strip()
        while s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()

    tokens = s.replace("(", " ").replace(")", " ").split()
    if not tokens:
        return "", True
    return f"({' '.join(tokens)})", is_pos


def _build_subtype_checker(dom_types_raw: Any):
    if not isinstance(dom_types_raw, dict):
        dom_types_raw = {}
    dom_types_map = {str(k).strip().lower(): str(v).strip().lower() if v else "object" for k, v in dom_types_raw.items()}

    def is_subtype(sub: str, super_t: str) -> bool:
        if not sub or not super_t:
            return True
        sub_l = str(sub).strip().lower()
        sup_l = str(super_t).strip().lower()
        if sup_l == "object" or sub_l == sup_l:
            return True
        curr = sub_l
        seen = set()
        while curr and curr in dom_types_map and curr not in seen:
            seen.add(curr)
            parent = dom_types_map[curr]
            if parent == sup_l:
                return True
            curr = parent
        return False

    return is_subtype


def find_common_supertype_hint(t1: str, t2: str, dom_types_raw: Any) -> str:
    if not isinstance(dom_types_raw, dict):
        return "object"
    dom_types_map = {str(k).strip().lower(): str(v).strip().lower() if v else "object" for k, v in dom_types_raw.items()}
    a1, curr = [str(t1).strip().lower()], str(t1).strip().lower()
    while curr in dom_types_map and dom_types_map[curr] not in a1:
        curr = dom_types_map[curr]
        a1.append(curr)
    if "object" not in a1:
        a1.append("object")
    a2, curr = [str(t2).strip().lower()], str(t2).strip().lower()
    while curr in dom_types_map and dom_types_map[curr] not in a2:
        curr = dom_types_map[curr]
        a2.append(curr)
    if "object" not in a2:
        a2.append("object")
    for x in a1:
        if x in a2:
            return x
    return "object"


def run_causal_fault_analysis(
    domain_bp: Any,
    problem_pddl: Any,
    raw_errors: List[str],
    historical_results: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Lightweight Static Grounding & Effect Completeness Checker between D_gen and fixed P_gold.
    Skips completely when VAL syntax/type errors are present (since VAL already provides exact line/type traces).
    """
    empty_result = {
        "orphaned_goals": [],
        "internal_contradictions": [],
        "ungroundable_preconditions": [],
        "directional_traps": [],
        "irreversible_locks": [],
        "causal_cycles": [],
        "top_action": None,
        "diagnostic_summary": ""
    }

    # Skip static reachability analysis only when raw syntax/parse errors prevent AST analysis
    if any("syntax error" in err.lower() or "parse error" in err.lower() for err in (raw_errors or [])):
        return empty_result

    actions = getattr(domain_bp, "actions", []) if hasattr(domain_bp, "actions") else domain_bp.get("actions", [])
    if not actions:
        empty_result["diagnostic_summary"] = "Domain has zero actions."
        return empty_result

    prob_meta = extract_pddl_problem_metadata(problem_pddl) if isinstance(problem_pddl, str) else (problem_pddl if isinstance(problem_pddl, dict) else {})
    dom_types_raw = getattr(domain_bp, "types", {}) if hasattr(domain_bp, "types") else domain_bp.get("types", {})
    constants_raw = getattr(domain_bp, "constants", {}) if hasattr(domain_bp, "constants") else domain_bp.get("constants", {})
    objects_raw = prob_meta.get("objects", {})
    is_subtype = _build_subtype_checker(dom_types_raw)

    dom_preds_raw = getattr(domain_bp, "predicates", []) if hasattr(domain_bp, "predicates") else domain_bp.get("predicates", [])
    dom_pred_sigs: Dict[str, Tuple[str, ...]] = {}
    for p_str in dom_preds_raw:
        p_clean = p_str.strip("() ").strip()
        if not p_clean:
            continue
        toks = p_clean.split()
        if not toks:
            continue
        p_name = toks[0]
        args_tokens = toks[1:]
        types_list = []
        curr_vars = []
        i = 0
        while i < len(args_tokens):
            tok = args_tokens[i]
            if tok == "-":
                if i + 1 < len(args_tokens):
                    type_name = args_tokens[i + 1].lower()
                    for _ in curr_vars:
                        types_list.append(type_name)
                    curr_vars = []
                    i += 2
                    continue
            elif tok.startswith("?"):
                curr_vars.append(tok)
            i += 1
        for _ in curr_vars:
            types_list.append("object")
        dom_pred_sigs[p_name] = tuple(types_list)

    all_objs: Dict[str, str] = {}
    if isinstance(constants_raw, dict):
        for k, v in constants_raw.items():
            all_objs[str(k)] = str(v).lower() if v else "object"
    if isinstance(objects_raw, dict):
        for k, v in objects_raw.items():
            all_objs[str(k)] = str(v).lower() if v else "object"
    prob_obj_types = sorted({str(v).lower() for v in (objects_raw.values() if isinstance(objects_raw, dict) else []) if v})

    init_atoms = prob_meta.get("initial_state") or prob_meta.get("init", [])
    goal_atoms = prob_meta.get("goal_state") or prob_meta.get("goal", [])

    init_facts: Dict[str, List[List[str]]] = {}
    init_types_by_pred: Dict[str, Set[Tuple[str, ...]]] = {}
    for a in init_atoms:
        canon, is_pos = normalize_atom_expression(a)
        if canon and is_pos:
            toks = canon.strip("() ").split()
            if toks:
                pname, args = toks[0], toks[1:]
                init_facts.setdefault(pname, []).append(args)
                arg_t = tuple(all_objs.get(x, "object") for x in args)
                init_types_by_pred.setdefault(pname, set()).add(arg_t)

    produced_preds: Set[str] = set()
    deleted_preds: Set[str] = set()
    strict_producers_by_pred: Dict[str, Set[str]] = {}
    internal_contradictions: List[Dict[str, Any]] = []
    ungroundable_preconditions: List[Dict[str, Any]] = []

    for act in actions:
        act_n_p = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        effs_p = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        p_set, n_set = set(), set()
        for eff in effs_p:
            c_e, is_p = normalize_atom_expression(eff)
            if c_e:
                if is_p:
                    p_set.add(c_e)
                else:
                    n_set.add(c_e)
        for c_e in (p_set - n_set):
            toks_e = c_e.strip("() ").split()
            if toks_e:
                strict_producers_by_pred.setdefault(toks_e[0], set()).add(act_n_p)

    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        preconds = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        pos_preconds = set()
        for p in preconds:
            pcanon, pis_pos = normalize_atom_expression(p)
            if pcanon and pis_pos:
                pos_preconds.add(pcanon)

        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        pos_effs, neg_effs = set(), set()
        for eff in effs:
            canon, is_pos = normalize_atom_expression(eff)
            if not canon:
                continue
            toks = canon.strip("() ").split()
            if is_pos:
                pos_effs.add(canon)
                if toks:
                    produced_preds.add(toks[0])
            else:
                neg_effs.add(canon)
                if toks:
                    deleted_preds.add(toks[0])

        # Invariant 3: Contradictory Simultaneous Action Effects
        for clash in sorted(pos_effs.intersection(neg_effs)):
            is_in_pre = clash in pos_preconds
            clash_pred = clash.strip("() ").split()[0] if clash.strip("() ").split() else ""
            other_strict_prods = strict_producers_by_pred.get(clash_pred, set()) - {act_name}
            if is_in_pre and not other_strict_prods:
                # Under PDDL 2.1 add-after-delete semantics (s' = (s \ del(a)) U add(a)), when no other action
                # in the domain restores clash_pred, this represents a transient step-internal lock-and-release
                # that compile_pddl_programmatically (sanitize_action_effects) already compiles to keep positive.
                continue
            if is_in_pre:
                resolution = (
                    f"Atom '{clash}' is required in preconditions, so this action transition consumes/vacates it. "
                    f"Keep the delete effect '(not {clash})' and REMOVE the contradictory positive effect '{clash}'."
                )
            else:
                resolution = (
                    f"Atom '{clash}' is NOT in preconditions, so this action transition establishes/uncovers it. "
                    f"Keep the positive effect '{clash}' and REMOVE the contradictory delete effect '(not {clash})'."
                )
            internal_contradictions.append({
                "action_name": act_name,
                "atom": clash,
                "is_in_precond": is_in_pre,
                "description": (
                    f"Action '{act_name}' simultaneously adds '{clash}' and deletes '(not {clash})' in its effects. "
                    f"{resolution}"
                )
            })

    init_facts_lower: Set[str] = {k.lower() for k in init_facts.keys()}

    # Invariant 2: Unproduced Goal Predicates & Typed Goal Grounding Coverage
    orphaned_goals: List[str] = []
    for g in goal_atoms:
        canon, is_pos = normalize_atom_expression(g)
        if canon and is_pos:
            toks = canon.strip("() ").split()
            if toks:
                gpred, gargs = toks[0], toks[1:]
                if gpred not in produced_preds and gpred not in init_facts and gpred not in orphaned_goals:
                    orphaned_goals.append(gpred)
                    # Check if any action produces a near-match for this goal predicate under identifier variation
                    best_cand = find_best_symbol_match(gpred, list(produced_preds))
                    if best_cand:
                        matching_actions = [
                            getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                            for act in actions
                            if any(
                                normalize_atom_expression(e)[1] and normalize_atom_expression(e)[0].strip("() ").split()[:1] == [best_cand]
                                for e in (getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", []))
                            )
                        ]
                        target_act = matching_actions[0] if matching_actions else "domain.actions"
                        ungroundable_preconditions.append({
                            "action_name": target_act,
                            "predicate": gpred,
                            "expression": f"({gpred} ...)",
                            "best_match": gpred,
                            "reason": (
                                f"Goal predicate '{gpred}' in P_gold :goal is not produced by any action! "
                                f"Action(s) {matching_actions} produce effect '({best_cand} ...)', but P_gold :goal requires '({gpred} ...)'. "
                                f"In domain 'predicates' and action effects in {matching_actions}, rename '({best_cand} ...)' to the exact P_gold symbol '({gpred} ...)'."
                            )
                        })
                    else:
                        # Find best candidate action in domain by name token overlap and parameter compatibility
                        best_act = None
                        best_act_score = -1.0
                        g_clean = gpred.lower().replace("-", "_")
                        g_tokens = set(g_clean.split("_"))
                        g_types = [all_objs.get(x, "object") for x in gargs]

                        best_act_obj = None
                        for act in actions:
                            act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                            a_clean = act_name.lower().replace("-", "_")
                            a_tokens = set(a_clean.split("_"))
                            overlap = len(g_tokens.intersection(a_tokens))
                            ratio = difflib.SequenceMatcher(None, g_clean, a_clean).ratio()

                            params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
                            norm_p = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
                            p_types = list(norm_p.values())
                            type_compat = all(any(is_subtype(gt, pt) for pt in p_types) for gt in g_types) if g_types else False

                            score = (overlap * 50.0) + (ratio * 50.0) + (25.0 if type_compat else 0.0)
                            if score > best_act_score:
                                best_act_score = score
                                best_act = act_name
                                best_act_obj = act

                        suggested_goal_atom = f"({gpred} ...)"
                        extra_param_note = ""
                        if best_act and best_act_score >= 40.0 and best_act_obj is not None:
                            b_params = getattr(best_act_obj, "parameters", {}) if hasattr(best_act_obj, "parameters") else best_act_obj.get("parameters", {})
                            b_norm_p = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (b_params.items() if isinstance(b_params, dict) else []) if v}
                            b_precs = getattr(best_act_obj, "preconditions", []) if hasattr(best_act_obj, "preconditions") else best_act_obj.get("preconditions", [])
                            derived_payload_vars: List[str] = []
                            for bp in b_precs:
                                bp_canon, bp_pos = normalize_atom_expression(bp)
                                if bp_canon and bp_pos:
                                    bp_toks = bp_canon.strip("() ").split()
                                    if bp_toks and bp_toks[0].lower() not in init_facts_lower and bp_toks[0] in produced_preds:
                                        for dv in bp_toks[2:]:
                                            if dv.startswith("?") and dv not in derived_payload_vars:
                                                derived_payload_vars.append(dv)
                            bound_g_vars: List[str] = []
                            type_fix_notes: List[str] = []
                            for idx_g, gt in enumerate(g_types):
                                matching_pvars = [pv for pv, pt in b_norm_p.items() if (is_subtype(gt, pt) or is_subtype(pt, gt)) and pt != "object" and pv not in bound_g_vars]
                                preferred_pvars = [pv for pv in matching_pvars if pv in derived_payload_vars]
                                if preferred_pvars:
                                    bound_g_vars.append(preferred_pvars[0])
                                elif len(matching_pvars) == 1:
                                    bound_g_vars.append(matching_pvars[0])
                                elif derived_payload_vars and idx_g == 0 and len(g_types) == 1:
                                    dv0 = derived_payload_vars[0]
                                    bound_g_vars.append(dv0)
                                    if b_norm_p.get(dv0, "object") != gt:
                                        type_fix_notes.append(f"ensure parameter '{dv0}' in '{best_act}' has type '{gt}'")
                                elif matching_pvars:
                                    bound_g_vars.append(matching_pvars[0])
                            if len(bound_g_vars) == len(g_types) and g_types:
                                suggested_goal_atom = f"({gpred} {' '.join(bound_g_vars)})"
                            if type_fix_notes:
                                extra_param_note = f" ({'; '.join(type_fix_notes)})"
                            reason_msg = (
                                f"Goal predicate '{gpred}' in P_gold :goal (expected argument types {g_types}) is not produced by any action! "
                                f"Action '{best_act}' has the closest semantic role and parameter signature to establish this goal. "
                                f"In domain 'predicates' (with types {g_types}) and in action '{best_act}' positive effects, add '{suggested_goal_atom}'{extra_param_note}."
                            )
                        else:
                            reason_msg = (
                                f"Goal predicate '{gpred}' in P_gold :goal is not produced by any action in the domain! "
                                f"Check the problem requirements and add '({gpred} ...)' as a positive effect to the primary goal-achieving action."
                            )

                        ungroundable_preconditions.append({
                            "action_name": best_act or "domain.actions",
                            "predicate": gpred,
                            "expression": suggested_goal_atom,
                            "best_match": gpred,
                            "reason": reason_msg
                        })
                elif all_objs and gpred in produced_preds and gargs not in init_facts.get(gpred, []):
                    g_arg_types = [all_objs.get(x, "object") for x in gargs]
                    can_ground_goal = False
                    narrow_producers = []
                    arity_mismatch_producers = []
                    for act in actions:
                        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
                        norm_params = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
                        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
                        for eff in effs:
                            ecanon, eis_pos = normalize_atom_expression(eff)
                            if ecanon and eis_pos:
                                etoks = ecanon.strip("() ").split()
                                if etoks and etoks[0] == gpred and len(etoks[1:]) == len(g_arg_types):
                                    e_vars = etoks[1:]
                                    e_types = [norm_params.get(v if v.startswith("?") else f"?{v}", all_objs.get(v, "object")) for v in e_vars]
                                    if all(is_subtype(gt, et) for gt, et in zip(g_arg_types, e_types)):
                                        can_ground_goal = True
                                        break
                                    else:
                                        mismatches = [
                                            (e_vars[idx], e_types[idx], gargs[idx], g_arg_types[idx], find_common_supertype_hint(e_types[idx], g_arg_types[idx], dom_types_raw))
                                            for idx in range(len(g_arg_types))
                                            if not is_subtype(g_arg_types[idx], e_types[idx])
                                        ]
                                        narrow_producers.append((act_name, ecanon, mismatches))
                                elif etoks and etoks[0] == gpred and len(etoks[1:]) != len(g_arg_types):
                                    arity_mismatch_producers.append((act_name, ecanon, etoks[1:], norm_params))
                        if can_ground_goal:
                            break
                    if not can_ground_goal and arity_mismatch_producers:
                        for act_name, ecanon, cur_evars, norm_p in arity_mismatch_producers:
                            suggested_evars: List[str] = []
                            for gt in g_arg_types:
                                cands = [pv for pv, pt in norm_p.items() if (is_subtype(gt, pt) or is_subtype(pt, gt)) and pv not in suggested_evars]
                                suggested_evars.append(cands[0] if cands else "?")
                            sug_atom = f"({gpred} {' '.join(suggested_evars)})"
                            arity_reason = (
                                f"Action '{act_name}' produces goal effect '{ecanon}' with {len(cur_evars)} argument(s), "
                                f"but P_gold :goal atom '{canon}' requires {len(g_arg_types)} argument(s) of types {g_arg_types}! "
                                f"In domain 'predicates' and action '{act_name}' effects, update '{ecanon}' to '{sug_atom}' with parameter types {g_arg_types}."
                            )
                            if not any(u.get("reason") == arity_reason for u in ungroundable_preconditions):
                                ungroundable_preconditions.append({
                                    "action_name": act_name,
                                    "predicate": gpred,
                                    "expression": ecanon,
                                    "best_match": sug_atom,
                                    "reason": arity_reason
                                })
                    if not can_ground_goal and narrow_producers:
                        for act_name, ecanon, mismatches in narrow_producers:
                            for p_var, p_type, g_obj, g_type, sup_hint in mismatches:
                                ungroundable_preconditions.append({
                                    "action_name": act_name,
                                    "predicate": gpred,
                                    "expression": ecanon,
                                    "best_match": None,
                                    "reason": (
                                        f"Action '{act_name}' produces goal predicate '{ecanon}', but parameter '{p_var}' is typed too narrowly as '{p_type}', "
                                        f"which CANNOT ground P_gold :goal atom '{canon}' where object '{g_obj}' has type '{g_type}'! " +
                                        (f"In action '{act_name}' parameters, change parameter '{p_var}' from '{p_type}' to '{g_type}' (or supertype '{sup_hint}' if multiple types are used), "
                                         f"and ensure any predicate in domain 'predicates' that takes '{p_var}' also accepts '{g_type}'."
                                         if sup_hint == "object" and g_type != "object" else
                                         f"In action '{act_name}' parameters, generalize '{p_var}' from '{p_type}' to supertype '{sup_hint}' "
                                         f"(and ensure any predicate in domain 'predicates' that takes '{p_var}' also accepts '{sup_hint}').")
                                    )
                                })

                    # Invariant 2b: Static Parameter Constraint & Variable Aliasing on Goal Producers
                    # Detect if all producers of goal atom 'canon' bind a goal-argument parameter to a
                    # STATIC precondition (not produced anywhere) whose allowed initial values exclude goal constant gargs[idx].
                    aliased_producers = []
                    can_ground_statically = False
                    for act in actions:
                        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
                        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
                        for eff in effs:
                            ecanon, eis_pos = normalize_atom_expression(eff)
                            if ecanon and eis_pos:
                                etoks = ecanon.strip("() ").split()
                                if etoks and etoks[0] == gpred and len(etoks[1:]) == len(gargs):
                                    evars = etoks[1:]
                                    producer_blocked = False
                                    for idx, (c_val, v_param) in enumerate(zip(gargs, evars)):
                                        v_norm = v_param.lower()
                                        for prec in precs:
                                            pcanon, pis_pos = normalize_atom_expression(prec)
                                            if pcanon and pis_pos:
                                                ptoks = pcanon.strip("() ").split()
                                                is_static = ptoks and (ptoks[0] not in produced_preds and ptoks[0] not in deleted_preds)
                                                if is_static:
                                                    ppred, pargs = ptoks[0], [x.lower() for x in ptoks[1:]]
                                                    if v_norm in pargs:
                                                        pos = pargs.index(v_norm)
                                                        allowed = {f[pos] for f in init_facts.get(ppred, []) if len(f) > pos}
                                                        if allowed and c_val not in allowed:
                                                            all_ppred_consts = {elem for f in init_facts.get(ppred, []) for elem in f}
                                                            alt_pos = None
                                                            if c_val in all_ppred_consts:
                                                                for f in init_facts.get(ppred, []):
                                                                    if c_val in f:
                                                                        alt_pos = f.index(c_val)
                                                                        break
                                                            aliased_producers.append({
                                                                "action_name": act_name,
                                                                "parameter": v_param,
                                                                "static_pred": ppred,
                                                                "pos": pos,
                                                                "allowed": sorted(allowed),
                                                                "goal_const": c_val,
                                                                "goal_atom": canon,
                                                                "alt_pos": alt_pos
                                                            })
                                                            producer_blocked = True
                                                            break
                                        if producer_blocked:
                                            break
                                    if not producer_blocked:
                                        can_ground_statically = True
                        if can_ground_statically:
                            break

                    if not can_ground_statically and aliased_producers:
                        for item in aliased_producers:
                            act_n = item["action_name"]
                            p_var = item["parameter"]
                            s_pred = item["static_pred"]
                            c_v = item["goal_const"]
                            g_at = item["goal_atom"]
                            al_vals = item["allowed"]
                            if item.get("alt_pos") is not None:
                                reason_msg = (
                                    f"Goal atom '{g_at}' is unreachable via action '{act_n}': effect produces '{gpred}', "
                                    f"but parameter '{p_var}' is bound at position {item['pos'] + 1} in static precondition '({s_pred} ...)'. "
                                    f"In P_gold :init facts for '{s_pred}', the required value '{c_v}' appears at position {item['alt_pos'] + 1}! "
                                    f"In action '{act_n}' preconditions, adjust the argument positions in '({s_pred} ...)' so '{p_var}' appears at position {item['alt_pos'] + 1} matching P_gold :init."
                                )
                            else:
                                p_var_clean = p_var.lstrip('?')
                                p_var_t = norm_params.get(p_var if p_var.startswith('?') else f'?{p_var}', 'object')
                                new_param_var = f"?{s_pred.replace('-', '_')}_{p_var_clean}"
                                reason_msg = (
                                    f"Goal atom '{g_at}' is unreachable via action '{act_n}': effect produces '{gpred}', "
                                    f"but parameter '{p_var}' is co-indexed (aliased) in static precondition '({s_pred} ...)' "
                                    f"at position {item['pos'] + 1}. Because '{s_pred}' is static, this restricts '{p_var}' to the stationary "
                                    f"entity/location of '{s_pred}' and prevents action '{act_n}' from achieving arbitrary goal instances such as '{g_at}'! "
                                    f"To resolve this in action '{act_n}': (1) In action parameters, declare a new parameter '{new_param_var} - {p_var_t}'. "
                                    f"(2) In static precondition '({s_pred} ...)', replace '{p_var}' with '{new_param_var}'. "
                                    f"(3) In effects, keep '{p_var}' in '({gpred} {p_var})' so '{p_var}' can achieve goal instance '{c_v}'. "
                                    f"(IMPORTANT: Action schemas in domain files must ONLY use variable parameters starting with '?', NEVER hardcode problem object constants)."
                                )
                            if not any(u.get("reason") == reason_msg for u in ungroundable_preconditions):
                                ungroundable_preconditions.append({
                                    "action_name": act_n,
                                    "predicate": gpred,
                                    "expression": g_at,
                                    "best_match": None,
                                    "reason": reason_msg
                                })

                    # Invariant 2c: Disconnected Derived Payload Variable vs Spatial Location Binding on Goal Producers
                    for act in actions:
                        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
                        norm_params = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
                        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
                        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
                        all_eff_vars = {
                            v for e in effs if normalize_atom_expression(e)[0]
                            for v in normalize_atom_expression(e)[0].strip("() ").split()[1:] if v.startswith("?")
                        }
                        init_prec_vars = {
                            v for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]
                            and normalize_atom_expression(p)[0].strip("() ").split()[0].lower() in init_facts_lower
                            for v in normalize_atom_expression(p)[0].strip("() ").split()[1:] if v.startswith("?")
                        }
                        unused_derived_payloads: List[Tuple[str, str]] = []
                        for p in precs:
                            pcanon, pis_pos = normalize_atom_expression(p)
                            if pcanon and pis_pos:
                                ptoks = pcanon.strip("() ").split()
                                if ptoks and ptoks[0].lower() not in init_facts_lower and ptoks[0] in produced_preds:
                                    for dv in ptoks[2:]:
                                        if dv.startswith("?") and dv not in all_eff_vars and dv not in init_prec_vars:
                                            unused_derived_payloads.append((dv, pcanon))
                        if unused_derived_payloads:
                            for eff in effs:
                                ecanon, eis_pos = normalize_atom_expression(eff)
                                if ecanon and eis_pos:
                                    etoks = ecanon.strip("() ").split()
                                    if etoks and etoks[0] == gpred and len(etoks[1:]) == 1 and len(g_arg_types) == 1:
                                        cur_gv = etoks[1]
                                        if cur_gv in init_prec_vars:
                                            pay_v, pay_prec = unused_derived_payloads[0]
                                            req_gt = g_arg_types[0]
                                            cur_pay_t = norm_params.get(pay_v, "object")
                                            # Action signatures are fixed contracts: do not suggest mutating action parameters
                                            rebind_reason = (
                                                f"Action '{act_name}' produces goal effect '{ecanon}' using spatial/context variable '{cur_gv}', "
                                                f"leaving the payload variable '{pay_v}' of derived precondition '{pay_prec}' completely unused in effects! "
                                                f"In action '{act_name}' effects, replace '{ecanon}' with '({gpred} {pay_v})'."
                                            )
                                            if not any(u.get("action_name") == act_name and u.get("expression") == ecanon for u in ungroundable_preconditions):
                                                ungroundable_preconditions.append({
                                                    "action_name": act_name,
                                                    "predicate": gpred,
                                                    "expression": ecanon,
                                                    "best_match": f"({gpred} {pay_v})",
                                                    "reason": rebind_reason
                                                })

    # Check fluent initial facts of goal/mutable predicates that cannot be consumed/deleted because action parameters are typed too narrowly
    goal_preds_set: Set[str] = set()
    goal_facts_map: Dict[str, List[List[str]]] = {}
    for g in goal_atoms:
        gcanon, gis_pos = normalize_atom_expression(g)
        if gcanon and gis_pos:
            gtoks = gcanon.strip("() ").split()
            if gtoks:
                goal_preds_set.add(gtoks[0])
                goal_facts_map.setdefault(gtoks[0], []).append(gtoks[1:])

    for init_pred, fact_args_list in (init_facts.items() if all_objs else []):
        if init_pred not in produced_preds:
            continue
        for f_args in fact_args_list:
            if f_args in goal_facts_map.get(init_pred, []):
                continue
            f_arg_types = [all_objs.get(x, "object") for x in f_args]
            can_consume_fact = False
            narrow_consumers = []
            for act in actions:
                act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
                params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
                norm_params = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
                precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
                for prec in precs:
                    pcanon, pis_pos = normalize_atom_expression(prec)
                    if pcanon and pis_pos:
                        ptoks = pcanon.strip("() ").split()
                        if ptoks and ptoks[0] == init_pred and len(ptoks[1:]) == len(f_arg_types):
                            p_vars = ptoks[1:]
                            p_types = [norm_params.get(v if v.startswith("?") else f"?{v}", all_objs.get(v, "object")) for v in p_vars]
                            if all(is_subtype(ft, pt) for ft, pt in zip(f_arg_types, p_types)):
                                can_consume_fact = True
                                break
                            elif sorted(p_types) == sorted(f_arg_types) and p_types != f_arg_types:
                                perm_reason = (
                                    f"Precondition '{pcanon}' in action '{act_name}' has permuted argument types {p_types} "
                                    f"compared to P_gold :init fact '({init_pred} {' '.join(f_args)})' which has types {f_arg_types}. "
                                    f"In action '{act_name}' preconditions, swap argument order to match P_gold :init: '({init_pred} ...)' with types {f_arg_types}."
                                )
                                if not any(u.get("reason") == perm_reason for u in ungroundable_preconditions):
                                    ungroundable_preconditions.append({
                                        "action_name": act_name,
                                        "predicate": init_pred,
                                        "expression": pcanon,
                                        "best_match": None,
                                        "reason": perm_reason
                                    })
                            elif not any(is_subtype(ft, pt) or is_subtype(pt, ft) or (find_common_supertype_hint(pt, ft, dom_types_raw) not in {"object", "none", None}) for ft, pt in zip(f_arg_types, p_types)):
                                # First check if P_gold :init declares another predicate that natively accepts p_types
                                matching_alt_preds = []
                                for alt_p, alt_sigs in init_types_by_pred.items():
                                    if alt_p != init_pred:
                                        for asig in alt_sigs:
                                            if len(asig) == len(p_types) and all(is_subtype(pt, at) or is_subtype(at, pt) for pt, at in zip(p_types, asig)):
                                                sim = difflib.SequenceMatcher(None, init_pred.lower(), alt_p.lower()).ratio()
                                                if init_pred.lower() in alt_p.lower() or alt_p.lower() in init_pred.lower():
                                                    sim += 1.0
                                                matching_alt_preds.append((sim, alt_p))

                                if matching_alt_preds:
                                    matching_alt_preds.sort(key=lambda x: x[0], reverse=True)
                                    best_alt_p = matching_alt_preds[0][1]
                                    type_sig_reason = (
                                        f"Precondition '{pcanon}' in action '{act_name}' uses predicate '{init_pred}', which in P_gold :init "
                                        f"is defined for types {f_arg_types}, NOT for parameter(s) '{' '.join(p_vars)}' of type(s) {p_types}. "
                                        f"However, P_gold :init declares predicate '({best_alt_p} ...)' specifically for type(s) {p_types}. "
                                        f"In domain 'predicates', action '{act_name}' preconditions, and action '{act_name}' effects, replace '{pcanon}' (and '(not {pcanon})') with '({best_alt_p} {' '.join(p_vars)})' to use the correct problem predicate."
                                    )
                                else:
                                    matching_act_vars = []
                                    for req_t in f_arg_types:
                                        cands = [v for v, vt in norm_params.items() if is_subtype(vt, req_t) or is_subtype(req_t, vt)]
                                        matching_act_vars.append(cands[0] if cands else None)
                                    if all(matching_act_vars) and len(set(matching_act_vars)) == len(matching_act_vars):
                                        suggested_atom = f"({init_pred} {' '.join(matching_act_vars)})"
                                        type_sig_reason = (
                                            f"Precondition '{pcanon}' in action '{act_name}' passes parameters with types {p_types}, "
                                            f"which contradicts the immutable problem contract P_gold :init for predicate '{init_pred}' (expected types: {f_arg_types}). "
                                            f"Action '{act_name}' declares matching parameters {matching_act_vars}. "
                                            f"In action '{act_name}' preconditions, replace '{pcanon}' with '{suggested_atom}'."
                                        )
                                    else:
                                        param_fixes = [
                                            f"change parameter '{v}' in action '{act_name}' parameters from '{ct}' to '{et}'"
                                            for v, ct, et in zip(p_vars, p_types, f_arg_types) if ct != et
                                        ]
                                        fix_str = "; ".join(param_fixes) if param_fixes else f"align parameter types to {f_arg_types}"
                                        type_sig_reason = (
                                            f"Precondition '{pcanon}' in action '{act_name}' requires argument types {p_types}, "
                                            f"which contradicts the immutable problem contract P_gold :init for predicate '{init_pred}' (expected types: {f_arg_types}). "
                                            f"To resolve this: {fix_str} (and update any predicates in domain 'predicates' taking those parameters to expect {f_arg_types}). "
                                            f"Do NOT add extra duplicate parameters to '{act_name}' or declare disjoint types as inheriting from each other."
                                        )
                                if not any(u.get("action_name") == act_name and u.get("expression") == pcanon for u in ungroundable_preconditions):
                                    ungroundable_preconditions.append({
                                        "action_name": act_name,
                                        "predicate": init_pred,
                                        "expression": pcanon,
                                        "best_match": best_alt_p if matching_alt_preds else None,
                                        "reason": type_sig_reason
                                    })
                if can_consume_fact:
                    break

    # Invariant 1 & 4a: Empty Action Parameter Domains & Unreachable / Unseeded Preconditions
    empty_type_actions: Dict[str, List[str]] = {}
    empty_type_inferred_subtypes: Dict[str, Set[str]] = {}
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])

        if all_objs:
            for p_name, p_type in norm_params.items():
                if not any(is_subtype(obj_t, p_type) for obj_t in all_objs.values()):
                    if act_name not in empty_type_actions.setdefault(p_type, []):
                        empty_type_actions[p_type].append(act_name)
                    for prec in precs:
                        pcanon, pis_pos = normalize_atom_expression(prec)
                        if pcanon and pis_pos:
                            ptoks = pcanon.strip("() ").split()
                            if ptoks:
                                pname, pargs = ptoks[0], ptoks[1:]
                                known_sigs = init_types_by_pred.get(pname, set())
                                if known_sigs and not any(len(ft) == len(pargs) for ft in known_sigs):
                                    sample_ft = next(iter(known_sigs))
                                    arity_reason = (
                                        f"Precondition '{pcanon}' in action '{act_name}' uses predicate '{pname}' with arity {len(pargs)} "
                                        f"(parameters: {pargs}), but P_gold :init defines '{pname}' with arity {len(sample_ft)} (expected types: {list(sample_ft)}). "
                                        f"Parameter '{p_name}' of type '{p_type}' has ZERO objects in problem objects! "
                                        f"In action '{act_name}', remove phantom parameter '{p_name} - {p_type}' and update '({pname} ...)' to arity {len(sample_ft)} matching P_gold :init."
                                    )
                                    if not any(u.get("action_name") == act_name and u.get("expression") == pcanon for u in ungroundable_preconditions):
                                        ungroundable_preconditions.append({
                                            "action_name": act_name,
                                            "predicate": pname,
                                            "expression": pcanon,
                                            "best_match": None,
                                            "reason": arity_reason
                                        })
                                    continue
                                for idx, pa in enumerate(pargs):
                                    pa_var = pa if pa.startswith("?") else f"?{pa}"
                                    if pa_var == p_name:
                                        for ft in known_sigs:
                                            if len(pargs) == len(ft) and idx < len(ft) and ft[idx] != "object":
                                                empty_type_inferred_subtypes.setdefault(p_type, set()).add(ft[idx])

    for p_type, act_list in empty_type_actions.items():
        inferred = sorted(empty_type_inferred_subtypes.get(p_type, set()))
        inf_t = inferred[0] if inferred else (prob_obj_types[0] if prob_obj_types else "object")
        sub_hint_str = (
            f"in domain 'actions' for {act_list}, replace parameter type '{p_type}' with declared problem type '{inf_t}' (e.g. change '?param - {p_type}' to '?param - {inf_t}'), "
            f"OR if '{p_type}' is a supertype, declare '{inf_t} - {p_type}' in domain 'types'"
            if inferred
            else f"in domain 'actions' for {act_list}, replace parameter type '{p_type}' with an existing problem type from {prob_obj_types}, "
                 f"OR if no '{p_type}' objects exist in the problem (e.g. single-agent implicit modeling), REMOVE parameter '?param - {p_type}' from action(s) {act_list} and use state predicates over the remaining parameters"
        )
        ungroundable_preconditions.append({
            "action_name": "types",
            "predicate": p_type,
            "expression": f"?param - {p_type}",
            "best_match": None,
            "reason": (
                f"Type '{p_type}' (required by action parameters in {act_list}) has ZERO objects in fixed problem :objects (types: {prob_obj_types}) "
                f"and domain :constants! In P_gold :init, the argument positions bound to '{p_type}' are populated by object types {inferred or prob_obj_types}. "
                f"To resolve this, {sub_hint_str}."
            )
        })

    # Causal Forward Reachability Analysis: Fixed-Point Propagation from P_gold :init through D_gen
    def _resolve_type(t: str) -> str:
        if t in empty_type_actions and empty_type_inferred_subtypes.get(t):
            return sorted(empty_type_inferred_subtypes[t])[0]
        return t

    def _types_satisfy(avail_types: Tuple[str, ...], req_types_seq: Sequence[str]) -> bool:
        if len(avail_types) != len(req_types_seq):
            return False
        if not all_objs:
            return True
        return all(is_subtype(a_t, _resolve_type(r_t)) for a_t, r_t in zip(avail_types, req_types_seq))

    bootstrap_producers_by_pred: Dict[str, List[Tuple[str, Tuple[str, ...]]]] = {}
    domain_used_preds: Set[str] = {k.lower() for k in dom_pred_sigs.keys()}
    for act in actions:
        act_name_b = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params_b = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_p_b = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params_b.items() if isinstance(params_b, dict) else []) if v}
        precs_b = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs_b = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])

        act_pos_prec_sigs: Set[Tuple[str, Tuple[str, ...]]] = set()
        for prec in precs_b:
            pcanon, pis_pos = normalize_atom_expression(prec)
            if pcanon:
                ptoks = pcanon.strip("() ").split()
                if ptoks:
                    domain_used_preds.add(ptoks[0].lower())
                    if pis_pos:
                        p_sig = tuple(norm_p_b.get(x if x.startswith("?") else f"?{x}", all_objs.get(x, "object")) for x in ptoks[1:])
                        act_pos_prec_sigs.add((ptoks[0].lower(), p_sig))

        for eff in effs_b:
            ecanon, eis_pos = normalize_atom_expression(eff)
            if ecanon:
                etoks = ecanon.strip("() ").split()
                if etoks:
                    epred = etoks[0]
                    domain_used_preds.add(epred.lower())
                    if eis_pos:
                        eargs_t = tuple(norm_p_b.get(x if x.startswith("?") else f"?{x}", all_objs.get(x, "object")) for x in etoks[1:])
                        if (epred.lower(), eargs_t) not in act_pos_prec_sigs:
                            bootstrap_producers_by_pred.setdefault(epred.lower(), []).append((act_name_b, eargs_t))

    reachable_types: Set[Tuple[str, Tuple[str, ...]]] = set()
    for pname, type_tuples in init_types_by_pred.items():
        for tt in type_tuples:
            reachable_types.add((pname, tt))

    changed = True
    iterations = 0
    while changed and iterations < 10:
        iterations += 1
        changed = False
        for act in actions:
            params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
            norm_p = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
            precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
            effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])

            act_enabled = True
            for prec in precs:
                pcanon, pis_pos = normalize_atom_expression(prec)
                if pcanon and pis_pos:
                    ptoks = pcanon.strip("() ").split()
                    if ptoks:
                        ppred = ptoks[0]
                        pargs_t = tuple(norm_p.get(x if x.startswith("?") else f"?{x}", all_objs.get(x, "object")) for x in ptoks[1:])
                        sat = any(
                            rt[0] == ppred and _types_satisfy(rt[1], pargs_t)
                            for rt in reachable_types
                        )
                        if not sat:
                            act_enabled = False
                            break
            if act_enabled:
                for eff in effs:
                    ecanon, eis_pos = normalize_atom_expression(eff)
                    if ecanon and eis_pos:
                        etoks = ecanon.strip("() ").split()
                        if etoks:
                            epred = etoks[0]
                            eargs_t = tuple(norm_p.get(x if x.startswith("?") else f"?{x}", all_objs.get(x, "object")) for x in etoks[1:])
                            all_known_t = {str(k).lower() for k in (dom_types_raw.keys() if isinstance(dom_types_raw, dict) else [])} | set(all_objs.values()) | {"object"}
                            sub_options = []
                            for t in eargs_t:
                                subs = sorted({t} | {st for st in all_known_t if is_subtype(st, t)})
                                sub_options.append(subs if subs else [t])
                            for comb in itertools.product(*sub_options):
                                if (epred, comb) not in reachable_types:
                                    reachable_types.add((epred, comb))
                                    changed = True

    root_unseeded_preconditions: List[Dict[str, Any]] = []
    downstream_derived_preconditions: List[Dict[str, Any]] = []
    init_facts_lower = {k.lower(): v for k, v in init_facts.items()}
    init_types_lower = {k.lower(): v for k, v in init_types_by_pred.items()}

    # ARMS Invariant A.1 (Yang et al. 2007): Self-Blocking State-Transition Precondition Clash
    # When an action transitions a relation P from old tuple (not (P ... ?old ...)) to new tuple (P ... ?new ...),
    # requiring the target post-condition (P ... ?new ...) to ALREADY hold in preconditions blocks the transition.
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        act_pos_effs = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]}
        act_neg_effs = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and not normalize_atom_expression(e)[1]}

        for prec in precs:
            pcanon, pis_pos = normalize_atom_expression(prec)
            if not pcanon or not pis_pos:
                continue
            if pcanon in act_pos_effs and pcanon not in act_neg_effs:
                ptoks = pcanon.strip("() ").split()
                if len(ptoks) >= 2:
                    ppred, pargs = ptoks[0], ptoks[1:]
                    req_types_p = [norm_params.get(a if a.startswith("?") else f"?{a}", all_objs.get(a, "object")) for a in pargs]
                    matching_init_preds_for_sig = [
                        ip for ip, isigs in init_types_by_pred.items()
                        if any(len(s) == len(req_types_p) and all(is_subtype(st, rt) for st, rt in zip(s, req_types_p)) for s in isigs)
                    ]
                    if ppred.lower() not in init_facts_lower and len(matching_init_preds_for_sig) >= 2:
                        continue
                    matching_dels = [
                        d for d in act_neg_effs
                        if d != pcanon and d.strip("() ").split()[:1] == [ppred] and len(d.strip("() ").split()[1:]) == len(pargs)
                    ]
                    if matching_dels:
                        del_args = matching_dels[0].strip("() ").split()[1:]
                        diff_vars = [v for v, dv in zip(pargs, del_args) if v != dv]
                        new_var = diff_vars[0] if diff_vars else pargs[-1]
                        new_var_t = norm_params.get(new_var if new_var.startswith("?") else f"?{new_var}", "object")
                        unclaimed_unary = [
                            up for up, usigs in init_types_by_pred.items()
                            if up.lower() not in domain_used_preds and any(len(s) == 1 and is_subtype(new_var_t, s[0]) for s in usigs)
                        ]
                        if unclaimed_unary:
                            best_u = unclaimed_unary[0]
                            clash_reason = (
                                f"Action '{act_name}' transitions '{ppred}' from '{matching_dels[0]}' to '{pcanon}', "
                                f"so requiring target post-condition '{pcanon}' in preconditions violates ARMS Invariant A.1 (self-blocking transition deadlock). "
                                f"P_gold :init declares the unclaimed predicate '({best_u} {new_var})' for type '{new_var_t}'. "
                                f"In action '{act_name}' preconditions, replace '{pcanon}' with '({best_u} {new_var})' (while keeping '{pcanon}' in effects)."
                            )
                        else:
                            clash_reason = (
                                f"Action '{act_name}' transitions '{ppred}' from '{matching_dels[0]}' to '{pcanon}', "
                                f"so requiring target post-condition '{pcanon}' in preconditions violates ARMS Invariant A.1 (self-blocking transition deadlock). "
                                f"In action '{act_name}' preconditions, REMOVE the self-blocking precondition '{pcanon}' (while keeping '{pcanon}' in effects)."
                            )
                        root_unseeded_preconditions.append({
                            "action_name": act_name,
                            "predicate": ppred,
                            "expression": pcanon,
                            "best_match": unclaimed_unary[0] if unclaimed_unary else None,
                            "reason": clash_reason
                        })

    all_prob_consts: Set[str] = (
        {str(x).lower() for flist in init_facts.values() for f in flist for x in f}
        | {str(k).lower() for k in (objects_raw.keys() if isinstance(objects_raw, dict) else [])}
    )

    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])

        # Count how many preconditions in this action use each (pname, tuple(req_types))
        act_prec_sig_counts: Dict[Tuple[str, Tuple[str, ...]], int] = {}
        for p_item in precs:
            pc_tmp, pos_tmp = normalize_atom_expression(p_item)
            if pc_tmp and pos_tmp:
                t_tmp = pc_tmp.strip("() ").split()
                if t_tmp:
                    rt_tmp = tuple(norm_params.get(a if a.startswith("?") else f"?{a}", all_objs.get(a, "object")) for a in t_tmp[1:])
                    act_prec_sig_counts[(t_tmp[0].lower(), rt_tmp)] = act_prec_sig_counts.get((t_tmp[0].lower(), rt_tmp), 0) + 1

        for prec in precs:
            canon, is_pos = normalize_atom_expression(prec)
            if not canon or not is_pos:
                continue
            toks = canon.strip("() ").split()
            if not toks:
                continue
            pname, args = toks[0], toks[1:]
            req_types = [norm_params.get(a if a.startswith("?") else f"?{a}", all_objs.get(a, "object")) for a in args]
            phantom_consts = [a for a in args if not a.startswith("?") and all_prob_consts and a.lower() not in all_prob_consts]

            # Atom is reachable if initial seed exists or forward reachability can produce it (and no unseeded phantom constants exist)
            is_unreachable = bool(phantom_consts and pname not in produced_preds) or not any(
                rt[0] == pname and _types_satisfy(rt[1], req_types)
                for rt in reachable_types
            )

            if not is_unreachable:
                continue

            # Precondition atom is dead/unreachable. Perform formal diagnostic localization:
            if any(
                u.get("action_name") == act_name and u.get("expression") == canon
                for u in (ungroundable_preconditions + root_unseeded_preconditions + downstream_derived_preconditions)
            ):
                continue

            # Sub-case 0: Reified Phantom Constant or Variable -> Specialized P_gold :init Predicate (e.g., (at ?c soil-sample) -> (at_soil_sample ?c))
            reified_matches = []
            if all_objs and len(args) > 0:
                eff_pos_vars_act = {
                    v for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]
                    for v in normalize_atom_expression(e)[0].strip("() ").split()[1:] if v.startswith("?")
                }
                for idx, a in enumerate(args):
                    is_phantom_c = (not a.startswith("?") and all_prob_consts and a.lower() not in all_prob_consts)
                    is_phantom_v = (
                        a.startswith("?") and (
                            (all_objs and not any(is_subtype(ot, norm_params.get(a, "object")) for ot in all_objs.values()))
                            or (len(args) > 1 and a not in eff_pos_vars_act)
                        )
                    )
                    if is_phantom_c or is_phantom_v:
                        rem_args = [x for i, x in enumerate(args) if i != idx]
                        rem_req_types = [norm_params.get(x if x.startswith("?") else f"?{x}", all_objs.get(x, "object")) for x in rem_args]
                        a_clean = a.lstrip("?").lower().replace("-", "_")
                        a_toks = set(a_clean.split("_"))
                        p_clean = pname.lower().replace("-", "_")
                        p_toks = set(p_clean.split("_"))
                        combined_toks = a_toks | p_toks
                        for alt_p, sigs in init_types_by_pred.items():
                            for sig in sigs:
                                if len(sig) == len(rem_req_types) and all(is_subtype(st, rt) or rt == "object" for st, rt in zip(sig, rem_req_types)):
                                    alt_toks = set(alt_p.lower().replace("-", "_").split("_"))
                                    ov = len(combined_toks.intersection(alt_toks))
                                    a_ov = len(a_toks.intersection(alt_toks))
                                    if a_ov > 0:
                                        reified_matches.append((ov * 100 + a_ov * 50, alt_p, a, is_phantom_c, rem_args, rem_req_types))
                                        break
            if reified_matches:
                reified_matches.sort(key=lambda x: x[0], reverse=True)
                _, best_reified_p, ph_arg, is_c, rem_args, rem_req_types = reified_matches[0]
                sug_reified_atom = f"({best_reified_p} {' '.join(rem_args)})" if rem_args else f"({best_reified_p})"
                if is_c:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' embeds phantom constant '{ph_arg}' "
                        f"which does NOT exist in P_gold :objects or :init! "
                        f"P_gold :init models this property as the {len(rem_args)}-argument predicate '{sug_reified_atom}' for type(s) {rem_req_types}. "
                        f"In domain 'predicates', action '{act_name}' preconditions, and action '{act_name}' effects, "
                        f"replace '{canon}' with '{sug_reified_atom}' (and replace '(not {canon})' with '(not {sug_reified_atom})'), "
                        f"and remove '{ph_arg}' from domain 'constants'."
                    )
                else:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' reifies property '{ph_arg}' as an extraneous parameter argument! "
                        f"P_gold :init models this property directly as the {len(rem_args)}-argument predicate '{sug_reified_atom}' for type(s) {rem_req_types}. "
                        f"In domain 'predicates', action '{act_name}' preconditions, and action '{act_name}' effects, "
                        f"replace '{canon}' with '{sug_reified_atom}' (and replace any delete effect '(not {canon})' with '(not {sug_reified_atom})'), "
                        f"and remove '{ph_arg}' from action '{act_name}' parameters."
                    )
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": sug_reified_atom,
                    "reason": reason_msg
                })
                continue

            # Check if (pname, req_types) has a type-compatible non-self-loop bootstrap producer in D_gen
            matching_bootstrap_producers = []
            all_bootstrap_sigs = []
            for prod_act_name, prod_eargs_t in bootstrap_producers_by_pred.get(pname.lower(), []):
                if len(prod_eargs_t) == len(req_types):
                    if prod_eargs_t not in all_bootstrap_sigs:
                        all_bootstrap_sigs.append(prod_eargs_t)
                    if _types_satisfy(prod_eargs_t, req_types) or all(is_subtype(rt, pt) for pt, rt in zip(prod_eargs_t, req_types)):
                        if prod_act_name not in matching_bootstrap_producers:
                            matching_bootstrap_producers.append(prod_act_name)

            best_sym_match = find_best_symbol_match(pname, list(init_facts.keys()))
            has_unclaimed_init_alt = any(
                alt_p.lower() != pname.lower()
                and alt_p.lower() not in domain_used_preds
                and len(req_types) > 0
                and any(
                    len(sig) == len(req_types) and all(is_subtype(s_t, r_t) for s_t, r_t in zip(sig, req_types))
                    for sig in sigs
                )
                for alt_p, sigs in init_types_by_pred.items()
            )

            # If pname is a derived fluent produced in D_gen, but ONLY for different parameter types (e.g. ['shaker', 'ingredient'] instead of ['cocktail', 'ingredient'])
            if (
                not matching_bootstrap_producers
                and all_bootstrap_sigs
                and pname.lower() not in init_facts_lower
                and not has_unclaimed_init_alt
            ):
                other_prec_vars = {
                    v for p_other in precs
                    if normalize_atom_expression(p_other)[0] and normalize_atom_expression(p_other)[0] != canon
                    for v in normalize_atom_expression(p_other)[0].strip("() ").split()[1:] if v.startswith("?")
                }
                # Check if action parameters contain a unique variable matching one of all_bootstrap_sigs AND mismatched arg_v is used by another precondition
                suggested_rebind = None
                for target_sig in all_bootstrap_sigs:
                    rebound_vars = []
                    for arg_v, cur_t, exp_t in zip(args, req_types, target_sig):
                        if is_subtype(cur_t, exp_t) or is_subtype(exp_t, cur_t):
                            rebound_vars.append(arg_v)
                        elif arg_v in other_prec_vars:
                            cand_v = [k for k, vt in norm_params.items() if is_subtype(vt, exp_t) or is_subtype(exp_t, vt)]
                            rebound_vars.append(cand_v[0] if len(cand_v) == 1 else None)
                        else:
                            rebound_vars.append(None)
                    if all(rebound_vars):
                        suggested_rebind = f"({pname} {' '.join(rebound_vars)})"
                        break
                if suggested_rebind:
                    root_unseeded_preconditions.append({
                        "action_name": act_name,
                        "predicate": pname,
                        "expression": canon,
                        "best_match": suggested_rebind,
                        "reason": (
                            f"Precondition '{canon}' in action '{act_name}' binds argument types {req_types}, "
                            f"but derived fluent '{pname}' is NEVER produced for {req_types} "
                            f"(producer actions establish '{pname}' for types {[list(s) for s in all_bootstrap_sigs]}). "
                            f"In action '{act_name}' preconditions, replace '{canon}' with '{suggested_rebind}' so argument types match {list(target_sig)}."
                        )
                    })
                    continue
                else:
                    all_prod_acts = sorted({pa for pa, _ in bootstrap_producers_by_pred.get(pname.lower(), [])})
                    target_sig_l = list(all_bootstrap_sigs[0])
                    param_fixes = [
                        f"change parameter '{v}' in action '{act_name}' parameters from '{ct}' to '{et}'"
                        for v, ct, et in zip(args, req_types, target_sig_l) if ct != et
                    ]
                    fix_str = "; ".join(param_fixes) if param_fixes else f"align parameter types of '{canon}' to {target_sig_l}"
                    root_unseeded_preconditions.append({
                        "action_name": act_name,
                        "predicate": pname,
                        "expression": canon,
                        "best_match": None,
                        "reason": (
                            f"Precondition '{canon}' in action '{act_name}' passes argument types {req_types}, "
                            f"but producer action(s) {all_prod_acts} establish derived fluent '{pname}' for types {target_sig_l}! "
                            f"To resolve this: {fix_str} (and ensure '({pname} ...)' in domain 'predicates' declares parameter types {target_sig_l}, NOT 'object')."
                        )
                    })
                    continue

            # Isolate Downstream Derived Fluents from Root Unseeded Preconditions
            if (
                matching_bootstrap_producers
                and pname.lower() not in init_facts_lower
                and (not best_sym_match or best_sym_match.lower() == pname.lower())
                and not has_unclaimed_init_alt
            ):
                downstream_derived_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "reason": (
                        f"Precondition '{canon}' in action '{act_name}' depends on derived fluent '{pname}' "
                        f"(produced by action(s) {matching_bootstrap_producers}), which is currently unreachable from P_gold :init "
                        f"because its producer action(s) {matching_bootstrap_producers} cannot be triggered from the initial state. "
                        f"Repair the upstream precondition faults in {matching_bootstrap_producers} first."
                    )
                })
                continue

            # Sub-case A: Check for argument order permutation on pname in P_gold :init
            perm_match = None
            for ft in init_types_by_pred.get(pname, set()):
                if len(ft) == len(req_types) and sorted(ft) == sorted(req_types):
                    perm_match = list(ft)
                    break

            if perm_match:
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                    f"but P_gold :init facts for '{pname}' have argument types in order {perm_match}. "
                    f"In action '{act_name}' preconditions, swap argument order to match P_gold :init: '({pname} ...)' with types {perm_match}."
                )
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "reason": reason_msg
                })
                continue

            # Sub-case B: Search P_gold :init for specialized predicate alt_p matching req_types (or permuted/expanded req_types)
            current_act_prec_preds = {
                normalize_atom_expression(p)[0].strip("() ").split()[0].lower()
                for p in precs
                if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[0].strip("() ").split()
            }
            current_act_prec_atoms = {
                (
                    normalize_atom_expression(p)[0].strip("() ").split()[0].lower(),
                    tuple(normalize_atom_expression(p)[0].strip("() ").split()[1:])
                )
                for p in precs
                if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[0].strip("() ").split()
            }
            matching_alt_preds = []
            perm_alt_preds = []
            arity_alt_preds = []
            if len(req_types) > 0 and all_objs:
                for alt_p, sigs in init_types_by_pred.items():
                    if alt_p.lower() == pname.lower() or (
                        alt_p.lower() in current_act_prec_preds
                        and (alt_p.lower(), tuple(args)) not in current_act_prec_atoms
                    ):
                        continue
                    for sig in sigs:
                        alt_clean = alt_p.lower().replace("-", "_")
                        p_clean = pname.lower().replace("-", "_")
                        alt_tokens = set(alt_clean.split("_"))
                        p_tokens = set(p_clean.split("_"))
                        overlap = len(alt_tokens.intersection(p_tokens))
                        stem_overlap = any(len(t1) >= 4 and len(t2) >= 4 and t1[:5] == t2[:5] for t1 in alt_tokens for t2 in p_tokens)
                        ratio = difflib.SequenceMatcher(None, p_clean, alt_clean).ratio()
                        unclaimed_bonus = 25.0 if (pname.lower() in init_facts_lower and alt_p.lower() not in domain_used_preds) else 0.0
                        score = (100 * overlap) + (80.0 if stem_overlap else 0.0) + (50 * ratio) + 20.0 + unclaimed_bonus
                        if len(sig) == len(req_types) and all(
                            is_subtype(s_t, r_t)
                            for s_t, r_t in zip(sig, req_types)
                        ):
                            matching_alt_preds.append((score, alt_p, sig, "init"))
                            break
                        elif pname.lower() not in init_facts_lower and len(sig) == len(req_types) and sorted(sig) == sorted(req_types):
                            perm_alt_preds.append((score, alt_p, sig))
                            break
                        elif pname.lower() not in init_facts_lower and (stem_overlap or overlap > 0) and len(sig) == len(req_types) + 1:
                            if all(any(is_subtype(s_t, pt) for pt in norm_params.values()) for s_t in sig):
                                arity_alt_preds.append((score, alt_p, sig))
                                break

            if (
                matching_alt_preds
                and pname.lower() not in init_facts_lower
                and (matching_alt_preds[0][1].lower(), tuple(args)) in current_act_prec_atoms
                and matching_alt_preds[0][0] < 100.0
                and arity_alt_preds
                and max(x[0] for x in arity_alt_preds) >= 100.0
            ):
                matching_alt_preds = []

            if matching_alt_preds:
                matching_alt_preds.sort(key=lambda x: x[0], reverse=True)
                cand_names = [x[1] for x in matching_alt_preds]
                best_alt_p = cand_names[0]
                sample_facts = init_facts.get(best_alt_p, [])
                sample_str = f" (e.g. '({best_alt_p} {' '.join(sample_facts[0])})')" if sample_facts else ""
                same_sig_count = act_prec_sig_counts.get((pname.lower(), tuple(req_types)), 1)
                if (best_alt_p.lower(), tuple(args)) in current_act_prec_atoms:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' is a redundant unseeded duplicate because "
                        f"action '{act_name}' already declares '({best_alt_p} {' '.join(args)})' for {req_types}. "
                        f"In action '{act_name}' preconditions, REMOVE the redundant unseeded precondition '{canon}' "
                        f"(and in action '{act_name}' effects, replace any remaining '{pname}' with '{best_alt_p}')."
                    )
                    best_match_val = f"REMOVE_{canon}"
                elif same_sig_count >= 2 and len(cand_names) >= 2:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init for predicate '{pname}' (and no action produces it from the initial state). "
                        f"Action '{act_name}' has {same_sig_count} preconditions with types {req_types}, and P_gold :init declares {len(cand_names)} distinct predicates "
                        f"for {req_types}: {cand_names}{sample_str}. "
                        f"In domain 'predicates', action '{act_name}' preconditions, and any related effects, replace '{pname}' with the specialized P_gold symbols {cand_names} "
                        f"(using '{cand_names[0]}' for the dynamic fluent and '{cand_names[1]}' for the static reference fluent)."
                    )
                    best_match_val = str(cand_names)
                elif pname.lower() in init_facts_lower:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init for predicate '{pname}' (and no action produces it from the initial state). "
                        f"However, P_gold :init declares initial facts for {req_types} under the specialized predicate symbol '{best_alt_p}'{sample_str}. "
                        f"In domain 'predicates' and action '{act_name}' preconditions (and related effects for {req_types}), replace '{pname}' with the specialized P_gold symbol '{best_alt_p}' "
                        f"(while keeping '{pname}' in domain 'predicates' for its other P_gold :init argument types)."
                    )
                    best_match_val = best_alt_p
                else:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init for predicate '{pname}' (and no action produces it from the initial state). "
                        f"However, P_gold :init declares initial facts for {req_types} under the specialized predicate symbol '{best_alt_p}'{sample_str}. "
                        f"In domain 'predicates', action '{act_name}' preconditions, and any related effects, replace '{pname}' with the specialized P_gold symbol '{best_alt_p}'."
                    )
                    best_match_val = best_alt_p
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": best_match_val,
                    "reason": reason_msg
                })
                continue

            if perm_alt_preds:
                perm_alt_preds.sort(key=lambda x: x[0], reverse=True)
                cand_names = [x[1] for x in perm_alt_preds]
                best_alt_p = cand_names[0]
                best_sig = list(perm_alt_preds[0][2])
                sample_facts = init_facts.get(best_alt_p, [])
                sample_str = f" (e.g. '({best_alt_p} {' '.join(sample_facts[0])})')" if sample_facts else ""
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' uses unseeded predicate '{pname}' with argument types {req_types}, "
                    f"which has ZERO facts in P_gold :init. However, P_gold :init declares initial facts with permuted argument types {best_sig} "
                    f"under predicate symbol(s) {cand_names}{sample_str}. "
                    f"In domain 'predicates' and action '{act_name}' preconditions, replace '{canon}' with the P_gold symbol(s) {cand_names} "
                    f"and swap the argument order to match {best_sig}."
                )
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": best_alt_p,
                    "reason": reason_msg
                })
                continue

            if arity_alt_preds:
                arity_alt_preds.sort(key=lambda x: x[0], reverse=True)
                best_alt_p = arity_alt_preds[0][1]
                best_sig = list(arity_alt_preds[0][2])
                sample_facts = init_facts.get(best_alt_p, [])
                sample_str = f" (e.g. '({best_alt_p} {' '.join(sample_facts[0])})')" if sample_facts else ""
                sug_arity_atom = f"({best_alt_p} ...)"
                for extra_idx in range(len(best_sig)):
                    rem_sig = best_sig[:extra_idx] + best_sig[extra_idx + 1:]
                    if len(rem_sig) == len(req_types) and all(is_subtype(st, rt) for st, rt in zip(rem_sig, req_types)):
                        extra_t = best_sig[extra_idx]
                        extra_cands = [pv for pv, pt in norm_params.items() if is_subtype(extra_t, pt) and pv not in args]
                        if extra_cands:
                            full_args = list(args[:extra_idx]) + [extra_cands[0]] + list(args[extra_idx:])
                            sug_arity_atom = f"({best_alt_p} {' '.join(full_args)})"
                            break
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' uses unseeded {len(req_types)}-argument predicate '{pname}', "
                    f"which has ZERO facts in P_gold :init. However, P_gold :init declares the {len(best_sig)}-argument predicate "
                    f"'{best_alt_p}' with parameter types {best_sig}{sample_str}. "
                    f"In domain 'predicates' and action '{act_name}' preconditions, replace '{canon}' with '{sug_arity_atom}' "
                    f"binding all {len(best_sig)} action parameters matching types {best_sig}."
                )
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": sug_arity_atom if sug_arity_atom != f"({best_alt_p} ...)" else best_alt_p,
                    "reason": reason_msg
                })
                continue

            # Sub-case C: Check identifier variations under find_best_symbol_match
            if best_sym_match and best_sym_match.lower() != pname.lower():
                is_best_static = best_sym_match not in produced_preds and best_sym_match not in deleted_preds
                stat_str = "static " if is_best_static else ""
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' is unreachable: predicate '{pname}' has ZERO facts in P_gold :init "
                    f"and ZERO actions produce it. P_gold :init defines the matching {stat_str}predicate '{best_sym_match}'. "
                    f"In domain 'predicates' and action '{act_name}' preconditions, replace predicate '{pname}' with the exact P_gold symbol '{best_sym_match}'."
                )
                root_unseeded_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": best_sym_match,
                    "reason": reason_msg
                })
                continue

            # Sub-case D: General fallback diagnostic
            if pname.lower() not in init_facts_lower:
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' is unreachable: predicate '{pname}' has ZERO facts in P_gold :init "
                    f"and ZERO actions in the domain produce '({pname} ...)' from the initial state! "
                    f"MANDATORY REPAIR GUIDANCE: "
                    f"(1) If '{canon}' is an extraneous, deadlocked, or invalid constraint not required by the domain specification, eliminate '{canon}' from action '{act_name}' preconditions (and remove '({pname} ...)' from domain 'predicates' if no longer used). "
                    f"(2) Otherwise, if the specification mandates that an action establishes '{pname}', add '({pname} ...)' as a positive effect to the designated producer action, "
                    f"or replace '{pname}' with the matching predicate from P_gold :init ({sorted(init_facts.keys())})."
                )
            else:
                avail = [list(ft) for ft in sorted(init_types_lower.get(pname.lower(), set()))]
                if len(avail) == 1 and len(avail[0]) == len(req_types):
                    exp_sig = avail[0]
                    param_fixes = [
                        f"change parameter '{v}' in action '{act_name}' parameters from '{ct}' to '{et}'"
                        for v, ct, et in zip(args, req_types, exp_sig) if ct != et
                    ]
                    fix_str = "; ".join(param_fixes) if param_fixes else f"align parameter types to {exp_sig}"
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' passes argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init (P_gold :init signature for '{pname}' is {exp_sig}). "
                        f"To resolve this: {fix_str} (and update any predicates in domain 'predicates' taking those parameters to expect {exp_sig}). "
                        f"Do NOT declare disjoint problem object types as subtypes of each other."
                    )
                else:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init (available :init type signatures for '{pname}': {avail}). "
                        f"In action '{act_name}' parameters and preconditions, align parameter types to match {avail[0]}."
                    )
            root_unseeded_preconditions.append({
                "action_name": act_name,
                "predicate": pname,
                "expression": canon,
                "reason": reason_msg
            })

    if root_unseeded_preconditions or ungroundable_preconditions:
        ungroundable_preconditions.extend(root_unseeded_preconditions)
    else:
        ungroundable_preconditions.extend(downstream_derived_preconditions)

    # Invariant 0d: First-Order Logic Range-Restriction / Unbound Effect Parameters (McDermott 1998; Fox & Long 2003)
    # Every parameter variable ?v declared in an action schema with preconditions must be constrained by at least one precondition atom.
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        if not precs or not norm_params:
            continue

        prec_vars_set: Set[str] = set()
        prec_preds_set: Set[str] = set()
        act_pos_prec_atoms_rr: Set[str] = set()
        for p in precs:
            pcanon, pis_pos = normalize_atom_expression(p)
            if pcanon and pis_pos:
                act_pos_prec_atoms_rr.add(pcanon)
                ptoks = pcanon.strip("() ").split()
                if ptoks:
                    prec_preds_set.add(ptoks[0])
                    for v in ptoks[1:]:
                        if v.startswith("?"):
                            prec_vars_set.add(v)

        eff_vars_set: Set[str] = set()
        eff_atoms_by_var: Dict[str, List[str]] = {}
        act_neg_eff_atoms_rr: Set[str] = set()
        for e in effs:
            ecanon, eis_pos = normalize_atom_expression(e)
            if ecanon:
                if not eis_pos:
                    act_neg_eff_atoms_rr.add(ecanon)
                etoks = ecanon.strip("() ").split()
                for v in etoks[1:]:
                    if v.startswith("?"):
                        eff_vars_set.add(v)
                        eff_atoms_by_var.setdefault(v, []).append(ecanon)

        if any(u.get("action_name") == act_name for u in ungroundable_preconditions):
            continue

        for u_var, u_type in norm_params.items():
            if u_var in prec_vars_set:
                continue
            if u_var not in eff_vars_set:
                rr_reason = (
                    f"In action '{act_name}', parameter '{u_var}' (type '{u_type}') is declared in the action signature but never referenced in preconditions or effects. "
                    f"Action parameter signatures are fixed contract: do NOT delete or remove parameter '{u_var}'. Instead, ensure the necessary precondition or effect predicate involving '{u_var}' is included in action '{act_name}'."
                )
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": act_name,
                    "expression": u_var,
                    "best_match": None,
                    "reason": rr_reason
                })
                continue

            # Exclude complete-graph relocation destination parameters where substituting a bound variable into the effect atom yields a precondition/deleted source atom
            is_relocation_dest = any(
                re.sub(rf"(?<!\w){re.escape(u_var)}(?!\w)", bv, ea) in (act_pos_prec_atoms_rr | act_neg_eff_atoms_rr)
                for bv in prec_vars_set
                if bv in norm_params and (norm_params[bv] == u_type or is_subtype(norm_params[bv], u_type) or is_subtype(u_type, norm_params[bv]))
                for ea in eff_atoms_by_var.get(u_var, [])
            )
            if is_relocation_dest:
                continue

            # Check if another parameter of compatible type is already bound in preconditions (duplicate unbound parameter)
            compat_bound_vars = [
                bv for bv in prec_vars_set
                if bv in norm_params
                and (norm_params[bv] == u_type or is_subtype(norm_params[bv], u_type) or is_subtype(u_type, norm_params[bv]))
                and not any(bv in ea.strip("() ").split()[1:] for ea in eff_atoms_by_var.get(u_var, []))
            ]
            if compat_bound_vars:
                b_var = compat_bound_vars[0]
                rr_reason = (
                    f"In action '{act_name}', parameter '{u_var}' (type '{u_type}') appears in effects {eff_atoms_by_var.get(u_var, [])} "
                    f"but is NEVER bound in preconditions (violating First-Order Logic range-restriction), duplicating precondition-bound parameter '{b_var}' (type '{norm_params[b_var]}'). "
                    f"In action '{act_name}', remove duplicate parameter '{u_var}' from parameters and replace '{u_var}' with '{b_var}' in all effects of '{act_name}'."
                )
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": act_name,
                    "expression": u_var,
                    "best_match": None,
                    "reason": rr_reason
                })
            else:
                # Check if P_gold :init defines static predicate(s) matching u_type and other parameters in norm_params
                other_param_types = {vt for vk, vt in norm_params.items() if vk != u_var}
                matching_init_static = []
                for ipred, isigs in init_types_by_pred.items():
                    if ipred not in prec_preds_set and ipred not in produced_preds and ipred not in deleted_preds:
                        for isig in isigs:
                            if any(is_subtype(u_type, st) or is_subtype(st, u_type) for st in isig):
                                other_sig_types = [st for st in isig if not (is_subtype(u_type, st) and is_subtype(st, u_type))]
                                if all(any(is_subtype(opt, ost) or is_subtype(ost, opt) for opt in other_param_types) for ost in other_sig_types):
                                    matching_init_static.append(ipred)
                                    break
                if matching_init_static:
                    rr_reason = (
                        f"In action '{act_name}', parameter '{u_var}' (type '{u_type}') appears in effects {eff_atoms_by_var.get(u_var, [])} "
                        f"but is completely unconstrained in preconditions (violating First-Order Logic range-restriction). "
                        f"P_gold :init defines static relation predicate(s) {sorted(matching_init_static)} for type '{u_type}'. "
                        f"In action '{act_name}' preconditions, add the required precondition atom(s) using {sorted(matching_init_static)} to constrain '{u_var}'."
                    )
                    ungroundable_preconditions.append({
                        "action_name": act_name,
                        "predicate": act_name,
                        "expression": u_var,
                        "best_match": None,
                        "reason": rr_reason
                    })

    # Invariant 4f: Ground Binary-Unary Join Contradiction (Support vs. Supported Item Clearance Inversion)
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        bin_precs = []
        unary_precs = []
        for prec in precs:
            pcanon, pis_pos = normalize_atom_expression(prec)
            if pcanon and pis_pos:
                ptoks = pcanon.strip("() ").split()
                if len(ptoks) == 3 and ptoks[0] in init_facts:
                    bin_precs.append((ptoks[0], ptoks[1], ptoks[2]))
                elif len(ptoks) == 2 and ptoks[0] in init_facts:
                    unary_precs.append((ptoks[0], ptoks[1]))
        for b_pred, v1, v2 in bin_precs:
            t1 = norm_params.get(v1 if v1.startswith("?") else f"?{v1}", "object")
            t2 = norm_params.get(v2 if v2.startswith("?") else f"?{v2}", "object")
            if v1 == v2 or not (is_subtype(t1, t2) or is_subtype(t2, t1)):
                continue
            b_facts = [f for f in init_facts.get(b_pred, []) if len(f) == 2]
            if not b_facts:
                continue
            for u_pred, u_var in unary_precs:
                if u_var == v2 and not any(up == u_pred and uv == v1 for up, uv in unary_precs):
                    u_set = {f[0] for f in init_facts.get(u_pred, []) if len(f) == 1}
                    if u_set:
                        arg2_in_u = any(f[1] in u_set for f in b_facts)
                        arg1_in_u = any(f[0] in u_set for f in b_facts)
                        if not arg2_in_u and arg1_in_u:
                            join_reason = (
                                f"Precondition '({u_pred} {v2})' in action '{act_name}' contradicts '({b_pred} {v1} {v2})' in P_gold :init: "
                                f"ZERO initial '({b_pred} ...)' facts have '{u_pred}' true on the second argument '{v2}' (the underlying support), "
                                f"whereas '{u_pred}' holds on the first argument '{v1}' (the supported item)! "
                                f"In action '{act_name}': (1) change precondition '({u_pred} {v2})' to '({u_pred} {v1})', "
                                f"(2) in effects, when removing '{v1}' from '{v2}', assert positive '({u_pred} {v2})' and delete '(not ({u_pred} {v1}))' "
                                f"(and in the complementary placement action that adds '({b_pred} {v1} {v2})', assert '({u_pred} {v1})' and delete '(not ({u_pred} {v2}))')."
                            )
                            ungroundable_preconditions.append({
                                "action_name": act_name,
                                "predicate": u_pred,
                                "expression": f"({u_pred} {v2})",
                                "best_match": f"({u_pred} {v1})",
                                "reason": join_reason
                            })

    # Invariant 4b: Directional Asymmetry on Static Binary Relations
    directional_traps: List[Dict[str, Any]] = []
    for r_name, facts in init_facts.items():
        if r_name in produced_preds or not facts or not all(len(f) == 2 for f in facts):
            continue
        f_set = {(f[0], f[1]) for f in facts}
        if not any((b, a) not in f_set for (a, b) in f_set):
            continue

        forward_acts, reverse_acts = [], []
        for act in actions:
            act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
            precs = [normalize_atom_expression(p)[0] for p in (getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", []))]
            effs_raw = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
            eff_adds = [normalize_atom_expression(e)[0] for e in effs_raw if normalize_atom_expression(e)[1]]
            eff_dels = [normalize_atom_expression(e)[0] for e in effs_raw if not normalize_atom_expression(e)[1]]

            for prec in precs:
                ptoks = prec.strip("() ").split()
                if len(ptoks) == 3 and ptoks[0] == r_name:
                    r1, r2 = ptoks[1], ptoks[2]
                    for d in eff_dels:
                        dtoks = d.strip("() ").split()
                        if r1 in dtoks:
                            idx = dtoks.index(r1)
                            if any(a.strip("() ").split()[:1] == dtoks[:1] and len(a.strip("() ").split()) == len(dtoks) and a.strip("() ").split()[idx] == r2 for a in eff_adds):
                                forward_acts.append((act_name, dtoks[0]))
                        elif r2 in dtoks:
                            idx = dtoks.index(r2)
                            if any(a.strip("() ").split()[:1] == dtoks[:1] and len(a.strip("() ").split()) == len(dtoks) and a.strip("() ").split()[idx] == r1 for a in eff_adds):
                                reverse_acts.append((act_name, dtoks[0]))

        if forward_acts and not reverse_acts:
            for g in goal_atoms:
                g_canon, _ = normalize_atom_expression(g)
                gtoks = g_canon.strip("() ").split()
                if len(gtoks) >= 2:
                    g_pred, g_obj, g_dest = gtoks[0], gtoks[1], gtoks[-1]
                    matching_fa = [fa[0] for fa in forward_acts if fa[1] == g_pred]
                    if matching_fa:
                        for f in init_facts.get(g_pred, []):
                            if len(f) >= 2 and f[0] == g_obj and (g_dest, f[-1]) in f_set and (f[-1], g_dest) not in f_set:
                                directional_traps.append({
                                    "relation": r_name,
                                    "forward_actions": matching_fa,
                                    "reason": (
                                        f"Directional Asymmetry / Missing Inverse Action: Action(s) {matching_fa} transition '{g_pred}' "
                                        f"only along '({r_name} ?from ?to)', but P_gold :goal requires '{g_obj}' to move from '{f[-1]}' to '{g_dest}' "
                                        f"where '({r_name} {g_dest} {f[-1]})' holds in :init. Add a separate inverse action schema (e.g. '{matching_fa[0]}_2') "
                                        f"with precondition '({r_name} ?to ?from)'."
                                    )
                                })



    # Invariant 4d: Irreversible Resource Depletion / Absorbing State Lockout
    irreversible_locks: List[Dict[str, Any]] = []
    all_precond_preds: Set[str] = set()
    for act in actions:
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        for p in precs:
            pcanon, pis_pos = normalize_atom_expression(p)
            if pcanon and pis_pos:
                ptoks = pcanon.strip("() ").split()
                if ptoks:
                    all_precond_preds.add(ptoks[0])

    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        act_pos_prec_atoms = {normalize_atom_expression(p)[0] for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]}
        act_prec_preds = {a.strip("() ").split()[0] for a in act_pos_prec_atoms if a.strip("() ").split()}
        act_pos_eff_atoms = [normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]]

        for eff in effs:
            ecanon, eis_pos = normalize_atom_expression(eff)
            if not ecanon or eis_pos:
                continue
            etoks = ecanon.strip("() ").split()
            if not etoks:
                continue
            del_pname = etoks[0]
            del_args = etoks[1:]
            if del_pname not in produced_preds and (del_pname in act_prec_preds or del_pname in all_precond_preds):
                adds_replacement_on_arg = any(
                    any(da in pa.strip("() ").split()[1:] for da in del_args)
                    for pa in act_pos_eff_atoms
                )
                is_spurious_self_del = (ecanon in act_pos_prec_atoms and not adds_replacement_on_arg)
                if is_spurious_self_del:
                    lock_reason = (
                        f"Action '{act_name}' requires '{ecanon}' in preconditions and deletes '(not {ecanon})' in effects "
                        f"without transitioning {del_args} to any replacement state (and no action in the domain produces '{del_pname}'). "
                        f"This is a spurious self-depleting delete effect on a reusable entity status that permanently locks {del_args} after a single execution. "
                        f"In action '{act_name}' effects, REMOVE the delete effect '(not {ecanon})' (do NOT add '({del_pname} ...)' to unrelated actions)."
                    )
                else:
                    lock_reason = (
                        f"Action '{act_name}' deletes '(not ({del_pname} ...))', but NO action across the entire domain produces '({del_pname} ...)'. "
                        f"Because predicate '{del_pname}' has zero add-effects anywhere in the domain, it is irreversibly depleted after a single execution, "
                        f"permanently locking the entity from executing any subsequent actions requiring '{del_pname}'. "
                        f"If '{del_pname}' is a reversible condition (such as clearance, vacancy, or location), ensure the complementary action "
                        f"that vacates, unloads, or moves away produces '({del_pname} ...)' in its positive effects. "
                        f"Only omit the delete effect if '{act_name}' is a repeatable non-destructive observation/inspection."
                    )
                if not any(il.get("reason") == lock_reason for il in irreversible_locks):
                    irreversible_locks.append({
                        "action_name": act_name,
                        "predicate": del_pname,
                        "expression": ecanon,
                        "is_spurious_self_delete": is_spurious_self_del,
                        "reason": lock_reason
                    })

    # Invariant 4e: Bilateral Mutex Clearance Conservation (Moving / Vacating Slots)
    clearance_preds = {p for p in all_precond_preds if any(k in p.lower() for k in ["clear", "empty", "free", "available", "clean", "vacant"])}
    bilateral_mutex_faults: List[Dict[str, Any]] = []
    if clearance_preds:
        # Map each unary clearance predicate cp to the parameter types it applies to across action preconditions and :init
        cp_target_types: Dict[str, Set[str]] = {}
        for cp in clearance_preds:
            for sig in init_types_by_pred.get(cp, set()):
                if len(sig) == 1:
                    cp_target_types.setdefault(cp, set()).add(sig[0])
            for o_act in actions:
                o_params = getattr(o_act, "parameters", {}) if hasattr(o_act, "parameters") else o_act.get("parameters", {})
                o_norm_p = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (o_params.items() if isinstance(o_params, dict) else []) if v}
                o_precs = getattr(o_act, "preconditions", []) if hasattr(o_act, "preconditions") else o_act.get("preconditions", [])
                for op in o_precs:
                    op_c, op_pos = normalize_atom_expression(op)
                    if op_c and op_pos:
                        op_toks = op_c.strip("() ").split()
                        if len(op_toks) == 2 and op_toks[0] == cp:
                            vt = o_norm_p.get(op_toks[1] if op_toks[1].startswith("?") else f"?{op_toks[1]}")
                            if vt:
                                cp_target_types.setdefault(cp, set()).add(vt)

        for act in actions:
            act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
            params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
            act_norm_p = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
            precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
            act_pos_precs = {normalize_atom_expression(p)[0] for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]}
            effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
            pos_eff_atoms = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]}
            neg_eff_atoms = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and not normalize_atom_expression(e)[1]}
            pos_eff_preds = {a.strip("() ").split()[0] for a in pos_eff_atoms if a}

            for eff in effs:
                ecanon, eis_pos = normalize_atom_expression(eff)
                if not ecanon or eis_pos:
                    continue
                etoks = ecanon.strip("() ").split()
                if len(etoks) >= 2:
                    del_p, del_args = etoks[0], etoks[1:]
                    del_p_toks = set(re.split(r"[-_]", del_p.lower()))
                    if del_p_toks.intersection({"at", "on", "in", "behind", "holding", "contains", "contain", "ontable", "inside", "lifting", "carrying"}):
                        for arg_idx, vac_arg in enumerate(del_args):
                            if not vac_arg.startswith("?"):
                                continue
                            # If vac_arg is re-bound at the same argument position of del_p in positive effects (e.g. moving entity ?r in (robot-at ?r ?to)), it is NOT vacated
                            still_bound_at_idx = any(
                                pa.strip("() ").split()[:1] == [del_p]
                                and len(pa.strip("() ").split()[1:]) == len(del_args)
                                and pa.strip("() ").split()[1:][arg_idx] == vac_arg
                                for pa in pos_eff_atoms
                            )
                            if still_bound_at_idx:
                                continue
                            vac_type = act_norm_p.get(vac_arg, "object")
                            for cp, target_ts in cp_target_types.items():
                                if f"({cp} {vac_arg})" in act_pos_precs or f"({cp} {vac_arg})" in pos_eff_atoms:
                                    continue
                                type_matches = any(
                                    t_cp != "object" and vac_type != "object" and (is_subtype(vac_type, t_cp) or is_subtype(t_cp, vac_type))
                                    for t_cp in target_ts
                                )
                                if not type_matches:
                                    continue
                                # Trigger if cp has zero positive effects in domain OR if this action deletes (not (cp ?other)) on another parameter of the same type
                                consumes_cp_on_peer = any(
                                    na.strip("() ").split()[:1] == [cp]
                                    and len(na.strip("() ").split()[1:]) == 1
                                    and na.strip("() ").split()[1] != vac_arg
                                    and is_subtype(act_norm_p.get(na.strip("() ").split()[1], "object"), vac_type)
                                    for na in neg_eff_atoms
                                )
                                if (cp not in produced_preds and cp not in pos_eff_preds) or (consumes_cp_on_peer and cp not in pos_eff_preds):
                                    bm_reason = (
                                        f"Action '{act_name}' vacates entity/location '{vac_arg}' (deleting '{ecanon}'), "
                                        f"but fails to assert the corresponding clearance/vacancy effect '({cp} {vac_arg})' in its positive effects. "
                                        f"Because other actions require '({cp} ...)' to enter or use '{vac_type}', "
                                        f"omitting '({cp} {vac_arg})' permanently locks '{vac_arg}', causing reachability deadlock. "
                                        f"In action '{act_name}' effects, add '({cp} {vac_arg})' as a positive effect."
                                    )
                                    if not any(bm.get("reason") == bm_reason for bm in bilateral_mutex_faults):
                                        bilateral_mutex_faults.append({
                                            "action_name": act_name,
                                            "predicate": cp,
                                            "expression": f"({cp} {vac_arg})",
                                            "reason": bm_reason
                                        })

    # If bilateral_mutex_faults already pinpointed the specific vacating actions for predicate cp,
    # remove generic irreversible_locks on cp so non-vacating actions (like paint-up) are not falsely told to drop their delete effects
    bm_covered_preds = {bm["predicate"] for bm in bilateral_mutex_faults}
    if bm_covered_preds:
        irreversible_locks = [il for il in irreversible_locks if il.get("predicate") not in bm_covered_preds or il.get("is_spurious_self_delete")]

    # Invariant 5: SAS+ Functional & Mutex State-Transition Delete Completeness (Helmert 2006)
    # If across the domain, transitions on entity type T that establish positive effect (P_add ?e ...)
    # consistently delete precondition (P_pre ?e ...) in at least one peer operator, then any operator
    # with precondition (P_pre ?e ...) and positive effect (P_add ?e ...) that omits (not (P_pre ?e ...))
    # leaves stale/contradictory fluents (violating SAS+ state-variable uniqueness and mutex invariants).
    missing_transition_deletes: List[Dict[str, Any]] = []
    self_del_evidence: Set[Tuple[str, str]] = set()
    cross_del_evidence: Set[Tuple[str, str, str]] = set()
    for act in actions:
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        act_np = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        pos_p = [normalize_atom_expression(p)[0] for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]]
        pos_e = [normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]]
        neg_e = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and not normalize_atom_expression(e)[1]}
        pos_p_by_ent = {(a.strip("() ").split()[0], a.strip("() ").split()[1]) for a in pos_p if len(a.strip("() ").split()) >= 2}
        pos_e_by_ent = {(a.strip("() ").split()[0], a.strip("() ").split()[1]) for a in pos_e if len(a.strip("() ").split()) >= 2}
        for pa in pos_p:
            if pa in neg_e:
                ptoks = pa.strip("() ").split()
                if len(ptoks) >= 2:
                    pp, pargs = ptoks[0], ptoks[1:]
                    ent_v = pargs[0]
                    ent_t = act_np.get(ent_v, "object")
                    for ea in pos_e:
                        if ea == pa:
                            continue
                        etoks = ea.strip("() ").split()
                        if len(etoks) >= 2 and etoks[1] == ent_v:
                            ep, eargs = etoks[0], etoks[1:]
                            if ep == pp and len(eargs) == len(pargs) and eargs != pargs:
                                self_del_evidence.add((pp, ent_t))
                            elif ep != pp and (pp, ent_v) not in pos_e_by_ent and (ep, ent_v) not in pos_p_by_ent:
                                cross_del_evidence.add((pp, ep, ent_t))
                                decl_t = (dom_pred_sigs.get(pp) or ("object",))[0]
                                if decl_t != "object":
                                    cross_del_evidence.add((pp, ep, decl_t))

    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        act_np = {(k if str(k).startswith("?") else f"?{k}"): _resolve_type(str(v).lower()) for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        pos_p = [normalize_atom_expression(p)[0] for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]]
        pos_e = [normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1]]
        neg_e = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[0] and not normalize_atom_expression(e)[1]}
        pos_p_by_ent = {(a.strip("() ").split()[0], a.strip("() ").split()[1]) for a in pos_p if len(a.strip("() ").split()) >= 2}
        pos_e_by_ent = {(a.strip("() ").split()[0], a.strip("() ").split()[1]) for a in pos_e if len(a.strip("() ").split()) >= 2}
        for pa in pos_p:
            if pa in neg_e or pa in pos_e:
                continue
            ptoks = pa.strip("() ").split()
            if len(ptoks) < 2:
                continue
            pp, pargs = ptoks[0], ptoks[1:]
            ent_v = pargs[0]
            ent_t = act_np.get(ent_v, "object")
            for ea in pos_e:
                etoks = ea.strip("() ").split()
                if len(etoks) >= 2 and etoks[1] == ent_v:
                    ep, eargs = etoks[0], etoks[1:]
                    if ep == pp and len(eargs) == len(pargs) and eargs != pargs:
                        if (pp, ent_t) in self_del_evidence or (pp in deleted_preds and len(pargs) == 2) or (pp in init_facts and len(pargs) == 2):
                            mtd_reason = (
                                f"Action '{act_name}' transitions '{pp}' on '{ent_v}' from precondition '{pa}' to positive effect '{ea}', "
                                f"but omits the required delete effect '(not {pa})'! "
                                f"In action '{act_name}' effects, add '(not {pa})'."
                            )
                            if not any(m.get("action_name") == act_name and m.get("expression") == pa for m in missing_transition_deletes):
                                missing_transition_deletes.append({
                                    "action_name": act_name,
                                    "predicate": pp,
                                    "expression": pa,
                                    "reason": mtd_reason
                                })
                    elif ep != pp and (pp, ent_v) not in pos_e_by_ent and (ep, ent_v) not in pos_p_by_ent:
                        is_unary_antonym = (
                            len(pargs) == 1
                            and len(eargs) == 1
                            and (pp in produced_preds or pp in deleted_preds)
                            and (ep in produced_preds or ep in deleted_preds)
                            and (
                                (pp.lower().startswith("un") and len(ep) >= 4 and ep.lower()[:4] in pp.lower())
                                or (ep.lower().startswith("un") and len(pp) >= 4 and pp.lower()[:4] in ep.lower())
                            )
                        )
                        decl_t = (dom_pred_sigs.get(pp) or ("object",))[0]
                        if (
                            (pp, ep, ent_t) in cross_del_evidence
                            or (ep, pp, ent_t) in cross_del_evidence
                            or (decl_t != "object" and ((pp, ep, decl_t) in cross_del_evidence or (ep, pp, decl_t) in cross_del_evidence))
                            or is_unary_antonym
                        ):
                            mtd_reason = (
                                f"Action '{act_name}' requires state precondition '{pa}' on '{ent_v}' and establishes mutex state '{ea}', "
                                f"but omits the required delete effect '(not {pa})'! "
                                f"In action '{act_name}' effects, add '(not {pa})'."
                            )
                            if not any(m.get("action_name") == act_name and m.get("expression") == pa for m in missing_transition_deletes):
                                missing_transition_deletes.append({
                                    "action_name": act_name,
                                    "predicate": pp,
                                    "expression": pa,
                                    "reason": mtd_reason
                                })

    summary_lines = []
    if ungroundable_preconditions:
        summary_lines.append("[UNGROUNDABLE ACTION PARAMETERS / PRECONDITIONS]:")
        for up in ungroundable_preconditions:
            summary_lines.append(f"  * Action '{up['action_name']}': {up['reason']}")
    if orphaned_goals:
        summary_lines.append("[UNPRODUCED GOAL PREDICATES]:")
        for og in orphaned_goals:
            summary_lines.append(f"  * Goal predicate '{og}' in P_gold :goal is not produced by any action's positive effects!")
    if directional_traps:
        summary_lines.append("[DIRECTIONAL ASYMMETRY / MISSING INVERSE ACTION]:")
        for dt in directional_traps:
            summary_lines.append(f"  * {dt['reason']}")
    if irreversible_locks:
        summary_lines.append("[IRREVERSIBLE RESOURCE DEPLETION / ABSORBING LOCKOUT]:")
        for il in irreversible_locks:
            summary_lines.append(f"  * Action '{il['action_name']}': {il['reason']}")
    if bilateral_mutex_faults:
        summary_lines.append("[BILATERAL MUTEX CLEARANCE CONSERVATION]:")
        for bm in bilateral_mutex_faults:
            summary_lines.append(f"  * Action '{bm['action_name']}': {bm['reason']}")
    if missing_transition_deletes:
        summary_lines.append("[MISSING STATE-TRANSITION DELETE EFFECTS]:")
        for mtd in missing_transition_deletes:
            summary_lines.append(f"  * Action '{mtd['action_name']}': {mtd['reason']}")
    if internal_contradictions:
        summary_lines.append("[CONTRADICTORY SIMULTANEOUS ACTION EFFECTS]:")
        for ic in internal_contradictions:
            summary_lines.append(f"  * {ic['description']}")

    # Detect circular precondition deadlock cycles on unseeded predicates and non-goal leaf bloat actions
    causal_cycles: List[Dict[str, Any]] = []
    non_goal_leaf_actions: List[str] = []
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])
        effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
        act_pos_precs = {
            normalize_atom_expression(p)[0].strip("() ").split()[0]
            for p in precs
            if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1] and normalize_atom_expression(p)[0].strip("() ").split()
        }
        act_pos_effs = {
            normalize_atom_expression(e)[0].strip("() ").split()[0]
            for e in effs
            if normalize_atom_expression(e)[0] and normalize_atom_expression(e)[1] and normalize_atom_expression(e)[0].strip("() ").split()
        }
        for p in sorted(act_pos_precs):
            if p not in init_facts and p in produced_preds:
                if p in act_pos_effs or not bootstrap_producers_by_pred.get(p.lower()):
                    causal_cycles.append({
                        "action_name": act_name,
                        "predicate": p,
                        "reason": f"Action '{act_name}' requires unseeded predicate '{p}' in a circular dependency loop."
                    })
        if act_pos_effs and not any(ep in goal_preds_set or ep in all_precond_preds for ep in act_pos_effs):
            non_goal_leaf_actions.append(act_name)

    top_act = None
    if internal_contradictions:
        top_act = internal_contradictions[0]["action_name"]
    elif ungroundable_preconditions:
        first_up_act = ungroundable_preconditions[0]["action_name"]
        if first_up_act == "types" and empty_type_actions:
            top_act = next(iter(empty_type_actions.values()))[0]
        else:
            top_act = first_up_act
    elif irreversible_locks:
        top_act = irreversible_locks[0]["action_name"]
    elif directional_traps and directional_traps[0].get("forward_actions"):
        top_act = directional_traps[0]["forward_actions"][0]
    elif bilateral_mutex_faults:
        top_act = bilateral_mutex_faults[0]["action_name"]
    elif missing_transition_deletes:
        top_act = missing_transition_deletes[0]["action_name"]

    return {
        "orphaned_goals": orphaned_goals,
        "internal_contradictions": internal_contradictions,
        "ungroundable_preconditions": ungroundable_preconditions,
        "directional_traps": directional_traps,
        "irreversible_locks": irreversible_locks,
        "bilateral_mutex_faults": bilateral_mutex_faults,
        "missing_transition_deletes": missing_transition_deletes,
        "causal_cycles": causal_cycles,
        "non_goal_leaf_actions": non_goal_leaf_actions,
        "top_action": top_act,
        "diagnostic_summary": "\n".join(summary_lines)
    }


def detect_add_precondition_clashes_and_ungrounded_dels(domain_bp: Any) -> List[Dict[str, Any]]:
    """
    Evaluates Yang et al. ARMS (2007) Invariants A.1 & A.2:
    - A.1 (Add-Precondition Disjointness): An action should not assert an add effect
          that is already declared in its preconditions (redundant/vacuous add effect).
    - A.2 (Delete Groundedness): Every variable appearing in a delete effect
          must be declared in the action's parameter list.
    """
    violations = []
    actions = getattr(domain_bp, "actions", []) if hasattr(domain_bp, "actions") else (domain_bp.get("actions", []) if isinstance(domain_bp, dict) else [])
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else (act.get("action_name", "") if isinstance(act, dict) else "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else (act.get("parameters", {}) if isinstance(act, dict) else {})
        param_vars = set(params.keys()) if isinstance(params, dict) else set(params)
        
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else (act.get("preconditions", []) if isinstance(act, dict) else [])
        effects = getattr(act, "effects", []) if hasattr(act, "effects") else (act.get("effects", []) if isinstance(act, dict) else [])
        
        prec_pos = set()
        for p in precs:
            canon, is_pos = normalize_atom_expression(p)
            if canon and is_pos:
                prec_pos.add(canon.lower())
                
        for eff in effects:
            canon, is_pos = normalize_atom_expression(eff)
            if not canon:
                continue
            if is_pos:
                if canon.lower() in prec_pos:
                    violations.append({
                        "action": act_name,
                        "type": "ADD_PRECONDITION_CLASH",
                        "literal": canon,
                        "description": f"Action '{act_name}' adds '{canon}' which is already required as a precondition (violates ARMS A.1)."
                    })
            else:
                toks = canon.strip("() ").split()
                if toks:
                    for arg in toks[1:]:
                        if arg.startswith("?") and arg not in param_vars:
                            violations.append({
                                "action": act_name,
                                "type": "UNGROUNDED_DELETE",
                                "literal": canon,
                                "variable": arg,
                                "description": f"Action '{act_name}' deletes '{canon}' with ungrounded variable '{arg}' not in parameters (violates ARMS A.2)."
                            })
    return violations


def detect_unbalanced_frame_transitions(domain_bp: Any) -> List[Dict[str, Any]]:
    """
    Evaluates SAS+ / Frame Axiom Multi-Valued State-Variable Invariants:
    When an action asserts a new state/location assignment for an entity
    (e.g. (at ?x ?to) or (on ?x ?y) or (in ?x ?c)), it must delete the previous assignment
    with the same primary entity argument to prevent object-cloning state anomalies.
    """
    violations = []
    actions = getattr(domain_bp, "actions", []) if hasattr(domain_bp, "actions") else (domain_bp.get("actions", []) if isinstance(domain_bp, dict) else [])
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else (act.get("action_name", "") if isinstance(act, dict) else "")
        effects = getattr(act, "effects", []) if hasattr(act, "effects") else (act.get("effects", []) if isinstance(act, dict) else [])
        
        pos_atoms = []
        del_atoms = []
        for eff in effects:
            canon, is_pos = normalize_atom_expression(eff)
            if not canon:
                continue
            toks = canon.strip("() ").split()
            if not toks:
                continue
            if is_pos:
                pos_atoms.append((toks[0].lower(), toks[1:]))
            else:
                del_atoms.append((toks[0].lower(), toks[1:]))
                
        frame_indicators = {"at", "on", "in", "carrying", "holding", "location", "pos"}
        for p_name, args in pos_atoms:
            if any(ind in p_name for ind in frame_indicators) and len(args) >= 2:
                primary_entity = args[0]
                has_delete = any(dp == p_name and d_args and d_args[0] == primary_entity for dp, d_args in del_atoms)
                if not has_delete:
                    violations.append({
                        "action": act_name,
                        "type": "UNBALANCED_FRAME_TRANSITION",
                        "predicate": p_name,
                        "entity": primary_entity,
                        "description": f"Action '{act_name}' adds '({p_name} {' '.join(args)})' without deleting previous state for '{primary_entity}', risking object-cloning."
                    })
    return violations


def detect_causal_type_mismatches(domain_bp: Any, problem_bp: Any = None) -> List[Dict[str, Any]]:
    """
    Evaluates Causal Producer-Consumer Type Signature Compatibility:
    Verifies that all predicate invocations across action preconditions and effects
    conform to declared predicate arity and parameter typing hierarchies.
    """
    violations = []
    dom_types_raw = getattr(domain_bp, "types", {}) if hasattr(domain_bp, "types") else (domain_bp.get("types", {}) if isinstance(domain_bp, dict) else {})
    is_subtype = _build_subtype_checker(dom_types_raw)
    
    dom_preds_raw = getattr(domain_bp, "predicates", []) if hasattr(domain_bp, "predicates") else (domain_bp.get("predicates", []) if isinstance(domain_bp, dict) else [])
    pred_sigs: Dict[str, List[str]] = {}
    for p_str in dom_preds_raw:
        p_clean = p_str.strip("() ").strip()
        if not p_clean:
            continue
        toks = p_clean.split()
        if not toks:
            continue
        p_name = toks[0].lower()
        args = toks[1:]
        types_list = []
        curr_vars = []
        i = 0
        while i < len(args):
            tok = args[i]
            if tok == "-":
                if i + 1 < len(args):
                    tname = args[i + 1].lower()
                    for _ in curr_vars:
                        types_list.append(tname)
                    curr_vars = []
                    i += 2
                    continue
            elif tok.startswith("?"):
                curr_vars.append(tok)
            i += 1
        for _ in curr_vars:
            types_list.append("object")
        pred_sigs[p_name] = types_list

    actions = getattr(domain_bp, "actions", []) if hasattr(domain_bp, "actions") else (domain_bp.get("actions", []) if isinstance(domain_bp, dict) else [])
    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else (act.get("action_name", "") if isinstance(act, dict) else "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else (act.get("parameters", {}) if isinstance(act, dict) else {})
        param_types = {k.lower(): str(v).lower() for k, v in params.items()} if isinstance(params, dict) else {}
        
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else (act.get("preconditions", []) if isinstance(act, dict) else [])
        effects = getattr(act, "effects", []) if hasattr(act, "effects") else (act.get("effects", []) if isinstance(act, dict) else [])
        
        for lit in precs + effects:
            canon, _ = normalize_atom_expression(lit)
            if not canon:
                continue
            toks = canon.strip("() ").split()
            if not toks:
                continue
            p_name = toks[0].lower()
            p_args = toks[1:]
            
            if p_name in pred_sigs:
                expected_types = pred_sigs[p_name]
                if len(p_args) != len(expected_types):
                    violations.append({
                        "action": act_name,
                        "type": "ARITY_MISMATCH",
                        "predicate": p_name,
                        "expected_arity": len(expected_types),
                        "actual_arity": len(p_args),
                        "description": f"Action '{act_name}' uses '{p_name}' with {len(p_args)} args, expected {len(expected_types)}."
                    })
                else:
                    for arg_var, exp_type in zip(p_args, expected_types):
                        if arg_var.startswith("?") and arg_var.lower() in param_types:
                            actual_type = param_types[arg_var.lower()]
                            if exp_type != "object" and not is_subtype(actual_type, exp_type):
                                violations.append({
                                    "action": act_name,
                                    "type": "TYPE_SIGNATURE_MISMATCH",
                                    "predicate": p_name,
                                    "variable": arg_var,
                                    "actual_type": actual_type,
                                    "expected_type": exp_type,
                                    "description": f"Action '{act_name}' passes '{arg_var}' ({actual_type}) to '{p_name}' which expects '{exp_type}'."
                                })
    return violations
