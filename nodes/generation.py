import re
from typing import Optional, Dict, Any, List
from schemas.pddl_blueprint import DomainBlueprint, PddlActionSchema
from tools.blueprint_parser import extract_pddl_problem_metadata


def normalize_pddl_expression(expr: str) -> str:
    """
    Normalizes whitespace in a PDDL expression to ensure valid syntax.
    
    Fixes common LLM output issues:
      - Missing space before '?' variables:  "(at?r" -> "(at ?r"
      - Missing space after type annotations: "robot?l" -> "robot ?l"
      - Collapsed 'not(' patterns:            "(not(" -> "(not ("
      - Multiple consecutive spaces collapsed to single space
    
    Examples:
      >>> normalize_pddl_expression("(at?r - robot?l - location)")
      '(at ?r - robot ?l - location)'
      >>> normalize_pddl_expression("(not(at?r?from))")
      '(not (at ?r ?from))'
    """
    s = expr.strip()
    # Strip redundant outer nested parentheses e.g. "((not ...))" -> "(not ...)"
    while s.startswith("((") and s.endswith("))"):
        inner = s[1:-1].strip()
        depth = 0
        balanced = True
        for idx, char in enumerate(inner):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0 and idx < len(inner) - 1:
                    balanced = False
                    break
        if depth == 0 and balanced:
            s = inner
        else:
            break

    # 1. Ensure space before any '?' that is preceded by a word character
    #    Handles: "(at?r" -> "(at ?r" and "robot?l" -> "robot ?l"
    s = re.sub(r'(?<=\w)\?', ' ?', s)
    # 2. Ensure space after '(' when followed by a word char but not already spaced
    #    Handles: "(not(" -> "(not (" — insert space between closing keywords and '('
    s = re.sub(r'(?<=\w)\(', ' (', s)
    # 3. Collapse multiple spaces into single space
    s = re.sub(r' {2,}', ' ', s)
    # 4. Strip accidental inline typing in atomic formulas:
    # e.g., "(at ?b - waypoint ?c - store)" -> "(at ?b ?c)" or "(at waypoint0 - soil-sample waypoint0)" -> "(at waypoint0 waypoint0)"
    # In classical PDDL 2.1, atomic formulas in preconditions, effects, and initial/goal states cannot contain inline typing
    s = re.sub(r'(\?[a-zA-Z0-9_\-]+|[a-zA-Z0-9_\-]+)\s+-\s+[a-zA-Z0-9_\-]+', r'\1', s)
    # 5. Collapse double negations "(not (not (P ...)))" -> "(P ...)"
    while re.match(r'^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$', s, flags=re.IGNORECASE):
        s = re.sub(r'^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$', r'\1', s, flags=re.IGNORECASE).strip()
    return s

def flatten_atoms_list(items) -> list:
    """Recursively flattens nested lists or tuples of PDDL atom strings."""
    if not items:
        return []
    flat = []
    for item in items:
        if isinstance(item, (list, tuple)):
            flat.extend(flatten_atoms_list(item))
        elif isinstance(item, str):
            item_str = item.strip()
            if item_str:
                flat.append(item_str)
        elif item is not None:
            flat.append(str(item).strip())
    return flat

def get_ancestors(t: str, parent_map: dict) -> list:
    """Traverses type hierarchy upwards to find all ancestor types."""
    ancestors = []
    curr = str(t).strip()
    while curr and curr in parent_map and parent_map[curr]:
        p = str(parent_map[curr]).strip()
        if p.lower() == "object" or p in ancestors:
            ancestors.append("object")
            break
        ancestors.append(p)
        curr = p
    if "object" not in ancestors:
        ancestors.append("object")
    return ancestors

def find_common_supertype(t1: str, t2: str, parent_map: dict) -> str:
    """Returns the most specific common supertype for two types."""
    if not t1 or not t2:
        return "object"
    t1_s, t2_s = str(t1).strip(), str(t2).strip()
    if t1_s.lower() == t2_s.lower():
        return t1_s
    anc1 = [t1_s] + get_ancestors(t1_s, parent_map)
    anc2 = [t2_s] + get_ancestors(t2_s, parent_map)
    if t2_s in anc1:
        return t2_s
    if t1_s in anc2:
        return t1_s
    for a in anc1:
        if a in anc2:
            return a
    return "object"

def parse_pddl_typed_params(param_tokens: list) -> list:
    """Parses token stream into [(var_name, type_name), ...]."""
    params = []
    current_vars = []
    i = 0
    while i < len(param_tokens):
        token = param_tokens[i]
        if token == "-":
            ptype = param_tokens[i+1] if i+1 < len(param_tokens) else "object"
            for v in current_vars:
                var_name = v if v.startswith("?") else f"?{v}"
                params.append((var_name, ptype))
            current_vars = []
            i += 2
        else:
            current_vars.append(token)
            i += 1
    for v in current_vars:
        var_name = v if v.startswith("?") else f"?{v}"
        params.append((var_name, "object"))
    return params

