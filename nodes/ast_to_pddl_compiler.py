"""
nodes/ast_to_pddl_compiler.py
Pure, deterministic compilation engine translating structured DomainRepresentation ASTs into valid PDDL 2.1 syntax.
Contains zero LangGraph or agent state dependencies.
"""

import re
from typing import Optional, Dict, Any, List, Set
from nodes.schemas.pddl_representation import DomainRepresentation, PddlActionSchema
from nodes.pddl_to_ast_parser import extract_pddl_problem_metadata
from tools.pddl_utils import (
    normalize_pddl_expression,
    normalize_atom,
    flatten_atoms,
    find_common_supertype,
    parse_typed_params,
)


def enforce_effect_consistency(raw_effects: list) -> list:
    """Enforces classical PDDL 2.1 effect consistency: prunes delete effects that conflict with positive add effects."""
    flat = flatten_atoms(raw_effects)
    pos_atoms = set()
    for eff in flat:
        atom, is_pos = normalize_atom(eff)
        if is_pos:
            pos_atoms.add(atom)

    consistent_effects = []
    seen = set()
    for eff in flat:
        atom, is_pos = normalize_atom(eff)
        if not is_pos and atom in pos_atoms:
            # Positive add takes precedence over delete under STRIPS update semantics
            continue
        clean_eff = atom if is_pos else f"(not {atom})"
        if clean_eff not in seen:
            seen.add(clean_eff)
            consistent_effects.append(clean_eff)
    return consistent_effects


def synchronize_ast_predicate_symbols(representation_data: dict, problem_pddl: Optional[str] = None) -> dict:
    """Synchronizes domain predicate symbols to match problem predicate naming."""
    if not problem_pddl or not isinstance(representation_data, dict):
        return representation_data

    prob_meta = extract_pddl_problem_metadata(problem_pddl)
    prob_atoms = flatten_atoms(prob_meta.get("initial_state", [])) + flatten_atoms(prob_meta.get("goal_state", []))
    prob_pred_map: Dict[str, str] = {}
    for a in prob_atoms:
        atom, _ = normalize_atom(a)
        toks = atom.strip("() ").split()
        if toks:
            sym = toks[0]
            norm_key = sym.lower().replace("-", "_")
            prob_pred_map[norm_key] = sym

    if not prob_pred_map:
        return representation_data

    def _replace_sym(atom_str: str) -> str:
        atom, is_pos = normalize_atom(atom_str)
        toks = atom.strip("() ").split()
        if not toks:
            return atom_str
        norm_key = toks[0].lower().replace("-", "_")
        if norm_key in prob_pred_map:
            toks[0] = prob_pred_map[norm_key]
        core = f"({' '.join(toks)})"
        return core if is_pos else f"(not {core})"

    representation_data["predicates"] = [_replace_sym(p) for p in representation_data.get("predicates", [])]
    for act in representation_data.get("actions", []):
        if isinstance(act, dict):
            act["preconditions"] = [_replace_sym(p) for p in act.get("preconditions", [])]
            act["effects"] = [_replace_sym(e) for e in act.get("effects", [])]

    return representation_data


