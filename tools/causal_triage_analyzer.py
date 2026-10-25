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


def run_causal_triage_analysis(
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

    # Skip static reachability analysis when VAL reports syntax or type-checking errors
    if any("VAL Error:" in err for err in (raw_errors or [])):
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
    internal_contradictions: List[Dict[str, Any]] = []
    ungroundable_preconditions: List[Dict[str, Any]] = []

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

                        if best_act and best_act_score >= 40.0:
                            reason_msg = (
                                f"Goal predicate '{gpred}' in P_gold :goal is not produced by any action! "
                                f"Action '{best_act}' has the closest semantic role and parameter signature to establish this goal. "
                                f"In domain 'actions', add '({gpred} ...)' as a positive effect to action '{best_act}' with the corresponding parameters."
                            )
                        else:
                            reason_msg = (
                                f"Goal predicate '{gpred}' in P_gold :goal is not produced by any action in the domain! "
                                f"Check the problem requirements and add '({gpred} ...)' as a positive effect to the primary goal-achieving action."
                            )

                        ungroundable_preconditions.append({
                            "action_name": best_act or "domain.actions",
                            "predicate": gpred,
                            "expression": f"({gpred} ...)",
                            "best_match": gpred,
                            "reason": reason_msg
                        })
                elif gpred in produced_preds and gargs not in init_facts.get(gpred, []):
                    g_arg_types = [all_objs.get(x, "object") for x in gargs]
                    can_ground_goal = False
                    narrow_producers = []
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
                        if can_ground_goal:
                            break
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
                                        f"which CANNOT ground P_gold :goal atom '{canon}' where object '{g_obj}' has type '{g_type}'! "
                                        f"In action '{act_name}' parameters, generalize '{p_var}' from '{p_type}' to supertype '{sup_hint}' "
                                        f"(and ensure any predicate in domain 'predicates' that takes '{p_var}' also accepts '{sup_hint}')."
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
                                reason_msg = (
                                    f"Goal atom '{g_at}' is unreachable via action '{act_n}': effect produces '{gpred}', "
                                    f"but parameter '{p_var}' is co-indexed (aliased) in static precondition '({s_pred} ...)' "
                                    f"at position {item['pos'] + 1}. Because '{s_pred}' is static, this restricts '{p_var}' to the stationary "
                                    f"entity/location of '{s_pred}' and prevents action '{act_n}' from achieving arbitrary goal instances such as '{g_at}'! "
                                    f"In action '{act_n}', unbind '{p_var}' from '({s_pred} ...)' by introducing a distinct parameter variable "
                                    f"(e.g. a separate variable for '{s_pred}') in action parameters and '({s_pred} ...)' so that '{p_var}' is free to ground '{c_v}'. "
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

    for init_pred, fact_args_list in init_facts.items():
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
                                        f"In action '{act_name}' preconditions, replace '{pcanon}' with '({best_alt_p} {' '.join(p_vars)})' to use the correct problem predicate."
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
                                        type_sig_reason = (
                                            f"Precondition '{pcanon}' in action '{act_name}' requires argument types {p_types}, "
                                            f"which contradicts the immutable problem contract P_gold :init for predicate '{init_pred}' (expected types: {f_arg_types}). "
                                            f"In action '{act_name}' parameters and preconditions, bind parameters with types matching {f_arg_types} to '({init_pred} ...)'. "
                                            f"(Do NOT declare incompatible types as inheriting from each other)."
                                        )
                                if not any(u.get("action_name") == act_name and u.get("expression") == pcanon for u in ungroundable_preconditions):
                                    ungroundable_preconditions.append({
                                        "action_name": act_name,
                                        "predicate": init_pred,
                                        "expression": pcanon,
                                        "best_match": None,
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
            norm_p = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
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
                            rt[0] == ppred and len(rt[1]) == len(pargs_t) and all(is_subtype(rt_elem, pt_elem) for rt_elem, pt_elem in zip(rt[1], pargs_t))
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
                            sub_options = []
                            for t in eargs_t:
                                if t != "object":
                                    subs = [st for st in dom_types_raw.keys() if is_subtype(st, t)]
                                    sub_options.append(subs if subs else [t])
                                else:
                                    sub_options.append([t])
                            for comb in itertools.product(*sub_options):
                                if (epred, comb) not in reachable_types:
                                    reachable_types.add((epred, comb))
                                    changed = True

    for act in actions:
        act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
        params = getattr(act, "parameters", {}) if hasattr(act, "parameters") else act.get("parameters", {})
        norm_params = {(k if str(k).startswith("?") else f"?{k}"): str(v).lower() for k, v in (params.items() if isinstance(params, dict) else []) if v}
        precs = getattr(act, "preconditions", []) if hasattr(act, "preconditions") else act.get("preconditions", [])

        for prec in precs:
            canon, is_pos = normalize_atom_expression(prec)
            if not canon or not is_pos:
                continue
            toks = canon.strip("() ").split()
            if not toks:
                continue
            pname, args = toks[0], toks[1:]
            req_types = [norm_params.get(a if a.startswith("?") else f"?{a}", all_objs.get(a, "object")) for a in args]

            # Atom is reachable if initial seed exists or forward reachability can produce it
            is_unreachable = not any(
                rt[0] == pname and len(rt[1]) == len(req_types) and all(is_subtype(rt_elem, pt_elem) for rt_elem, pt_elem in zip(rt[1], req_types))
                for rt in reachable_types
            )

            if not is_unreachable:
                continue

            # Precondition atom is dead/unreachable. Perform formal diagnostic localization:
            if any(u.get("action_name") == act_name and u.get("expression") == canon for u in ungroundable_preconditions):
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
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "reason": reason_msg
                })
                continue

            # Sub-case B: Search P_gold :init and declared domain predicates for specialized predicate alt_p matching req_types
            matching_alt_preds = []
            for alt_p, sigs in init_types_by_pred.items():
                if alt_p.lower() == pname.lower():
                    continue
                for sig in sigs:
                    if len(sig) == len(req_types) and all(is_subtype(r_t, s_t) or is_subtype(s_t, r_t) for s_t, r_t in zip(sig, req_types)):
                        alt_clean = alt_p.lower().replace("-", "_")
                        p_clean = pname.lower().replace("-", "_")
                        alt_tokens = set(alt_clean.split("_"))
                        p_tokens = set(p_clean.split("_"))
                        overlap = len(alt_tokens.intersection(p_tokens))
                        ratio = difflib.SequenceMatcher(None, p_clean, alt_clean).ratio()
                        score = (100 * overlap) + (50 * ratio) + 20.0
                        matching_alt_preds.append((score, alt_p, sig, "init"))
                        break

            for alt_p, dom_sig in dom_pred_sigs.items():
                if alt_p.lower() == pname.lower():
                    continue
                if len(dom_sig) == len(req_types) and all(is_subtype(r_t, s_t) or is_subtype(s_t, r_t) for s_t, r_t in zip(dom_sig, req_types)):
                    if not any(x[1].lower() == alt_p.lower() for x in matching_alt_preds):
                        alt_clean = alt_p.lower().replace("-", "_")
                        p_clean = pname.lower().replace("-", "_")
                        alt_tokens = set(alt_clean.split("_"))
                        p_tokens = set(p_clean.split("_"))
                        overlap = len(alt_tokens.intersection(p_tokens))
                        ratio = difflib.SequenceMatcher(None, p_clean, alt_clean).ratio()
                        score = (100 * overlap) + (50 * ratio)
                        matching_alt_preds.append((score, alt_p, dom_sig, "domain_predicates"))

            if matching_alt_preds:
                matching_alt_preds.sort(key=lambda x: x[0], reverse=True)
                best_alt_p = matching_alt_preds[0][1]
                source_type = matching_alt_preds[0][3]
                if source_type == "init":
                    sample_facts = init_facts.get(best_alt_p, [])
                    sample_str = f" (e.g. '({best_alt_p} {' '.join(sample_facts[0])})')" if sample_facts else ""
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init for predicate '{pname}' (and no action produces it from the initial state). "
                        f"However, P_gold :init declares initial facts for {req_types} under the specialized predicate symbol '{best_alt_p}'{sample_str}. "
                        f"In domain 'predicates', action '{act_name}' preconditions, and any related effects, replace '{pname}' with the specialized P_gold symbol '{best_alt_p}'."
                    )
                else:
                    reason_msg = (
                        f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                        f"which has ZERO matching facts in P_gold :init for predicate '{pname}' (and no action produces it). "
                        f"However, domain 'predicates' declares predicate '({best_alt_p} ...)' specifically for types {list(matching_alt_preds[0][2])}. "
                        f"In action '{act_name}' preconditions, replace '{canon}' with '({best_alt_p} {' '.join(args)})' to bind the correct relation."
                    )
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": best_alt_p,
                    "reason": reason_msg
                })
                continue

            # Sub-case C: Check identifier variations under find_best_symbol_match
            best_match = find_best_symbol_match(pname, list(init_facts.keys()))
            if best_match and best_match.lower() != pname.lower():
                is_best_static = best_match not in produced_preds and best_match not in deleted_preds
                stat_str = "static " if is_best_static else ""
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' is unreachable: predicate '{pname}' has ZERO facts in P_gold :init "
                    f"and ZERO actions produce it. P_gold :init defines the matching {stat_str}predicate '{best_match}'. "
                    f"In domain 'predicates' and action '{act_name}' preconditions, replace predicate '{pname}' with the exact P_gold symbol '{best_match}'."
                )
                ungroundable_preconditions.append({
                    "action_name": act_name,
                    "predicate": pname,
                    "expression": canon,
                    "best_match": best_match,
                    "reason": reason_msg
                })
                continue

            # Sub-case D: General fallback diagnostic
            init_facts_lower = {k.lower(): v for k, v in init_facts.items()}
            init_types_lower = {k.lower(): v for k, v in init_types_by_pred.items()}
            if pname.lower() not in init_facts_lower:
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' is unreachable: predicate '{pname}' has ZERO facts in P_gold :init "
                    f"and ZERO actions in the domain produce '({pname} ...)' from the initial state! "
                    f"Add '({pname} ...)' as a positive effect on the producer action described in the requirements, "
                    f"or replace '{pname}' with the matching predicate from P_gold :init ({sorted(init_facts.keys())})."
                )
            else:
                avail = [list(ft) for ft in sorted(init_types_lower.get(pname.lower(), set()))]
                reason_msg = (
                    f"Precondition '{canon}' in action '{act_name}' requires argument types {req_types}, "
                    f"which has ZERO matching facts in P_gold :init (available :init type signatures for '{pname}': {avail}). "
                    f"Check argument order, parameter types, or whether types in {req_types} should inherit from {avail[0]} in domain 'types'."
                )
            ungroundable_preconditions.append({
                "action_name": act_name,
                "predicate": pname,
                "expression": canon,
                "reason": reason_msg
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
        act_prec_preds = {normalize_atom_expression(p)[0].strip("() ").split()[0] for p in precs if normalize_atom_expression(p)[0] and normalize_atom_expression(p)[1]}

        for eff in effs:
            ecanon, eis_pos = normalize_atom_expression(eff)
            if not ecanon or eis_pos:
                continue
            etoks = ecanon.strip("() ").split()
            if not etoks:
                continue
            del_pname = etoks[0]
            if del_pname not in produced_preds and (del_pname in act_prec_preds or del_pname in all_precond_preds):
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
                        "reason": lock_reason
                    })

    # Invariant 4e: Bilateral Mutex Clearance Conservation (Moving / Vacating Slots)
    clearance_preds = {p for p in all_precond_preds if any(k in p.lower() for k in ["clear", "empty", "free", "available", "clean", "vacant"])}
    bilateral_mutex_faults: List[Dict[str, Any]] = []
    if clearance_preds:
        for act in actions:
            act_name = getattr(act, "action_name", "") if hasattr(act, "action_name") else act.get("action_name", "")
            effs = getattr(act, "effects", []) if hasattr(act, "effects") else act.get("effects", [])
            pos_eff_atoms = {normalize_atom_expression(e)[0] for e in effs if normalize_atom_expression(e)[1]}
            pos_eff_preds = {a.strip("() ").split()[0] for a in pos_eff_atoms if a}
            
            for eff in effs:
                ecanon, eis_pos = normalize_atom_expression(eff)
                if not ecanon or eis_pos:
                    continue
                etoks = ecanon.strip("() ").split()
                if len(etoks) >= 2:
                    del_p, del_args = etoks[0], etoks[1:]
                    if any(k in del_p.lower() for k in ["at", "on", "in", "behind", "holding", "contain"]):
                        for vac_arg in del_args:
                            if vac_arg.startswith("?"):
                                for cp in clearance_preds:
                                    if cp not in produced_preds and cp not in pos_eff_preds:
                                        matching_req = False
                                        for o_act in actions:
                                            o_precs = getattr(o_act, "preconditions", []) if hasattr(o_act, "preconditions") else o_act.get("preconditions", [])
                                            for op in o_precs:
                                                op_c, op_pos = normalize_atom_expression(op)
                                                if op_c and op_pos:
                                                    op_toks = op_c.strip("() ").split()
                                                    if op_toks and op_toks[0] == cp and len(op_toks) > 1 and vac_arg in op_toks[1:]:
                                                        matching_req = True
                                                        break
                                            if matching_req:
                                                break
                                        if matching_req:
                                            bm_reason = (
                                                f"Action '{act_name}' vacates entity/location '{vac_arg}' (deleting '{ecanon}'), "
                                                f"but fails to assert the corresponding clearance/vacancy effect '({cp} {vac_arg})' in its positive effects. "
                                                f"Because other actions require '({cp} {vac_arg})' to enter or use '{vac_arg}', "
                                                f"and predicate '{cp}' has ZERO positive effects in the domain, "
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
    if internal_contradictions:
        summary_lines.append("[CONTRADICTORY SIMULTANEOUS ACTION EFFECTS]:")
        for ic in internal_contradictions:
            summary_lines.append(f"  * {ic['description']}")

    return {
        "orphaned_goals": orphaned_goals,
        "internal_contradictions": internal_contradictions,
        "ungroundable_preconditions": ungroundable_preconditions,
        "directional_traps": directional_traps,
        "irreversible_locks": irreversible_locks,
        "bilateral_mutex_faults": bilateral_mutex_faults,
        "causal_cycles": [],
        "top_action": ungroundable_preconditions[0]["action_name"] if ungroundable_preconditions else None,
        "diagnostic_summary": "\n".join(summary_lines)
    }