def deduplicate_and_unify_predicates(predicates: list, parent_map: dict, has_typing: bool) -> list:
    """
    Deduplicates and unifies predicate declarations sharing the same predicate symbol.
    If multiple declarations exist for the same predicate name with matching arity,
    their parameter types are unified to the common supertype in parent_map.
    This strictly prevents duplicate predicate definitions which violate Classical PDDL.
    """
    pred_map = {}
    for pred in predicates:
        clean = str(pred).strip()
        if not clean.startswith("("):
            clean = f"({clean}"
        if not clean.endswith(")"):
            clean = f"{clean})"
        inner = clean[1:-1].strip()
        tokens = inner.split()
        if not tokens:
            continue
        pname = tokens[0]
        params = parse_pddl_typed_params(tokens[1:])
        
        if pname not in pred_map:
            pred_map[pname] = params
        else:
            existing_params = pred_map[pname]
            if len(existing_params) == len(params):
                unified_params = []
                for (v1, t1), (v2, t2) in zip(existing_params, params):
                    sup = find_common_supertype(t1, t2, parent_map) if has_typing else "object"
                    unified_params.append((v2 if v2 else v1, sup))
                pred_map[pname] = unified_params

    out = []
    for pname, params in pred_map.items():
        if not params:
            out.append(f"({pname})")
        elif has_typing:
            p_str = " ".join([f"{v if v.startswith('?') else '?' + v} - {t}" for v, t in params])
            out.append(f"({pname} {p_str})")
        else:
            p_str = " ".join([v if v.startswith('?') else '?' + v for v, t in params])
            out.append(f"({pname} {p_str})")
    return out

def sanitize_action_effects(raw_effects: list) -> list:
    r"""
    Enforces classical STRIPS invariant: add(a) \cap del(a) = \emptyset.
    Under standard STRIPS add-after-delete semantics, if an action asserts both
    literal P and (not P), the add effect takes precedence, and the conflicting
    delete effect (not P) is pruned. This prevents planner/validator translation failures.
    """
    flat = flatten_atoms_list(raw_effects)
    pos_atoms = set()
    for eff in flat:
        norm = normalize_pddl_expression(eff)
        inner = norm.strip()
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()
        if not inner.lower().startswith("not"):
            clean_atom = re.sub(r'\s+', ' ', norm)
            pos_atoms.add(clean_atom)

    sanitized = []
    seen = set()
    for eff in flat:
        norm = normalize_pddl_expression(eff)
        inner = norm.strip()
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()
        if inner.lower().startswith("not"):
            neg_content = inner[3:].strip()
            if not neg_content.startswith("("):
                neg_content = f"({neg_content})"
            norm_pos = re.sub(r'\s+', ' ', normalize_pddl_expression(neg_content))
            if norm_pos in pos_atoms:
                # Contradictory effect detected: positive add takes precedence under add-after-delete
                continue
        clean_norm = re.sub(r'\s+', ' ', norm)
        if clean_norm not in seen:
            seen.add(clean_norm)
            sanitized.append(clean_norm)
    return sanitized