def compile_pddl_programmatically(representation_data: dict, problem_pddl: Optional[str] = None) -> str:
    """Compiles a DomainRepresentation dictionary into a PDDL domain string."""
    if problem_pddl:
        synchronize_ast_predicate_symbols(representation_data, problem_pddl)

    prob_meta = extract_pddl_problem_metadata(problem_pddl) if (problem_pddl and isinstance(problem_pddl, str)) else {}
    raw_dname = prob_meta.get("domain_name") or representation_data.get("domain_name", "generated_domain")
    domain_name = re.sub(r'\.pddl$', '', str(raw_dname), flags=re.IGNORECASE)
    domain_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', domain_name) or "generated_domain"

    requirements = representation_data.get("requirements", [":strips", ":typing"])
    types = representation_data.get("types", {})
    predicates = representation_data.get("predicates", [])
    actions = representation_data.get("actions", [])

    pddl_lines = []

    # 1. Header & Requirements
    pddl_lines.append(f"(define (domain {domain_name})")
    req_str = " ".join(requirements) if isinstance(requirements, list) else ":strips :typing"
    has_typing = ":typing" in req_str
    has_negative_preconditions = ":negative-preconditions" in req_str
    pddl_lines.append(f"  (:requirements {req_str})")
    pddl_lines.append("")

    # 2. Types Hierarchy Block
    def _sanitize_type(t_val: Any) -> Optional[str]:
        if not t_val:
            return None
        s = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(t_val).strip()).strip("_")
        return s if s and s.lower() not in ("none", "null") else None

    normalized_types: Dict[str, Optional[str]] = {}
    if isinstance(types, dict):
        for child, parent in types.items():
            c_clean = _sanitize_type(child)
            p_clean = _sanitize_type(parent)
            if c_clean and c_clean.lower() != "object":
                normalized_types[c_clean] = p_clean if p_clean and p_clean.lower() != c_clean.lower() else None
    elif isinstance(types, list):
        for item in types:
            if "-" in str(item):
                parts = str(item).split("-")
                parent = _sanitize_type(parts[1])
                for c in parts[0].strip().split():
                    c_clean = _sanitize_type(c)
                    if c_clean and c_clean.lower() != "object":
                        normalized_types[c_clean] = parent if parent and parent.lower() != c_clean.lower() else None
            else:
                for c in str(item).strip().split():
                    c_clean = _sanitize_type(c)
                    if c_clean and c_clean.lower() != "object":
                        normalized_types[c_clean] = None

    # Discover any undeclared types used in predicates or actions
    if has_typing:
        for p in predicates:
            for t in re.findall(r"\?\w+\s*-\s*([a-zA-Z0-9_\-]+)", str(p)):
                if t.lower() != "object" and t not in normalized_types:
                    normalized_types[t] = None
        for act in actions:
            act_params = act.get("parameters", {}) if isinstance(act, dict) else getattr(act, "parameters", {})
            if isinstance(act_params, dict):
                for ptype in act_params.values():
                    if ptype and str(ptype).lower() != "object" and str(ptype) not in normalized_types:
                        normalized_types[str(ptype)] = None
        if prob_meta and isinstance(prob_meta, dict):
            for obj_type in prob_meta.get("objects", {}).values():
                if obj_type and str(obj_type).lower() != "object" and str(obj_type) not in normalized_types:
                    normalized_types[str(obj_type)] = None

        # Ensure all referenced parents exist under 'object'
        all_parents = {p for p in normalized_types.values() if p and str(p).lower() != "object"}
        for p in all_parents:
            if p not in normalized_types:
                normalized_types[p] = "object"

    filtered_types = {c: p for c, p in normalized_types.items() if c and c.lower() != "object"}
    if filtered_types and has_typing:
        pddl_lines.append("  (:types")
        supertype_map: Dict[str, List[str]] = {}
        for child, parent in filtered_types.items():
            parent_key = parent if (parent and parent.lower() not in ("none", "null") and parent.lower() != child.lower()) else "object"
            supertype_map.setdefault(parent_key, []).append(child)

        for parent, children in supertype_map.items():
            children_str = " ".join(sorted(set(children)))
            pddl_lines.append(f"    {children_str} - {parent}")
        pddl_lines.append("  )")
        pddl_lines.append("")

    # 3. Constants Block
    raw_constants = representation_data.get("constants", {}) if isinstance(representation_data, dict) else getattr(representation_data, "constants", {})
    prob_objs = {str(k).strip().lower() for k in prob_meta.get("objects", {}).keys()} if prob_meta else set()
    valid_constants = {}
    if isinstance(raw_constants, dict):
        for cname, ctype in raw_constants.items():
            c_str = str(cname).strip()
            if c_str and c_str.lower() not in prob_objs and re.match(r'^[a-zA-Z][a-zA-Z0-9_\-]*$', c_str):
                valid_constants[c_str] = ctype if ctype else "object"

    if valid_constants:
        pddl_lines.append("  (:constants")
        const_map: Dict[str, List[str]] = {}
        for cname, ctype in valid_constants.items():
            const_map.setdefault(str(ctype) if ctype else "object", []).append(cname)
        for ctype, clist in const_map.items():
            cstr = " ".join(sorted(clist))
            pddl_lines.append(f"    {cstr} - {ctype}")
        pddl_lines.append("  )")
        pddl_lines.append("")

    # 4. Predicates Block & Signature Alignment
    RESERVED_WORDS = {"not", "and", "or", "imply", "exists", "forall", "object", "-", "="}
    pred_map: Dict[str, List[tuple]] = {}
    for pred in predicates:
        atom, _ = normalize_atom(str(pred))
        tokens = atom.strip("() ").split()
        if not tokens or tokens[0].lower() in RESERVED_WORDS:
            continue
        pname = tokens[0]
        params = parse_typed_params(tokens[1:])
        if pname not in pred_map:
            pred_map[pname] = params
        else:
            existing = pred_map[pname]
            if len(existing) == len(params):
                pred_map[pname] = [
                    (v1, find_common_supertype(t1, t2, normalized_types) if has_typing else "object")
                    for (v1, t1), (v2, t2) in zip(existing, params)
                ]

    # Unify predicate signatures with problem initial and goal atoms
    if prob_meta and isinstance(prob_meta, dict):
        obj_types = prob_meta.get("objects", {})
        prob_atoms = flatten_atoms(prob_meta.get("initial_state", [])) + flatten_atoms(prob_meta.get("goal_state", []))
        for atom_str in prob_atoms:
            atom, _ = normalize_atom(atom_str)
            tokens = atom.strip("() ").split()
            if not tokens or tokens[0].lower() in RESERVED_WORDS:
                continue
            pname = tokens[0]
            args = tokens[1:]
            inferred_types = [obj_types.get(arg, "object") for arg in args]
            matching_key = next((k for k in pred_map.keys() if k.lower() == pname.lower()), None)
            if not matching_key:
                pred_map[pname] = [(f"?x{i+1}", inferred_types[i]) for i in range(len(args))]
            else:
                existing = pred_map[matching_key]
                if len(existing) == len(inferred_types):
                    pred_map[matching_key] = [
                        (v1, find_common_supertype(t1, t2, normalized_types) if has_typing else "object")
                        for (v1, t1), t2 in zip(existing, inferred_types)
                    ]
                else:
                    pred_map[matching_key] = [(f"?x{i+1}", inferred_types[i]) for i in range(len(args))]

    if pred_map:
        pddl_lines.append("  (:predicates")
        for pname, params in pred_map.items():
            if not params:
                pddl_lines.append(f"    ({pname})")
            elif has_typing:
                p_str = " ".join([f"{v if v.startswith('?') else '?' + v} - {t}" for v, t in params])
                pddl_lines.append(f"    ({pname} {p_str})")
            else:
                p_str = " ".join([v if v.startswith('?') else '?' + v for v, _ in params])
                pddl_lines.append(f"    ({pname} {p_str})")
        pddl_lines.append("  )")
        pddl_lines.append("")

    # 5. Action Schemas Compilation
    for act in actions:
        if isinstance(act, dict):
            act_obj = PddlActionSchema(**act)
        else:
            act_obj = act

        flat_preconds = flatten_atoms(act_obj.preconditions)
        flat_effects = enforce_effect_consistency(act_obj.effects)

        # Validate preconditions against declared predicate arities
        sanitized_preconds = []
        for prec in flat_preconds:
            atom, is_pos = normalize_atom(prec)
            if not is_pos and not has_negative_preconditions:
                continue
            parts = atom.strip("() ").split()
            if parts:
                p_sym = parts[0]
                matching_k = next((k for k in pred_map.keys() if k.lower() == p_sym.lower()), None)
                if matching_k and len(parts[1:]) != len(pred_map[matching_k]):
                    continue
            sanitized_preconds.append(prec)

        # Validate effects against declared predicate arities
        sanitized_effects = []
        for eff in flat_effects:
            atom, is_pos = normalize_atom(eff)
            parts = atom.strip("() ").split()
            if parts:
                p_sym = parts[0]
                matching_k = next((k for k in pred_map.keys() if k.lower() == p_sym.lower()), None)
                if matching_k and len(parts[1:]) != len(pred_map[matching_k]):
                    continue
            sanitized_effects.append(eff)

        # Infer missing parameter types for variables in preconditions and effects
        all_action_atoms = sanitized_preconds + sanitized_effects
        used_vars = set(re.findall(r'\?[a-zA-Z0-9_\-]+', " ".join(all_action_atoms)))
        norm_params = {k if k.startswith("?") else f"?{k}": v for k, v in act_obj.parameters.items()}
        for mv in sorted(used_vars - set(norm_params.keys())):
            inferred_t = "object"
            for atom_str in all_action_atoms:
                atom, _ = normalize_atom(atom_str)
                parts = atom.strip("() ").split()
                if parts and mv in parts[1:]:
                    idx = parts[1:].index(mv)
                    p_sym = parts[0]
                    if p_sym in pred_map and idx < len(pred_map[p_sym]):
                        inferred_t = pred_map[p_sym][idx][1]
                        break
            norm_params[mv] = inferred_t
        act_obj.parameters = norm_params

        pddl_lines.append(f"  (:action {act_obj.action_name}")

        # Parameters
        if has_typing:
            param_parts = [f"{v if v.startswith('?') else '?' + v} - {t or 'object'}" for v, t in act_obj.parameters.items()]
        else:
            param_parts = [f"{v if v.startswith('?') else '?' + v}" for v in act_obj.parameters.keys()]
        pddl_lines.append(f"    :parameters ({' '.join(param_parts)})")

        # Preconditions
        if len(sanitized_preconds) == 1:
            pddl_lines.append(f"    :precondition {normalize_pddl_expression(sanitized_preconds[0])}")
        elif len(sanitized_preconds) > 1:
            pres = " ".join([normalize_pddl_expression(p) for p in sanitized_preconds])
            pddl_lines.append(f"    :precondition (and {pres})")
        else:
            pddl_lines.append("    :precondition (and)")

        # Effects
        if len(sanitized_effects) == 1:
            pddl_lines.append(f"    :effect {normalize_pddl_expression(sanitized_effects[0])}")
        elif len(sanitized_effects) > 1:
            effs = " ".join([normalize_pddl_expression(e) for e in sanitized_effects])
            pddl_lines.append(f"    :effect (and {effs})")
        else:
            pddl_lines.append("    :effect (and)")

        pddl_lines.append("  )")
        pddl_lines.append("")

    pddl_lines.append(")")
    return "\n".join(pddl_lines)
