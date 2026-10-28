#!/usr/bin/env python3
"""
tools/blueprint_parser.py
Universal deterministic PDDL domain and problem string-to-AST blueprint parsers.
Provides centralized AST blueprint conversion across the lifecycle agent,
reducing code duplication in app.py, benchmark loaders, and evaluation scripts.
"""

import re
from typing import Dict, List, Set, Any, Optional, Tuple

def extract_predicate_names(atom_list: List[str]) -> Set[str]:
    """Extracts base predicate names from a list of PDDL atom strings."""
    preds = set()
    for atom in atom_list:
        clean = atom.strip().replace("(", "").replace(")", "").replace("not", "").strip()
        tokens = clean.split()
        if tokens:
            preds.add(tokens[0].lower())
    return preds

def clean_blueprint_expression(raw_s: str) -> Optional[str]:
    """Cleans an individual PDDL precondition or effect expression into a valid blueprint atom."""
    s = raw_s.strip()
    if not s or s.lower() == "and":
        return None
    while s.startswith("((") and s.endswith("))"):
        s = s[1:-1].strip()
    if not s.startswith("("):
        s = f"({s}"
    if not s.endswith(")"):
        s = f"{s})"
    while re.match(r"^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$", s, flags=re.IGNORECASE):
        s = re.sub(r"^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$", r"\1", s, flags=re.IGNORECASE).strip()
    # Strip accidental inline typing in atomic formulas (classical PDDL 2.1 invariant)
    s = re.sub(r"(\?[a-zA-Z0-9_\-]+|[a-zA-Z0-9_\-]+)\s+-\s+[a-zA-Z0-9_\-]+", r"\1", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def alpha_convert_action_variables(
    action_name: str,
    parameters: Dict[str, str],
    preconditions: List[str],
    effects: List[str],
    predicates: List[str],
    types_hierarchy: Optional[Dict[str, str]] = None
) -> Tuple[List[str], List[str]]:
    """
    Universal FOL Alpha-Conversion for PDDL Action Schemas:
    Aligns locally renamed dummy variables in action preconditions/effects
    to the declared formal parameter names of that action based on predicate
    argument types and classical first-order logic variable binding invariants.
    """
    if not parameters:
        return preconditions, effects

    norm_params: Dict[str, str] = {
        (k if k.startswith("?") else f"?{k}"): str(v).lower()
        for k, v in parameters.items()
    }
    canon_vars = set(norm_params.keys())

    # Parse predicate signatures: predicate_name -> list of parameter types
    pred_sigs: Dict[str, List[str]] = {}
    for p in predicates:
        pm = re.match(r"\(\s*([a-zA-Z0-9_\-]+)\s*(.*?)\)", str(p))
        if pm:
            psym = pm.group(1).lower()
            rest = pm.group(2)
            ptypes: List[str] = []
            tokens = rest.split()
            cur: List[str] = []
            i = 0
            while i < len(tokens):
                if tokens[i] == "-":
                    t = tokens[i + 1].lower() if i + 1 < len(tokens) else "object"
                    for _ in cur:
                        ptypes.append(t)
                    cur = []
                    i += 2
                elif tokens[i].startswith("?"):
                    cur.append(tokens[i])
                    i += 1
                else:
                    i += 1
            for _ in cur:
                ptypes.append("object")
            pred_sigs[psym] = ptypes

    def extract_atoms(exprs: List[str]) -> List[Tuple[str, List[str]]]:
        atoms: List[Tuple[str, List[str]]] = []
        for e in exprs:
            for m in re.finditer(r"\(\s*([a-zA-Z0-9_\-]+)\s*(.*?)\)", str(e)):
                sym = m.group(1).lower()
                if sym in ("not", "and", "or", "imply", "forall", "exists"):
                    continue
                args = [a for a in m.group(2).split() if a.startswith("?")]
                atoms.append((sym, args))
        return atoms

    all_atoms = extract_atoms(preconditions) + extract_atoms(effects)
    used_vars = {v for _, args in all_atoms for v in args}

    unbound_vars = [v for v in sorted(used_vars) if v not in canon_vars]
    if not unbound_vars:
        return preconditions, effects

    unused_params = [p for p in norm_params.keys() if p not in used_vars]
    if not unused_params:
        return preconditions, effects

    # Subtype helper
    def is_type_compatible(actual: str, declared: str) -> bool:
        if not actual or not declared:
            return False
        a, d = actual.lower(), declared.lower()
        if a == d or d == "object" or a == "object":
            return True
        if types_hierarchy and isinstance(types_hierarchy, dict):
            curr = a
            while curr in types_hierarchy and types_hierarchy[curr]:
                curr = types_hierarchy[curr].lower()
                if curr == d:
                    return True
        return False

    # Infer type of each unbound variable from its positions in predicate atoms
    inferred_unbound_types: Dict[str, Set[str]] = {}
    for sym, args in all_atoms:
        if sym in pred_sigs:
            sig = pred_sigs[sym]
            for idx, arg in enumerate(args):
                if arg in unbound_vars and idx < len(sig):
                    inferred_unbound_types.setdefault(arg, set()).add(sig[idx])

    var_mapping: Dict[str, str] = {}
    remaining_params = list(unused_params)

    for uv in unbound_vars:
        types = inferred_unbound_types.get(uv, set())
        if not types:
            continue
        req_type = next(iter(types))
        compatible = [p for p in remaining_params if is_type_compatible(req_type, norm_params[p])]
        if compatible:
            chosen = compatible[0]
            var_mapping[uv] = chosen
            remaining_params.remove(chosen)

    if not var_mapping:
        return preconditions, effects

    def substitute_in_expr(expr: str) -> str:
        res = expr
        for old_v, new_v in var_mapping.items():
            # Replace variable with word boundary so ?p does not match ?p2
            res = re.sub(rf"\{old_v}\b", new_v, res)
        return res

    new_precs = [substitute_in_expr(p) for p in preconditions]
    new_effs = [substitute_in_expr(e) for e in effects]
    return new_precs, new_effs

def parse_pddl_domain_to_blueprint(pddl_str: str) -> Dict[str, Any]:
    """
    Parses a raw PDDL domain string into a structured Domain Blueprint dictionary.
    Extracts domain name, types hierarchy, predicates, and actions with parameters,
    preconditions, and effects.
    """
    if not pddl_str or not pddl_str.strip():
        return {}

    pddl_str = re.sub(r";[^\n]*", "", pddl_str)

    domain_name = re.search(r"\(\s*domain\s+([a-zA-Z0-9_\-]+)", pddl_str, re.IGNORECASE)
    dname = domain_name.group(1) if domain_name else "unnamed_domain"

    req_match = re.search(r"\(:requirements\s+(.*?)\)", pddl_str, re.IGNORECASE)
    reqs: List[str] = []
    if req_match:
        for r in req_match.group(1).split():
            clean_r = r.strip()
            if clean_r:
                if not clean_r.startswith(":"):
                    clean_r = f":{clean_r}"
                reqs.append(clean_r)

    types_match = re.search(r"\(:types\s+(.*?)\)", pddl_str, re.DOTALL | re.IGNORECASE)
    types_dict: Dict[str, str] = {}
    if types_match:
        tokens = types_match.group(1).split()
        current_types = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok == "-":
                parent = tokens[i+1] if i+1 < len(tokens) else "object"
                for t in current_types:
                    types_dict[t] = parent
                current_types = []
                i += 2
            else:
                current_types.append(tok)
                i += 1
        for t in current_types:
            types_dict[t] = "object"

    if not reqs:
        if types_dict or re.search(r"\?\w+\s*-\s*[a-zA-Z0-9_\-]+", pddl_str):
            reqs = [":strips", ":typing"]
        else:
            reqs = [":strips"]

    pred_match = re.search(r"\(:predicates\s+(.*?)\)\s*\(:", pddl_str, re.DOTALL | re.IGNORECASE)
    preds: List[str] = []
    if pred_match:
        preds = ["(" + p.strip() + ")" for p in re.findall(r"\((.*?)\)", pred_match.group(1)) if p.strip()]

    const_match = re.search(r"\(:constants\s+(.*?)\)\s*\(:", pddl_str, re.DOTALL | re.IGNORECASE)
    consts_dict: Dict[str, str] = {}
    if const_match:
        for line in const_match.group(1).split("\n"):
            line_clean = line.strip()
            if not line_clean or line_clean.startswith(";"):
                continue
            if "-" in line_clean:
                parts = line_clean.split("-")
                objs = parts[0].strip().split()
                parent = parts[1].strip()
                for o in objs:
                    consts_dict[o] = parent
            else:
                objs = line_clean.split()
                for o in objs:
                    consts_dict[o] = "object"

    actions: List[Dict[str, Any]] = []
    for act_match in re.finditer(r"\(:action\s+([a-zA-Z0-9_\-]+)(.*?)(?=\(:action|\)\s*$)", pddl_str, re.DOTALL | re.IGNORECASE):
        act_name = act_match.group(1)
        act_body = act_match.group(2)

        params_match = re.search(r":parameters\s*\((.*?)\)", act_body, re.DOTALL | re.IGNORECASE)
        param_dict: Dict[str, str] = {}
        if params_match:
            raw_p = params_match.group(1).strip()
            tokens = raw_p.split()
            current_vars: List[str] = []
            i = 0
            while i < len(tokens):
                tok = tokens[i]
                if tok == "-":
                    ptype = tokens[i+1] if i + 1 < len(tokens) else "object"
                    for v in current_vars:
                        param_dict[v] = ptype
                    current_vars = []
                    i += 2
                elif tok.startswith("?"):
                    current_vars.append(tok)
                    i += 1
                else:
                    i += 1
            for v in current_vars:
                param_dict[v] = "object"

        pre_match = re.search(r":precondition\s+(.*?)(?=:effect)", act_body, re.DOTALL | re.IGNORECASE)
        pre_list: List[str] = []
        if pre_match:
            pre_str = pre_match.group(1).strip()
            raw_pre = re.findall(r"\((?:not\s*\([^\(\)]+\)|[^\(\)]+)\)", pre_str)
            pre_list = [clean_blueprint_expression(p) for p in raw_pre if clean_blueprint_expression(p)]

        eff_match = re.search(r":effect\s+(.*?)(?=\)\s*$)", act_body, re.DOTALL | re.IGNORECASE)
        eff_list: List[str] = []
        if eff_match:
            eff_str = eff_match.group(1).strip()
            raw_eff = re.findall(r"\((?:not\s*\([^\(\)]+\)|[^\(\)]+)\)", eff_str)
            eff_list = [clean_blueprint_expression(p) for p in raw_eff if clean_blueprint_expression(p)]

        actions.append({
            "action_name": act_name,
            "parameters": param_dict,
            "preconditions": pre_list,
            "effects": eff_list
        })

    return {
        "domain_name": dname,
        "requirements": reqs,
        "types": types_dict,
        "constants": consts_dict,
        "predicates": preds,
        "actions": actions
    }

def extract_pddl_problem_metadata(pddl_str: str) -> Dict[str, Any]:
    """
    Extracts structured metadata (problem_name, domain_name, objects, initial_state, goal_state)
    from a fixed raw PDDL problem string (P_gold) using balanced S-expression depth parsing.
    """
    if not pddl_str or not pddl_str.strip():
        return {}

    pddl_str = re.sub(r";[^\n]*", "", pddl_str)

    prob_name = re.search(r"\(\s*problem\s+([a-zA-Z0-9_\-]+)", pddl_str, re.IGNORECASE)
    pname = prob_name.group(1) if prob_name else "unnamed_problem"

    dom_name = re.search(r"\(\s*:domain\s+([a-zA-Z0-9_\-]+)", pddl_str, re.IGNORECASE)
    dname = dom_name.group(1) if dom_name else "unnamed_domain"

    obj_match = re.search(r"\(:objects\s+(.*?)\)", pddl_str, re.DOTALL | re.IGNORECASE)
    objs_dict: Dict[str, str] = {}
    if obj_match:
        tokens = obj_match.group(1).split()
        pending = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.startswith(";"):
                i += 1
                continue
            if tok == "-":
                if i + 1 < len(tokens):
                    target_type = tokens[i + 1].lower()
                    for p in pending:
                        objs_dict[p] = target_type
                    pending = []
                    i += 2
                    continue
            else:
                pending.append(tok)
            i += 1
        for p in pending:
            objs_dict[p] = "object"

    # S-expression extraction for :init
    inits: List[str] = []
    init_match = re.search(r"\(:init\b", pddl_str, re.IGNORECASE)
    if init_match:
        start = init_match.start()
        depth = 0
        init_body = ""
        for i in range(start, len(pddl_str)):
            if pddl_str[i] == "(":
                depth += 1
            elif pddl_str[i] == ")":
                depth -= 1
                if depth == 0:
                    init_body = pddl_str[start:i+1]
                    break
        if not init_body:
            end_idx = goal_match.start() if goal_match else len(pddl_str)
            init_body = pddl_str[start:end_idx]
        inner_init = init_body[6:-1].strip() if init_body.startswith("(:init") and init_body.endswith(")") else init_body[6:].strip()
        pdepth = 0
        c_start = -1
        for idx, c in enumerate(inner_init):
            if c == "(":
                if pdepth == 0:
                    c_start = idx
                pdepth += 1
            elif c == ")":
                pdepth -= 1
                if pdepth == 0 and c_start != -1:
                    clause = inner_init[c_start:idx+1].strip()
                    if clause:
                        inits.append(clause)
                    c_start = -1

    # S-expression extraction for :goal
    goals: List[str] = []
    goal_match = re.search(r"\(:goal\b", pddl_str, re.IGNORECASE)
    if goal_match:
        start = goal_match.start()
        depth = 0
        goal_body = ""
        for i in range(start, len(pddl_str)):
            if pddl_str[i] == "(":
                depth += 1
            elif pddl_str[i] == ")":
                depth -= 1
                if depth == 0:
                    goal_body = pddl_str[start:i+1]
                    break
        if not goal_body:
            goal_body = pddl_str[start:]
        raw_goals = re.findall(r"\((?:not\s*\([^\(\)]+\)|[^\(\)]+)\)", goal_body)
        for g in raw_goals:
            clean_g = g.strip()
            if clean_g.lower() != "and":
                goals.append(clean_g)

    return {
        "problem_name": pname,
        "domain_name": dname,
        "objects": objs_dict,
        "initial_state": inits,
        "goal_state": goals
    }