def synchronize_ast_predicate_symbols(blueprint_data: dict, problem_pddl: Optional[str] = None) -> dict:
    """
    Universally synchronizes predicate symbols across domain AST (declarations and actions)
    to match the canonical identifier format (hyphen vs underscore or prefix variation)
    present in the fixed problem instance (P_gold).
    Domain-agnostic and universally applicable to any PDDL 2.1 domain.
    """
    if not problem_pddl or not isinstance(blueprint_data, dict):
        return blueprint_data

    prob_meta = extract_pddl_problem_metadata(problem_pddl)
    prob_atoms = flatten_atoms_list(prob_meta.get("initial_state", [])) + flatten_atoms_list(prob_meta.get("goal_state", []))
    prob_pred_map: Dict[str, str] = {}
    prob_pred_arities: Dict[str, Set[int]] = {}
    for a in prob_atoms:
        clean = normalize_pddl_expression(a).strip("() ")
        if clean.lower().startswith("not"):
            clean = clean[3:].strip("() ")
        toks = clean.split()
        if toks:
            sym = toks[0]
            norm_key = sym.lower().replace("-", "_")
            prob_pred_map[norm_key] = sym
            prob_pred_arities.setdefault(norm_key, set()).add(len(toks) - 1)

    if not prob_pred_map:
        return blueprint_data

    # Collect all declared predicate symbols in blueprint
    declared_symbols = set()
    for p in blueprint_data.get("predicates", []):
        clean = normalize_pddl_expression(p).strip("() ")
        if clean:
            toks_p = clean.split()
            if toks_p:
                declared_symbols.add(toks_p[0].lower().replace("-", "_"))

    def _replace_sym(atom_str: str) -> str:
        s = str(atom_str).strip()
        is_neg = False
        inner = s
        if inner.startswith("(") and inner.endswith(")"):
            inner = inner[1:-1].strip()
        if inner.lower().startswith("not"):
            is_neg = True
            inner = inner[3:].strip()
            if inner.startswith("(") and inner.endswith(")"):
                inner = inner[1:-1].strip()
        toks = inner.split()
        if not toks:
            return atom_str
        psym = toks[0]
        norm_key = psym.lower().replace("-", "_")
        target_sym = None
        if norm_key in prob_pred_map:
            target_sym = prob_pred_map[norm_key]
        else:
            # 1. Common prefixes: is_, has_, can_ (only if target problem predicate is not already declared separately)
            for prefix in ["is_", "has_", "can_"]:
                cand_k = norm_key[len(prefix):]
                if norm_key.startswith(prefix) and cand_k in prob_pred_map and cand_k not in declared_symbols:
                    target_sym = prob_pred_map[cand_k]
                    break
            # 2. Compound affix alignment: object_at -> at, free_from -> free (only for unclaimed problem predicates)
            if not target_sym:
                sub_toks = [t for t in norm_key.split("_") if t]
                if len(sub_toks) > 1:
                    atom_arity = len(parse_pddl_typed_params(toks[1:])) if "-" in toks else (len(toks) - 1)
                    matching_cands = [
                        prob_pred_map[t] for t in sub_toks
                        if t in prob_pred_map and t not in declared_symbols and atom_arity in prob_pred_arities.get(t, set())
                    ]
                    if len(matching_cands) == 1:
                        target_sym = matching_cands[0]

            # 3. Morphological abbreviation / token prefix match under identical arity: power_available -> power_avail
            if not target_sym:
                atom_arity = len(parse_pddl_typed_params(toks[1:])) if "-" in toks else (len(toks) - 1)
                sub_toks = [t for t in norm_key.split("_") if t]
                for p_cand, arities in prob_pred_arities.items():
                    if p_cand not in declared_symbols and atom_arity in arities:
                        c_toks = [t for t in p_cand.split("_") if t]
                        if len(sub_toks) == len(c_toks) and len(sub_toks) > 0:
                            if all(t1 == t2 or t1.startswith(t2) or t2.startswith(t1) for t1, t2 in zip(sub_toks, c_toks)):
                                target_sym = prob_pred_map[p_cand]
                                break

            # 4. Separator-free concatenation match under identical arity: on_table -> ontable
            if not target_sym:
                atom_arity = len(parse_pddl_typed_params(toks[1:])) if "-" in toks else (len(toks) - 1)
                norm_no_sep = norm_key.replace("_", "")
                for p_cand, arities in prob_pred_arities.items():
                    if p_cand not in declared_symbols and atom_arity in arities and norm_no_sep == p_cand.replace("_", ""):
                        target_sym = prob_pred_map[p_cand]
                        break

            # 5. Core root token affix alignment under identical arity: visible -> visible_from
            if not target_sym and len(norm_key) > 3:
                atom_arity = len(parse_pddl_typed_params(toks[1:])) if "-" in toks else (len(toks) - 1)
                affix_cands = []
                for p_cand, arities in prob_pred_arities.items():
                    if atom_arity in arities:
                        c_toks = [t for t in p_cand.split("_") if t]
                        if norm_key in c_toks or p_cand in [t for t in norm_key.split("_") if t]:
                            affix_cands.append(prob_pred_map[p_cand])
                if len(affix_cands) == 1:
                    target_sym = affix_cands[0]

        if target_sym:
            target_norm = target_sym.lower().replace("-", "_")
            if target_norm != norm_key and target_norm in declared_symbols:
                return atom_str
            if target_sym != psym:
                toks[0] = target_sym
                res = f"({' '.join(toks)})"
                return f"(not {res})" if is_neg else res
        return atom_str

    # Sync domain.predicates
    new_preds = []
    for p in blueprint_data.get("predicates", []):
        new_preds.append(_replace_sym(p))
    blueprint_data["predicates"] = new_preds

    # Sync actions preconditions and effects
    for act in blueprint_data.get("actions", []):
        if isinstance(act, dict):
            act["preconditions"] = [_replace_sym(p) for p in act.get("preconditions", [])]
            act["effects"] = [_replace_sym(e) for e in act.get("effects", [])]

    return blueprint_data

