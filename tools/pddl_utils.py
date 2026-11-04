import re
from typing import List, Tuple, Dict, Any, Optional


def normalize_pddl_expression(expr: str) -> str:
    """
    Normalizes whitespace and formatting in a PDDL expression.
    - Strips redundant outer nested parentheses
    - Ensures space before '?' variables: '(at?r' -> '(at ?r'
    - Ensures space after '(' when followed by word chars
    - Collapses multiple whitespace to single space
    - Strips illegal inline typing in atomic formulas: '(at ?x - loc ?y)' -> '(at ?x ?y)'
    - Collapses double negations: '(not (not (P ...)))' -> '(P ...)'
    """
    s = str(expr).strip()
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

    s = re.sub(r'(?<=\w)\?', ' ?', s)
    s = re.sub(r'(?<=\w)\(', ' (', s)
    s = re.sub(r' {2,}', ' ', s)
    s = re.sub(r'(\?[a-zA-Z0-9_\-]+|[a-zA-Z0-9_\-]+)\s+-\s+[a-zA-Z0-9_\-]+', r'\1', s)
    while re.match(r'^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$', s, flags=re.IGNORECASE):
        s = re.sub(r'^\(\s*not\s*\(\s*not\s*(\(.+\))\s*\)\s*\)$', r'\1', s, flags=re.IGNORECASE).strip()
    return s


def normalize_atom(atom_str: str) -> Tuple[str, bool]:
    """
    Normalizes a PDDL atom and returns (positive_atom_str, is_positive).
    Example: '(not (at ?x ?y))' -> ('(at ?x ?y)', False)
             '(on ?a ?b)' -> ('(on ?a ?b)', True)
    """
    s = normalize_pddl_expression(atom_str).strip()
    if not s.startswith("("):
        s = f"({s}"
    if not s.endswith(")"):
        s = f"{s})"

    inner = s[1:-1].strip()
    if inner.lower().startswith("not"):
        neg_content = inner[3:].strip()
        if not neg_content.startswith("("):
            neg_content = f"({neg_content})"
        norm_inner = normalize_pddl_expression(neg_content)
        return norm_inner, False
    return s, True


def norm_token(s: Any) -> str:
    """
    Normalizes an identifier or AST path for invariant comparison.
    Strips AST prefix qualifiers ('domain.actions.', etc.), hyphens, underscores, and lowercase.
    """
    clean = re.sub(r"^(domain\.)?(actions?|predicates?|types?|constants?)\.", "", str(s).strip("'\"` "), flags=re.IGNORECASE)
    return clean.lower().replace("-", "").replace("_", "")


def flatten_atoms(items: Any) -> List[str]:
    """Recursively flattens nested lists or tuples of PDDL atom strings."""
    if not items:
        return []
    flat = []
    for item in items:
        if isinstance(item, (list, tuple)):
            flat.extend(flatten_atoms(item))
        elif isinstance(item, str):
            item_str = item.strip()
            if item_str:
                flat.append(item_str)
        elif item is not None:
            flat.append(str(item).strip())
    return flat


def get_type_ancestors(t: str, parent_map: Dict[str, Any]) -> List[str]:
    """Traverses type hierarchy upwards to find all ancestor types ending at 'object'."""
    ancestors = []
    curr = str(t).strip()
    norm_parent_map = {str(k).strip().lower(): str(v).strip().lower() for k, v in parent_map.items() if v}
    while curr:
        curr_lower = curr.lower()
        if curr_lower in norm_parent_map:
            p = norm_parent_map[curr_lower]
            if p == "object" or p in ancestors:
                ancestors.append("object")
                break
            ancestors.append(p)
            curr = p
        else:
            break
    if "object" not in ancestors:
        ancestors.append("object")
    return ancestors


def is_subtype(child: str, parent: str, parent_map: Dict[str, Any]) -> bool:
    """Checks whether child equals or inherits from parent in the type hierarchy."""
    if not child or not parent:
        return False
    c_low = str(child).strip().lower()
    p_low = str(parent).strip().lower()
    if c_low == p_low or p_low == "object":
        return True
    ancestors = [a.lower() for a in get_type_ancestors(c_low, parent_map)]
    return p_low in ancestors


def find_common_supertype(t1: str, t2: str, parent_map: Dict[str, Any]) -> str:
    """Returns the most specific common supertype for two types in the type hierarchy."""
    if not t1 or not t2:
        return "object"
    t1_s, t2_s = str(t1).strip(), str(t2).strip()
    if t1_s.lower() == t2_s.lower():
        return t1_s
    anc1 = [t1_s.lower()] + [a.lower() for a in get_type_ancestors(t1_s, parent_map)]
    anc2 = [t2_s.lower()] + [a.lower() for a in get_type_ancestors(t2_s, parent_map)]
    if t2_s.lower() in anc1:
        return t2_s
    if t1_s.lower() in anc2:
        return t1_s
    for a in anc1:
        if a in anc2:
            return a
    return "object"


def parse_typed_params(param_tokens: List[str]) -> List[Tuple[str, str]]:
    """
    Parses a token stream into [(var_name, type_name), ...].
    Example: ['?x', '?y', '-', 'location', '?z', '-', 'package'] -> [('?x', 'location'), ('?y', 'location'), ('?z', 'package')]
    """
    params = []
    current_vars = []
    i = 0
    while i < len(param_tokens):
        token = param_tokens[i]
        if token == "-":
            ptype = param_tokens[i + 1] if i + 1 < len(param_tokens) else "object"
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