def compile_pddl_programmatically(blueprint_data: dict, problem_pddl: Optional[str] = None) -> str:
    """
    Deterministic conversion of a DomainBlueprint JSON dictionary
    into perfectly indented, parenthetically closed Lisp PDDL code strings.
    """
    if problem_pddl:
        synchronize_ast_predicate_symbols(blueprint_data, problem_pddl)
    prob_meta = extract_pddl_problem_metadata(problem_pddl) if (problem_pddl and isinstance(problem_pddl, str)) else {}
    raw_dname = prob_meta.get("domain_name") or blueprint_data.get("domain_name", "generated_domain")
    domain_name = re.sub(r'\.pddl$', '', str(raw_dname), flags=re.IGNORECASE)
    domain_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', domain_name)
    if not domain_name:
        domain_name = "generated_domain"
    requirements = blueprint_data.get("requirements", [":strips", ":typing"])
    types = blueprint_data.get("types", {})
    predicates = blueprint_data.get("predicates", [])
    actions = blueprint_data.get("actions", [])
    
    pddl_lines = []
    
    # 1. Header & Requirements
    pddl_lines.append(f"(define (domain {domain_name})")
    req_str = " ".join(requirements) if isinstance(requirements, list) else ":strips :typing"
    has_typing = ":typing" in req_str
    has_negative_preconditions = ":negative-preconditions" in req_str
    pddl_lines.append(f"  (:requirements {req_str})")
    pddl_lines.append("")
    
    # 2. Types Hierarchy Block
    def _sanitize_type_token(t_val: Any) -> Optional[str]:
        if not t_val:
            return None
        s = str(t_val).strip()
        if not s or s.lower() in ("none", "null"):
            return None
        # PDDL 2.1 lexical rule: '/' is illegal in PDDL identifiers; sanitize to '_'
        s = re.sub(r"[^a-zA-Z0-9_\-]", "_", s).strip("_")
        return s if s else None

    normalized_types = {}
    if isinstance(types, dict):
        for child, parent in types.items():
            c_clean = _sanitize_type_token(child)
            p_clean = _sanitize_type_token(parent)
            if c_clean and c_clean.lower() != "object":
                normalized_types[c_clean] = p_clean if p_clean and p_clean.lower() != c_clean.lower() else None
    elif isinstance(types, list):
        for item in types:
            if "-" in str(item):
                parts = str(item).split("-")
                children = parts[0].strip().split()
                parent = _sanitize_type_token(parts[1].strip())
                for c in children:
                    c_clean = _sanitize_type_token(c)
                    if c_clean and c_clean.lower() != "object":
                        normalized_types[c_clean] = parent if parent and parent.lower() != c_clean.lower() else None
            else:
                for c in str(item).strip().split():
                    c_clean = _sanitize_type_token(c)
                    if c_clean and c_clean.lower() != "object":
                        normalized_types[c_clean] = None

    def _resolve_type_expr(raw_t: Any) -> str:
        if not raw_t:
            return "object"
        s = str(raw_t).strip()
        if "/" in s or "|" in s:
            parts = [ _sanitize_type_token(p) for p in re.split(r"[/|]", s) if _sanitize_type_token(p) ]
            if len(parts) >= 2:
                # If a synthesized supertype 'a_b' was declared in normalized_types, use it; otherwise find common supertype
                joined = "_".join(parts)
                if joined in normalized_types:
                    for p in parts:
                        if p not in normalized_types or not normalized_types[p]:
                            normalized_types[p] = joined
                    return joined
                sup = parts[0]
                for nxt in parts[1:]:
                    sup = find_common_supertype(sup, nxt, normalized_types)
                return sup
        clean_t = _sanitize_type_token(s)
        return clean_t if clean_t else "object"

    # Sanitize any slash-types inside predicates and action parameters
    predicates = [
        re.sub(
            r"(\?\w+\s*-\s*)([a-zA-Z0-9_\-/|]+)",
            lambda m: m.group(1) + _resolve_type_expr(m.group(2)),
            str(p)
        )
        for p in predicates
    ]
    for act in actions:
        if isinstance(act, dict) and isinstance(act.get("parameters"), dict):
            act["parameters"] = {k: _resolve_type_expr(v) for k, v in act["parameters"].items()}
        elif hasattr(act, "parameters") and isinstance(getattr(act, "parameters"), dict):
            setattr(act, "parameters", {k: _resolve_type_expr(v) for k, v in getattr(act, "parameters").items()})

    raw_constants = getattr(blueprint_data, "constants", {}) if hasattr(blueprint_data, "constants") else blueprint_data.get("constants", {})
    if not isinstance(raw_constants, dict):
        raw_constants = {}
    else:
        raw_constants = dict(raw_constants)

    # Auto-discover types from predicates and action parameters (only when :typing is active)
    if has_typing:
        discovered_types = set()
        for pred in predicates:
            matches = re.findall(r"\?\w+\s*-\s*([a-zA-Z0-9_\-]+)", str(pred))
            for t in matches:
                if t.lower() != "object":
                    discovered_types.add(t)

        for act in actions:
            if isinstance(act, dict):
                params = act.get("parameters", {})
            else:
                params = getattr(act, "parameters", {})
            if isinstance(params, dict):
                for pvar, ptype in params.items():
                    if ptype and str(ptype).lower() != "object":
                        discovered_types.add(str(ptype))

        # Auto-discover types from fixed problem instance (:objects ...)
        # (Classical PDDL 2.1: every type used to declare objects in problem :objects must exist in domain :types)
        if prob_meta and isinstance(prob_meta, dict):
            for obj_name, obj_type in prob_meta.get("objects", {}).items():
                if obj_type and str(obj_type).lower() != "object":
                    discovered_types.add(str(obj_type))

        # Auto-discover object constants appearing in action preconditions and effects
        # (Classical PDDL 2.1: any non-variable literal argument in action schemas is an object constant,
        #  typed according to the declared predicate parameter signature at that argument position)
        raw_constants = getattr(blueprint_data, "constants", {}) if hasattr(blueprint_data, "constants") else blueprint_data.get("constants", {})
        if not isinstance(raw_constants, dict):
            raw_constants = {}
        else:
            raw_constants = dict(raw_constants)

        pred_param_types: dict = {}
        for pred in predicates:
            clean_p = str(pred).strip("() ")
            if not clean_p:
                continue
            ptoks = clean_p.split()
            psym = ptoks[0].lower()
            parsed_params = parse_pddl_typed_params(ptoks[1:])
            pred_param_types[psym] = [ptype for _, ptype in parsed_params]

        for act in actions:
            if isinstance(act, dict):
                act_params = act.get("parameters", {})
                act_precs = act.get("preconditions", [])
                act_effs = act.get("effects", [])
            else:
                act_params = getattr(act, "parameters", {})
                act_precs = getattr(act, "preconditions", [])
                act_effs = getattr(act, "effects", [])
            VALID_IDENTIFIER = re.compile(r'^[a-zA-Z][a-zA-Z0-9_\-]*$')
            PDDL_KEYWORDS = {"not", "and", "or", "imply", "exists", "forall", "object", "-", "="}
            norm_param_names = {k if k.startswith("?") else "?" + k for k in act_params.keys()}
            bare_param_names = {k.lstrip("?") for k in act_params.keys()}
            all_atoms = flatten_atoms_list(act_precs) + flatten_atoms_list(act_effs)
            for atom in all_atoms:
                norm_atom = normalize_pddl_expression(atom)
                clean = norm_atom.strip('() ')
                if clean.lower().startswith("not"):
                    clean = clean[3:].strip('() ')
                parts = clean.split()
                if len(parts) > 1:
                    psym = parts[0].lower()
                    expected_types = pred_param_types.get(psym, [])
                    for arg_idx, arg in enumerate(parts[1:]):
                        if (
                            not arg.startswith("?")
                            and not arg.replace('.', '', 1).isdigit()
                            and VALID_IDENTIFIER.match(arg)
                            and arg.lower() not in PDDL_KEYWORDS
                            and arg not in bare_param_names
                        ):
                            inferred_t = expected_types[arg_idx] if arg_idx < len(expected_types) else "object"
                            if inferred_t.lower() == arg.lower():
                                inferred_t = normalized_types.get(arg) or "object"
                            if arg not in raw_constants or (raw_constants[arg] == "object" and inferred_t != "object"):
                                raw_constants[arg] = inferred_t

        # Universal PDDL 2.1 Herbrand Universe Scoping Invariant:
        # 1) Domain (:constants ...) and Problem (:objects ...) share the global object namespace and MUST be disjoint.
        #    Any symbol already declared in problem (:objects ...) MUST NOT appear in domain (:constants ...).
        # 2) Any symbol appearing in problem (:init ...) or (:goal ...) that is NOT declared in problem (:objects ...)
        #    is formally a domain constant and must be declared in (:constants ...) with its predicate argument type.
        if prob_meta and isinstance(prob_meta, dict):
            VALID_IDENTIFIER = re.compile(r'^[a-zA-Z][a-zA-Z0-9_\-]*$')
            PDDL_KEYWORDS = {"not", "and", "or", "imply", "exists", "forall", "object", "-", "="}
            prob_objs = prob_meta.get("objects", {})
            if not isinstance(prob_objs, dict):
                prob_objs = {}
            prob_obj_lower = {str(k).strip().lower() for k in prob_objs.keys()}
            for cname in list(raw_constants.keys()):
                if str(cname).strip().lower() in prob_obj_lower:
                    raw_constants.pop(cname, None)

            # If any problem instance object was accidentally hardcoded inside an action schema
            # (which causes VAL syntax crash 'Object with unknown type: ...' because problem objects cannot be domain constants),
            # parameterize it cleanly as an action parameter variable.
            prob_obj_map = {str(k).strip().lower(): (str(k).strip(), str(v).strip()) for k, v in prob_objs.items()}
            for act in actions:
                act_params = act.get("parameters", {}) if isinstance(act, dict) else getattr(act, "parameters", {})
                if not isinstance(act_params, dict):
                    continue
                act_precs = act.get("preconditions", []) if isinstance(act, dict) else getattr(act, "preconditions", [])
                act_effs = act.get("effects", []) if isinstance(act, dict) else getattr(act, "effects", [])
                for atom_list in [act_precs, act_effs]:
                    for idx, atom in enumerate(atom_list):
                        norm_atom = normalize_pddl_expression(atom)
                        clean = norm_atom.strip('() ')
                        is_neg = clean.lower().startswith("not")
                        if is_neg:
                            clean = clean[3:].strip('() ')
                        parts = clean.split()
                        if len(parts) > 1:
                            new_parts = [parts[0]]
                            changed = False
                            for arg in parts[1:]:
                                arg_low = arg.lower()
                                if not arg.startswith("?") and arg_low in prob_obj_map:
                                    orig_k, orig_t = prob_obj_map[arg_low]
                                    var_name = f"?{orig_k}"
                                    new_parts.append(var_name)
                                    changed = True
                                    if var_name not in act_params and orig_k not in act_params:
                                        act_params[var_name] = orig_t
                                else:
                                    new_parts.append(arg)
                            if changed:
                                new_atom_str = f"({' '.join(new_parts)})"
                                if is_neg:
                                    new_atom_str = f"(not {new_atom_str})"
                                atom_list[idx] = new_atom_str
            prob_atoms = (
                flatten_atoms_list(prob_meta.get("initial_state", []))
                + flatten_atoms_list(prob_meta.get("goal_state", []))
            )
            for atom in prob_atoms:
                norm_atom = normalize_pddl_expression(atom)
                clean = norm_atom.strip('() ')
                if clean.lower().startswith("not"):
                    clean = clean[3:].strip('() ')
                parts = clean.split()
                if len(parts) > 1:
                    psym = parts[0].lower()
                    expected_types = pred_param_types.get(psym, [])
                    for arg_idx, arg in enumerate(parts[1:]):
                        if (
                            not arg.startswith("?")
                            and not arg.replace('.', '', 1).isdigit()
                            and VALID_IDENTIFIER.match(arg)
                            and arg.lower() not in PDDL_KEYWORDS
                            and arg.lower() not in prob_obj_lower
                            and arg not in normalized_types
                        ):
                            inferred_t = expected_types[arg_idx] if arg_idx < len(expected_types) else "object"
                            if inferred_t.lower() == arg.lower():
                                inferred_t = normalized_types.get(arg) or "object"
                            if arg not in raw_constants or (raw_constants[arg] == "object" and inferred_t != "object"):
                                raw_constants[arg] = inferred_t

        if isinstance(blueprint_data, dict):
            blueprint_data["constants"] = raw_constants
        elif hasattr(blueprint_data, "constants"):
            setattr(blueprint_data, "constants", raw_constants)

        # Auto-discover types from constants
        if raw_constants and isinstance(raw_constants, dict):
            for cname, ctype in raw_constants.items():
                if ctype and str(ctype).lower() != "object":
                    discovered_types.add(str(ctype))

        for dt in discovered_types:
            if dt not in normalized_types and dt.lower() != "object":
                normalized_types[dt] = None

        # Universal PDDL 2.1 Typing AST Invariant:
        # Any type referenced as a supertype that is not itself declared as a child of another type
        # must be declared as a subtype of the universal root 'object'.
        all_referenced_parents = {p for p in list(normalized_types.values()) if p and str(p).lower() not in {"object", "none"}}
        for p in all_referenced_parents:
            if p not in normalized_types:
                normalized_types[p] = "object"

    # 2b. Constants Block Determination (Classical PDDL 2.1 Domain Constants)
    valid_constants = {}
    if raw_constants and isinstance(raw_constants, dict):
        VALID_IDENTIFIER = re.compile(r'^[a-zA-Z][a-zA-Z0-9_\-]*$')
        PDDL_KEYWORDS = {"not", "and", "or", "imply", "exists", "forall", "object", "-", "="}
        for cname, ctype in raw_constants.items():
            cname_str = str(cname).strip()
            if (
                VALID_IDENTIFIER.match(cname_str)
                and cname_str.lower() not in PDDL_KEYWORDS
            ):
                valid_constants[cname_str] = ctype if ctype else "object"

    # In Classical PDDL 2.1 (:typing), every constant must have a valid declared type.
    # If a constant's declared type is not 'object', ensure its type is declared in normalized_types.
    for cname, ctype in valid_constants.items():
        if ctype and str(ctype).lower() != "object" and str(ctype) not in normalized_types:
            normalized_types[str(ctype)] = "object"

    # Only purge a constant symbol from types if it is NOT itself used as a type by any entity.
    used_type_names = {str(ctype) for ctype in valid_constants.values() if ctype} | {str(p) for p in normalized_types.values() if p}
    for cname in list(valid_constants.keys()):
        if cname not in used_type_names:
            normalized_types.pop(cname, None)

    # Filter out root 'object' from (:types ...)
    filtered_types = {c: p for c, p in normalized_types.items() if c and c.lower() != "object"}

    if filtered_types and has_typing:
        pddl_lines.append("  (:types")
        supertype_map = {}
        for child, parent in filtered_types.items():
            parent_key = parent if (parent and parent.lower() != "none" and parent.lower() != child.lower()) else "object"
            supertype_map.setdefault(parent_key, []).append(child)

        for parent, children in supertype_map.items():
            children_str = " ".join(sorted(set(children)))
            if parent == "object":
                pddl_lines.append(f"    {children_str} - object")
            else:
                pddl_lines.append(f"    {children_str} - {parent}")
        pddl_lines.append("  )")
        pddl_lines.append("")

    if valid_constants:
        pddl_lines.append("  (:constants")
        const_supertype_map = {}
        for cname, ctype in valid_constants.items():
            ckey = str(ctype) if ctype else "object"
            const_supertype_map.setdefault(ckey, []).append(str(cname))
        for ctype, clist in const_supertype_map.items():
            cstr = " ".join(sorted(clist))
            if ctype == "object":
                pddl_lines.append(f"    {cstr} - object")
            else:
                pddl_lines.append(f"    {cstr} - {ctype}")
        pddl_lines.append("  )")
        pddl_lines.append("")

        
    # 3. Predicates Block & Auto-Discovery
    # Build initial pred_map from declared predicates
    PDDL_RESERVED_PRED_NAMES = {"not", "and", "or", "imply", "exists", "forall", "object", "-", "="}
    pred_map = {}
    for pred in predicates:
        clean = str(pred).strip()
        if not clean.startswith("("):
            clean = f"({clean}"
        if not clean.endswith(")"):
            clean = f"{clean})"
        inner = clean[1:-1].strip()
        tokens = inner.split()
        if not tokens:
            continue
        pname = tokens[0]
        if pname.lower() in PDDL_RESERVED_PRED_NAMES:
            continue
        params = parse_pddl_typed_params(tokens[1:])
        if pname not in pred_map:
            pred_map[pname] = params
        else:
            existing_params = pred_map[pname]
            if len(existing_params) == len(params):
                unified_params = []
                for (v1, t1), (v2, t2) in zip(existing_params, params):
                    sup = find_common_supertype(t1, t2, normalized_types) if has_typing else "object"
                    unified_params.append((v2 if v2 else v1, sup))
                pred_map[pname] = unified_params

    # Auto-discover predicates and unify parameter signatures across action schemas
    for act in actions:
        if isinstance(act, dict):
            act_params = act.get("parameters", {})
            act_precs = act.get("preconditions", [])
            act_effs = act.get("effects", [])
        else:
            act_params = getattr(act, "parameters", {})
            act_precs = getattr(act, "preconditions", [])
            act_effs = getattr(act, "effects", [])
        norm_params = {k if k.startswith("?") else "?" + k: v for k, v in act_params.items()}

        all_atoms = flatten_atoms_list(act_precs) + flatten_atoms_list(act_effs)
        for atom in all_atoms:
            clean = atom.strip('() ')
            while clean.lower().startswith("not"):
                clean = clean[3:].strip('() ')
            tokens = clean.split()
            if not tokens:
                continue
            pname = tokens[0]
            if pname.lower() in PDDL_RESERVED_PRED_NAMES:
                continue
            args = tokens[1:]

            inferred_types = []
            for arg in args:
                if arg in norm_params:
                    inferred_types.append(norm_params[arg])
                elif raw_constants and arg in raw_constants:
                    inferred_types.append(raw_constants[arg])
                else:
                    inferred_types.append("object")

            matching_key = next((k for k in pred_map.keys() if k.lower() == pname.lower()), None)
            if not matching_key:
                param_tuples = [
                    (f"?x{i+1}" if not arg.startswith("?") else arg, inferred_types[i])
                    for i, arg in enumerate(args)
                ]
                pred_map[pname] = param_tuples
            else:
                existing_params = pred_map[matching_key]
                if len(existing_params) == len(inferred_types):
                    unified_params = []
                    for (v1, t1), t2 in zip(existing_params, inferred_types):
                        sup = find_common_supertype(t1, t2, normalized_types) if has_typing else "object"
                        unified_params.append((v1, sup))
                    pred_map[matching_key] = unified_params

    # Unify pred_map with ground atoms in fixed problem PDDL (:init and :goal)
    if prob_meta and isinstance(prob_meta, dict):
        prob_objs = prob_meta.get("objects", {})
        if not isinstance(prob_objs, dict):
            prob_objs = {}
        all_known_obj_types = {str(k).lower(): str(v) for k, v in {**(raw_constants or {}), **prob_objs}.items() if v}
        prob_atoms = (
            flatten_atoms_list(prob_meta.get("initial_state", []))
            + flatten_atoms_list(prob_meta.get("goal_state", []))
        )
        for atom in prob_atoms:
            clean = atom.strip('() ')
            while clean.lower().startswith("not"):
                clean = clean[3:].strip('() ')
            tokens = clean.split()
            if not tokens:
                continue
            pname = tokens[0]
            if pname.lower() in PDDL_RESERVED_PRED_NAMES:
                continue
            args = tokens[1:]
            inferred_types = [all_known_obj_types.get(arg.lower(), "object") for arg in args]
            matching_key = next((k for k in pred_map.keys() if k.lower() == pname.lower()), None)
            if not matching_key:
                pred_map[pname] = [(f"?x{i+1}", inferred_types[i]) for i in range(len(args))]
            else:
                existing_params = pred_map[matching_key]
                if len(existing_params) == len(inferred_types):
                    pred_map[matching_key] = [
                        (v1, find_common_supertype(t1, t2, normalized_types) if has_typing else "object")
                        for (v1, t1), t2 in zip(existing_params, inferred_types)
                    ]
                else:
                    # Immutable Problem Contract Invariant: Problem :init/:goal arity is fixed ground truth.
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
                p_str = " ".join([v if v.startswith('?') else '?' + v for v, t in params])
                pddl_lines.append(f"    ({pname} {p_str})")
        pddl_lines.append("  )")
        pddl_lines.append("")

    # 4. Action Schemas Compilation
    for act in actions:
        if isinstance(act, dict):
            act_obj = PddlActionSchema(**act)
        else:
            act_obj = act

        flat_preconds = flatten_atoms_list(act_obj.preconditions)
        flat_effects = sanitize_action_effects(act_obj.effects)

        # In Classical PDDL 2.1, predicates cannot be signature-overloaded with multiple arities.
        # Prune precondition and effect atoms whose argument count contradicts the declared predicate signature in pred_map.
        sanitized_preconds = []
        for prec in flat_preconds:
            clean_p = prec.strip('() ')
            is_neg = clean_p.lower().startswith("not")
            if is_neg and not has_negative_preconditions:
                continue
            if is_neg:
                clean_p = clean_p[3:].strip('() ')
            pparts = clean_p.split()
            if pparts:
                ppname = pparts[0]
                matching_k = next((k for k in pred_map.keys() if k.lower() == ppname.lower()), None)
                if matching_k and len(pparts[1:]) != len(pred_map[matching_k]):
                    continue
            sanitized_preconds.append(prec)
        flat_preconds = sanitized_preconds
        sanitized_effects = []
        norm_act_params = {k if k.startswith("?") else "?" + k: str(v).lower() for k, v in act_obj.parameters.items() if v}
        for eff in flat_effects:
            clean_eff = eff.strip('() ')
            is_neg_eff = clean_eff.lower().startswith("not")
            if is_neg_eff:
                clean_eff = clean_eff[3:].strip('() ')
            eparts = clean_eff.split()
            if eparts:
                epname = eparts[0]
                matching_k = next((k for k in pred_map.keys() if k.lower() == epname.lower()), None)
                if matching_k and len(eparts[1:]) != len(pred_map[matching_k]):
                    target_params = pred_map[matching_k]
                    if len(eparts[1:]) < len(target_params):
                        rebuilt_args = []
                        used_e_args = set()
                        for _, req_t in target_params:
                            req_tl = str(req_t).lower()
                            matched_arg = next(
                                (a for a in eparts[1:] if a not in used_e_args and norm_act_params.get(a, "") == req_tl),
                                None
                            )
                            if not matched_arg:
                                cands = [k for k, vt in norm_act_params.items() if k not in used_e_args and vt == req_tl]
                                if len(cands) == 1:
                                    matched_arg = cands[0]
                            if matched_arg:
                                rebuilt_args.append(matched_arg)
                                used_e_args.add(matched_arg)
                        if len(rebuilt_args) == len(target_params):
                            new_core = f"({epname} {' '.join(rebuilt_args)})"
                            eff = f"(not {new_core})" if is_neg_eff else new_core
                        else:
                            continue
                    else:
                        continue
            sanitized_effects.append(eff)
        flat_effects = sanitized_effects

        # Resolve contradictory simultaneous action effects ((P ...) and (not (P ...)))
        # under Classical STRIPS state-transition semantics (Fox & Long 2003):
        pos_atoms_set = set()
        neg_atoms_set = set()
        for e in flat_effects:
            clean = e.strip('() ')
            if clean.lower().startswith("not"):
                neg_atoms_set.add(normalize_pddl_expression(clean[3:].strip('() ')))
            else:
                pos_atoms_set.add(normalize_pddl_expression(clean))
        
        contradictions = pos_atoms_set.intersection(neg_atoms_set)
        if contradictions:
            norm_preconds = {normalize_pddl_expression(p.strip('() ')) for p in flat_preconds if not p.strip('() ').lower().startswith("not")}
            resolved_effects = []
            for e in flat_effects:
                clean = e.strip('() ')
                is_neg = clean.lower().startswith("not")
                core = normalize_pddl_expression(clean[3:].strip('() ') if is_neg else clean)
                if core in contradictions:
                    in_pre = core in norm_preconds
                    # If in preconditions, action consumes it: keep negative effect (not core), discard positive effect core
                    if in_pre and not is_neg:
                        continue
                    # If NOT in preconditions, action establishes it: keep positive effect core, discard negative effect (not core)
                    if not in_pre and is_neg:
                        continue
                resolved_effects.append(e)
            flat_effects = resolved_effects

        # In Classical PDDL 2.1, free/unbound variables in action schemas violate AST well-formedness.
        # Ensure all variables in preconditions and effects are declared in parameters.
        all_atoms = flat_preconds + flat_effects
        used_vars = set(re.findall(r'\?[a-zA-Z0-9_\-]+', " ".join(all_atoms)))
        existing_params_norm = {k if k.startswith("?") else "?" + k: v for k, v in act_obj.parameters.items()}
        missing_vars = used_vars - set(existing_params_norm.keys())
        if missing_vars:
            for mv in sorted(missing_vars):
                inferred_type = "object"
                for atom in all_atoms:
                    clean = atom.strip('() ')
                    if clean.lower().startswith("not"):
                        clean = clean[3:].strip('() ')
                    parts = clean.split()
                    if parts and mv in parts[1:]:
                        idx = parts[1:].index(mv)
                        p_sym = parts[0]
                        if p_sym in pred_map:
                            sig_params = pred_map[p_sym]
                            if idx < len(sig_params):
                                inferred_type = sig_params[idx][1]
                                break
                existing_params_norm[mv] = inferred_type
            act_obj.parameters = existing_params_norm

        pddl_lines.append(f"  (:action {act_obj.action_name}")

        # Format Parameters: Ensure every variable starts with '?'
        if has_typing:
            param_parts = [
                f"{var if var.startswith('?') else '?' + var} - {type_name if type_name else 'object'}"
                for var, type_name in act_obj.parameters.items()
            ]
        else:
            param_parts = [
                f"{var if var.startswith('?') else '?' + var}"
                for var in act_obj.parameters.keys()
            ]
        param_str = " ".join(param_parts)
        pddl_lines.append(f"    :parameters ({param_str})")

        # Format Preconditions
        if len(flat_preconds) == 1:
            pre_str = normalize_pddl_expression(flat_preconds[0])
            pddl_lines.append(f"    :precondition {pre_str}")
        elif len(flat_preconds) > 1:
            pres = " ".join([normalize_pddl_expression(p) for p in flat_preconds])
            pddl_lines.append(f"    :precondition (and {pres})")
        else:
            pddl_lines.append("    :precondition (and)")

        # Format Effects
        if len(flat_effects) == 1:
            eff_str = normalize_pddl_expression(flat_effects[0])
            pddl_lines.append(f"    :effect {eff_str}")
        elif len(flat_effects) > 1:
            effs = " ".join([normalize_pddl_expression(e) for e in flat_effects])
            pddl_lines.append(f"    :effect (and {effs})")
        else:
            pddl_lines.append("    :effect (and)")

        pddl_lines.append("  )")
        pddl_lines.append("")
        
    pddl_lines.append(")")
    return "\n".join(pddl_lines)

def run_generation_node(state: dict) -> dict:
    """
    Phase 2.2 Node: Programmatically compiles the DomainBlueprint JSON
    into valid Lisp PDDL code without calling an LLM, holding the fixed
    ground-truth problem PDDL (P_gold) read-only.
    """
    import time
    start_t = time.time()
    blueprint_data = state.get("pddl_domain_blueprint", {})
    if hasattr(blueprint_data, "model_dump"): 
        blueprint_data = blueprint_data.model_dump()
    elif hasattr(blueprint_data, "dict"):
        blueprint_data = blueprint_data.dict()

    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    if problem_pddl:
        prob_meta = extract_pddl_problem_metadata(problem_pddl)
        if prob_meta.get("domain_name") and isinstance(blueprint_data, dict):
            blueprint_data["domain_name"] = prob_meta["domain_name"]
            state["pddl_domain_blueprint"] = blueprint_data
        state["generated_problem_pddl"] = problem_pddl
        if "initial_problem_pddl" not in state or not state["initial_problem_pddl"]:
            state["initial_problem_pddl"] = problem_pddl

    # Compile Domain against fixed P_gold
    compiled_pddl = compile_pddl_programmatically(blueprint_data, problem_pddl=problem_pddl)
    state["generated_domain_pddl"] = compiled_pddl
    if "initial_domain_pddl" not in state or not state["initial_domain_pddl"]:
        state["initial_domain_pddl"] = compiled_pddl
    if "initial_pddl_domain_blueprint" not in state or not state["initial_pddl_domain_blueprint"]:
        state["initial_pddl_domain_blueprint"] = blueprint_data

    latencies = state.get("node_latencies", {})
    latencies["generate"] = round(latencies.get("generate", 0.0) + (time.time() - start_t), 3)
    state["node_latencies"] = latencies
    return state
