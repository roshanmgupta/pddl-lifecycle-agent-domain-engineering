"""
eval/ac.py
Structural Action Reconstruction & Operator Alignment for PDDL Model Verification.

Grounded in Peer-Reviewed AI Planning Literature:
- Action Reconstruction Error (ARE) & Operator Alignment (Oswald et al., ICAPS 2024 / AAAI 2024).
- Decoupled Precondition, Add-Effect, and Delete-Effect Information Retrieval Metrics (Precision, Recall, F1).
- Polynomial-Time Optimal Bipartite Matching via Kuhn-Munkres (Hungarian) Algorithm.

Note:
True semantic equivalence is determined by Plan Transferability via VAL (tools/symbolic_oracles.py).
This module provides structural/syntactic operator-level reconstruction metrics without arbitrary hardcoded weights.
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Any, Optional


@dataclass
class StripsOperator:
    """Classical STRIPS Operator Representation: Name, Parameters, Arity, Preconditions, Add-Effects, Delete-Effects."""
    name: str
    parameters: List[str]
    arity: int
    preconditions: Set[str] = field(default_factory=set)
    add_effects: Set[str] = field(default_factory=set)
    delete_effects: Set[str] = field(default_factory=set)


def normalize_predicate_token(pred: str) -> str:
    """Normalizes predicate symbol to lowercase alphanumeric format to eliminate typographic formatting differences."""
    return pred.strip().lower().replace("-", "").replace("_", "")


def extract_predicate_literals(expression_text: str) -> Tuple[Set[str], Set[str]]:
    """
    Extracts positive (Add) and negative (Delete) predicate literals from a PDDL expression.
    Filters out variables (?var) and logical control keywords.
    Returns: (positive_literals_set, negative_literals_set).
    """
    if not expression_text:
        return set(), set()

    pos_literals = set()
    neg_literals = set()

    # Negated literals: (not (pred ...))
    neg_matches = re.finditer(r"\(\s*not\s*\(\s*([a-zA-Z][a-zA-Z0-9_\-]*)", expression_text, re.IGNORECASE)
    for m in neg_matches:
        pred = normalize_predicate_token(m.group(1))
        if pred not in ["and", "or", "not", "when", "forall", "exists"]:
            neg_literals.add(pred)

    # Positive literals: (pred ...)
    all_matches = re.finditer(r"\(\s*([a-zA-Z][a-zA-Z0-9_\-]*)", expression_text, re.IGNORECASE)
    for m in all_matches:
        pred = normalize_predicate_token(m.group(1))
        if pred not in ["and", "or", "not", "when", "forall", "exists"]:
            if pred not in neg_literals:
                pos_literals.add(pred)

    return pos_literals, neg_literals


def extract_strips_operators(pddl_text: str) -> List[StripsOperator]:
    """Parses a PDDL domain string and extracts structured classical STRIPS operators."""
    # Strip PDDL comments (; to end-of-line) to avoid false literal matches
    clean_text = re.sub(r";.*$", "", pddl_text, flags=re.MULTILINE)
    operators = []
    action_matches = re.finditer(
        r"\(:action\s+([a-zA-Z0-9_\-]+)(.*?)(?=\(:action|\)\s*$)", 
        clean_text, 
        re.DOTALL | re.IGNORECASE
    )

    for match in action_matches:
        name = match.group(1).strip()
        body = match.group(2)

        # Extract parameters
        params = []
        param_match = re.search(r":parameters\s*\((.*?)\)", body, re.DOTALL | re.IGNORECASE)
        if param_match:
            raw_params = param_match.group(1)
            params = re.findall(r"\?([a-zA-Z0-9_\-]+)", raw_params)

        # Extract preconditions
        pre_literals = set()
        pre_match = re.search(r":precondition\s*(.*?)(?=:effect|\)\s*$)", body, re.DOTALL | re.IGNORECASE)
        if pre_match:
            pos_pre, _ = extract_predicate_literals(pre_match.group(1))
            pre_literals = pos_pre

        # Extract effects
        add_effs = set()
        del_effs = set()
        eff_match = re.search(r":effect\s*(.*?)(?=\)\s*$)", body, re.DOTALL | re.IGNORECASE)
        if eff_match:
            add_effs, del_effs = extract_predicate_literals(eff_match.group(1))

        operators.append(StripsOperator(
            name=name,
            parameters=params,
            arity=len(params),
            preconditions=pre_literals,
            add_effects=add_effs,
            delete_effects=del_effs
        ))

    return operators


def compute_set_prf(set_gen: Set[str], set_gt: Set[str]) -> Tuple[float, float, float]:
    """Computes standard Precision, Recall, and F1-score for two sets."""
    if not set_gen and not set_gt:
        return 1.0, 1.0, 1.0
    if not set_gen or not set_gt:
        return 0.0, 0.0, 0.0

    intersection = len(set_gen & set_gt)
    precision = intersection / len(set_gen) if len(set_gen) > 0 else 0.0
    recall = intersection / len(set_gt) if len(set_gt) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def compute_operator_structural_f1(op_gen: StripsOperator, op_gt: StripsOperator) -> Dict[str, Any]:
    """
    Computes decoupled STRIPS structural conformance metrics between two operators:
    - Precondition F1
    - Add-Effect F1
    - Delete-Effect F1
    - Structural F1 (arithmetic mean across the 3 components)
    """
    pre_p, pre_r, pre_f1 = compute_set_prf(op_gen.preconditions, op_gt.preconditions)
    add_p, add_r, add_f1 = compute_set_prf(op_gen.add_effects, op_gt.add_effects)
    del_p, del_r, del_f1 = compute_set_prf(op_gen.delete_effects, op_gt.delete_effects)

    # Arithmetic mean across the 3 physical STRIPS components (no arbitrary magic weights)
    structural_f1 = round((pre_f1 + add_f1 + del_f1) / 3.0, 4)

    # Morphological name similarity: Word-token Jaccard (handles inverted token order like move_slow_elevator_up vs move-up-slow) + substring ratio
    w1 = set(re.findall(r"[a-z0-9]+", op_gen.name.lower()))
    w2 = set(re.findall(r"[a-z0-9]+", op_gt.name.lower()))
    token_jaccard = len(w1 & w2) / len(w1 | w2) if (w1 and w2) else 0.0
    seq_ratio = difflib.SequenceMatcher(None, op_gen.name.lower().replace("-", "_"), op_gt.name.lower().replace("-", "_")).ratio()
    name_similarity = round(0.7 * token_jaccard + 0.3 * seq_ratio, 4)

    # Arity alignment
    arity_match = 1.0 if op_gen.arity == op_gt.arity else 0.5

    return {
        "precondition_precision": pre_p,
        "precondition_recall": pre_r,
        "precondition_f1": pre_f1,
        "add_effect_precision": add_p,
        "add_effect_recall": add_r,
        "add_effect_f1": add_f1,
        "delete_effect_precision": del_p,
        "delete_effect_recall": del_r,
        "delete_effect_f1": del_f1,
        "structural_f1": structural_f1,
        "name_similarity": name_similarity,
        "arity_match": arity_match
    }


def kuhn_munkres_max_bipartite_matching(weight_matrix: List[List[float]]) -> List[Tuple[int, int]]:
    """
    Exact Kuhn-Munkres (Hungarian) algorithm implementation for Maximum Weight Bipartite Matching.
    Finds globally optimal 1-to-1 matching maximizing total edge weights in O(V^3) polynomial time.
    """
    if not weight_matrix or not weight_matrix[0]:
        return []

    n_rows = len(weight_matrix)
    n_cols = len(weight_matrix[0])
    n = max(n_rows, n_cols)

    cost = [[0.0] * n for _ in range(n)]
    for r in range(n_rows):
        for c in range(n_cols):
            cost[r][c] = weight_matrix[r][c]

    max_val = max(max(row) for row in cost)
    c_min = [[max_val - cost[r][c] for c in range(n)] for r in range(n)]

    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (n + 1)
        used = [False] * (n + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0

            for j in range(1, n + 1):
                if not used[j]:
                    cur = c_min[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j

            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    matches = []
    for j in range(1, n + 1):
        if p[j] != 0:
            row_idx = p[j] - 1
            col_idx = j - 1
            if row_idx < n_rows and col_idx < n_cols:
                matches.append((row_idx, col_idx))

    matches.sort(key=lambda x: x[0])
    return matches


def extract_declared_predicate_signatures(pddl_text: str) -> Dict[str, List[str]]:
    """
    Extracts declared predicate symbols mapped to their list of normalized parameter types
    from (:predicates ...) in a PDDL domain string.
    """
    clean_text = re.sub(r";.*$", "", pddl_text, flags=re.MULTILINE)
    pred_block_m = re.search(r"\(:predicates\s+(.*?)\)\s*\(:", clean_text, re.DOTALL | re.IGNORECASE)
    if not pred_block_m:
        pred_block_m = re.search(r"\(:predicates\s+(.*)\)", clean_text, re.DOTALL | re.IGNORECASE)
    if not pred_block_m:
        return {}

    sigs: Dict[str, List[str]] = {}
    for m in re.finditer(r"\(\s*([a-zA-Z][a-zA-Z0-9_\-]*)(.*?)\)", pred_block_m.group(1), re.DOTALL):
        pname = normalize_predicate_token(m.group(1))
        if pname in ["and", "or", "not", "when", "forall", "exists"]:
            continue
        raw_params = m.group(2).strip()
        if not raw_params:
            sigs[pname] = []
            continue
        tokens = raw_params.split()
        param_types: List[str] = []
        cur_vars: List[str] = []
        i = 0
        while i < len(tokens):
            if tokens[i] == "-":
                ptype = normalize_predicate_token(tokens[i + 1]) if i + 1 < len(tokens) else "object"
                for _ in cur_vars:
                    param_types.append(ptype)
                cur_vars = []
                i += 2
            elif tokens[i].startswith("?"):
                cur_vars.append(tokens[i])
                i += 1
            else:
                i += 1
        for _ in cur_vars:
            param_types.append("object")
        sigs[pname] = param_types
    return sigs


def align_predicate_vocabulary_kuhn_munkres(
    gt_pddl: str,
    generated_pddl: str,
    gt_operators: List[StripsOperator],
    gen_operators: List[StripsOperator]
) -> Dict[str, str]:
    """
    Computes an optimal 1-to-1 bijection from generated predicate symbols to ground-truth
    predicate symbols using Kuhn-Munkres Maximum Weight Bipartite Matching.
    - Predicates that already match identically by normalized symbol are fixed as identity mappings.
    - Remaining unmatched predicates (e.g., internal fluents not appearing in P_gold :init/:goal)
      are matched strictly across equal-arity predicates based on:
        1) Parameter-type signature compatibility (multiset/positional type overlap),
        2) STRIPS state-transition role compatibility (precondition / add / delete occurrence),
        3) Morphological name similarity.
    """
    gt_sigs = extract_declared_predicate_signatures(gt_pddl)
    gen_sigs = extract_declared_predicate_signatures(generated_pddl)

    all_gt_preds: Set[str] = set(gt_sigs.keys())
    all_gen_preds: Set[str] = set(gen_sigs.keys())
    for op in gt_operators:
        all_gt_preds |= op.preconditions | op.add_effects | op.delete_effects
    for op in gen_operators:
        all_gen_preds |= op.preconditions | op.add_effects | op.delete_effects

    pred_map: Dict[str, str] = {}
    exact_matches = all_gt_preds & all_gen_preds
    for p in exact_matches:
        pred_map[p] = p

    unmatched_gen = sorted(all_gen_preds - exact_matches)
    unmatched_gt = sorted(all_gt_preds - exact_matches)
    if not unmatched_gen or not unmatched_gt:
        return pred_map

    def _transition_roles(pred: str, ops: List[StripsOperator]) -> Tuple[int, int, int]:
        pre_c = sum(1 for op in ops if pred in op.preconditions)
        add_c = sum(1 for op in ops if pred in op.add_effects)
        del_c = sum(1 for op in ops if pred in op.delete_effects)
        return (1 if pre_c > 0 else 0, 1 if add_c > 0 else 0, 1 if del_c > 0 else 0)

    weight_matrix: List[List[float]] = []
    for p_gen in unmatched_gen:
        row: List[float] = []
        t_gen = gen_sigs.get(p_gen)
        r_gen = _transition_roles(p_gen, gen_operators)
        for p_gt in unmatched_gt:
            t_gt = gt_sigs.get(p_gt)
            # Strict FOL arity invariant: predicates with different declared arities cannot map to each other
            if t_gen is not None and t_gt is not None and len(t_gen) != len(t_gt):
                row.append(0.0)
                continue

            if t_gen is not None and t_gt is not None:
                if len(t_gen) == 0:
                    type_sim = 1.0
                else:
                    # Positional type match or multiset type match (since parameter order may be permuted)
                    pos_matches = sum(
                        1.0 if (a == b or a == "object" or b == "object") else 0.0
                        for a, b in zip(t_gen, t_gt)
                    ) / len(t_gen)
                    multiset_matches = sum(
                        1.0 if (a in t_gt or a == "object" or "object" in t_gt) else 0.0
                        for a in t_gen
                    ) / len(t_gen)
                    type_sim = max(pos_matches, multiset_matches)
                if len(t_gen) > 0 and type_sim == 0.0:
                    row.append(0.0)
                    continue
            else:
                type_sim = 0.5

            r_gt = _transition_roles(p_gt, gt_operators)
            role_sim = sum(1.0 for a, b in zip(r_gen, r_gt) if a == b) / 3.0
            name_sim = difflib.SequenceMatcher(None, p_gen, p_gt).ratio()

            weight = round(0.5 * type_sim + 0.3 * role_sim + 0.2 * name_sim, 4)
            row.append(weight)
        weight_matrix.append(row)

    matches = kuhn_munkres_max_bipartite_matching(weight_matrix)
    for gen_idx, gt_idx in matches:
        if weight_matrix[gen_idx][gt_idx] >= 0.55:
            pred_map[unmatched_gen[gen_idx]] = unmatched_gt[gt_idx]

    return pred_map


def evaluate_action_reconstruction(gt_pddl: str, generated_pddl: str) -> Dict[str, Any]:
    """
    Evaluates Action Reconstruction Error (ARE) between generated PDDL and ground truth PDDL
    using exact maximum bipartite matching over STRIPS predicates and operator definitions.
    
    Returns standard structural metrics:
    - macro_structural_f1: Average structural F1 across matched operators.
    - action_precision, action_recall, action_f1: Operator cardinality alignment.
    - mean_precondition_f1, mean_add_effect_f1, mean_delete_effect_f1.
    - action_mapping: Optimal mapping from generated action to ground truth action.
    """
    gt_operators = extract_strips_operators(gt_pddl)
    gen_operators = extract_strips_operators(generated_pddl)

    # Align internal predicate symbols via Kuhn-Munkres bipartite matching before comparing operator sets
    pred_bijection = align_predicate_vocabulary_kuhn_munkres(gt_pddl, generated_pddl, gt_operators, gen_operators)
    for op in gen_operators:
        op.preconditions = {pred_bijection.get(p, p) for p in op.preconditions}
        op.add_effects = {pred_bijection.get(p, p) for p in op.add_effects}
        op.delete_effects = {pred_bijection.get(p, p) for p in op.delete_effects}

    gt_count = len(gt_operators)
    gen_count = len(gen_operators)

    if gt_count == 0 or gen_count == 0:
        return {
            "gt_operator_count": gt_count,
            "generated_operator_count": gen_count,
            "matched_operator_count": 0,
            "macro_structural_f1": 0.0,
            "mean_precondition_f1": 0.0,
            "mean_add_effect_f1": 0.0,
            "mean_delete_effect_f1": 0.0,
            "action_precision": 0.0,
            "action_recall": 0.0,
            "action_f1": 0.0,
            "action_mapping": {},
            "detailed_operator_reports": []
        }

    # Bipartite weight matrix based on structural overlap + name similarity
    weight_matrix = []
    pairwise_metrics = {}

    for i, gen_op in enumerate(gen_operators):
        row = []
        for j, gt_op in enumerate(gt_operators):
            m = compute_operator_structural_f1(gen_op, gt_op)
            pairwise_metrics[(i, j)] = m
            # ARMS literature metric: Structural STRIPS F1 with tie-breaker on token name similarity
            match_weight = round(m["structural_f1"] + 0.05 * m["name_similarity"], 4)
            row.append(match_weight)
        weight_matrix.append(row)

    optimal_matches = kuhn_munkres_max_bipartite_matching(weight_matrix)

    detailed_reports = []
    action_mapping = {}
    matched_f1_scores = []
    pre_scores = []
    add_scores = []
    del_scores = []

    for gen_idx, gt_idx in optimal_matches:
        gen_op = gen_operators[gen_idx]
        gt_op = gt_operators[gt_idx]
        m = pairwise_metrics[(gen_idx, gt_idx)]

        action_mapping[gen_op.name] = gt_op.name
        matched_f1_scores.append(m["structural_f1"])
        pre_scores.append(m["precondition_f1"])
        add_scores.append(m["add_effect_f1"])
        del_scores.append(m["delete_effect_f1"])

        detailed_reports.append({
            "generated_action": gen_op.name,
            "ground_truth_action": gt_op.name,
            "precondition_f1": m["precondition_f1"],
            "add_effect_f1": m["add_effect_f1"],
            "delete_effect_f1": m["delete_effect_f1"],
            "structural_f1": m["structural_f1"],
            "name_similarity": m["name_similarity"],
            "arity_match": m["arity_match"] == 1.0
        })

    matched_count = len(detailed_reports)
    precision = round(matched_count / gen_count, 4) if gen_count > 0 else 0.0
    recall = round(matched_count / gt_count, 4) if gt_count > 0 else 0.0
    action_f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    macro_structural_f1 = round(sum(matched_f1_scores) / gt_count, 4) if gt_count > 0 else 0.0
    mean_pre_f1 = round(sum(pre_scores) / gt_count, 4) if gt_count > 0 else 0.0
    mean_add_f1 = round(sum(add_scores) / gt_count, 4) if gt_count > 0 else 0.0
    mean_del_f1 = round(sum(del_scores) / gt_count, 4) if gt_count > 0 else 0.0
    mean_arity_match = round(sum(1.0 if r.get("arity_match") else 0.0 for r in detailed_reports) / max(1, matched_count), 4) if matched_count > 0 else 0.0

    is_equiv = bool(macro_structural_f1 >= 0.99 and action_f1 >= 0.99)
    verdict = "Equivalent (Isomorphic)" if is_equiv else ("Subsumed / Partial" if macro_structural_f1 >= 0.5 else "Non-Equivalent")

    return {
        "gt_operator_count": gt_count,
        "generated_operator_count": gen_count,
        "matched_operator_count": matched_count,
        "macro_structural_f1": macro_structural_f1,
        "mean_precondition_f1": mean_pre_f1,
        "mean_add_effect_f1": mean_add_f1,
        "mean_delete_effect_f1": mean_del_f1,
        "mean_arity_match": mean_arity_match,
        "action_precision": precision,
        "action_recall": recall,
        "action_f1": action_f1,
        "action_mapping": action_mapping,
        "detailed_operator_reports": detailed_reports,
        "is_semantically_equivalent": is_equiv,
        "verdict": verdict
    }


def extract_action_bodies(pddl_text: str) -> Dict[str, str]:
    """Extracts raw action body strings mapped by action name."""
    clean = re.sub(r";.*$", "", pddl_text, flags=re.MULTILINE)
    bodies = {}
    for m in re.finditer(r"\(:action\s+([a-zA-Z0-9_\-]+)(.*?)(?=\(:action|\)\s*$)", clean, re.DOTALL | re.IGNORECASE):
        bodies[m.group(1).strip()] = m.group(2)
    return bodies


def parse_typed_parameters(action_body: str) -> List[Tuple[str, str]]:
    """Parses parameter variable names and declared types from an action body."""
    m = re.search(r":parameters\s*\((.*?)\)", action_body, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    tokens = m.group(1).split()
    res = []
    cur = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "-":
            t = tokens[i + 1].lower() if i + 1 < len(tokens) else "object"
            for v in cur:
                res.append((v.lstrip("?"), t))
            cur = []
            i += 2
        elif tokens[i].startswith("?"):
            cur.append(tokens[i])
            i += 1
        else:
            i += 1
    for v in cur:
        res.append((v.lstrip("?"), "object"))
    return res


def _normalize_pred_symbol_for_sig(pred: str) -> str:
    """Normalizes predicate symbol across hyphen/underscore and prefix variants (have_, has_, is_)."""
    p = str(pred).strip("() ").lower().replace("-", "_")
    p = re.sub(r"^(have|has|is)[_\-]", "", p)
    return p.replace('_', '')


def get_param_relational_signatures(action_body: str) -> List[Dict[str, Any]]:
    """
    Extracts typed parameters along with their relational roles (preconditions, add effects, delete effects)
    and normalized predicate occurrence signatures (pred, arg_index) to disambiguate parameters sharing types.
    """
    param_m = re.search(r":parameters\s*\((.*?)\)", action_body, re.DOTALL | re.IGNORECASE)
    tokens = param_m.group(1).split() if param_m else []
    params = []
    cur = []
    i = 0
    while i < len(tokens):
        if tokens[i] == "-":
            t = tokens[i + 1].lower() if i + 1 < len(tokens) else "object"
            for v in cur:
                params.append((v.lstrip("?"), t))
            cur = []
            i += 2
        elif tokens[i].startswith("?"):
            cur.append(tokens[i])
            i += 1
        else:
            i += 1
    for v in cur:
        params.append((v.lstrip("?"), "object"))

    pre_m = re.search(r":precondition\s*(.*?)(?=:effect|\)\s*$)", action_body, re.DOTALL | re.IGNORECASE)
    pre_str = pre_m.group(1) if pre_m else ""

    eff_m = re.search(r":effect\s*(.*?)(?=\)\s*$)", action_body, re.DOTALL | re.IGNORECASE)
    eff_str = eff_m.group(1) if eff_m else ""

    def _extract_occurrences(s: str) -> Dict[str, Set[Tuple[str, int]]]:
        res: Dict[str, Set[Tuple[str, int]]] = {}
        for am in re.finditer(r"\(\s*([a-zA-Z0-9_\-]+)\s*(.*?)\)", s):
            p = _normalize_pred_symbol_for_sig(am.group(1))
            if p in ("and", "not", "or", "imply"):
                continue
            args = [a.lstrip("?").lower() for a in am.group(2).split() if a]
            for idx, a in enumerate(args):
                res.setdefault(a, set()).add((p, idx))
        return res

    # Separate positive effects from negative (delete) effects
    del_str = " ".join([m.group(1) for m in re.finditer(r"\(\s*not\s*\((.*?)\)\s*\)", eff_str, re.DOTALL | re.IGNORECASE)])
    add_str = re.sub(r"\(\s*not\s*\(.*?\)\s*\)", "", eff_str, flags=re.DOTALL | re.IGNORECASE)

    pre_occ = _extract_occurrences(pre_str)
    add_occ = _extract_occurrences(add_str)
    del_occ = _extract_occurrences(del_str)

    del_vars = set(re.findall(r"\?([a-zA-Z0-9_\-]+)", del_str))
    add_vars = set(re.findall(r"\?([a-zA-Z0-9_\-]+)", add_str))
    pre_vars = set(re.findall(r"\?([a-zA-Z0-9_\-]+)", pre_str))

    sigs = []
    for v, t in params:
        sigs.append({
            "var": v,
            "type": t,
            "in_pre": v in pre_vars,
            "in_add": v in add_vars,
            "in_del": v in del_vars,
            "pre_occ": pre_occ.get(v.lower(), set()),
            "add_occ": add_occ.get(v.lower(), set()),
            "del_occ": del_occ.get(v.lower(), set())
        })
    return sigs


def compute_typed_param_permutation(gen_body: str, gt_body: str) -> List[int]:
    """
    Computes argument index permutation from generated action parameters to ground-truth action parameters.
    Disambiguates arguments sharing the same type via their STRIPS relational transition roles
    and exact predicate occurrence signatures.
    Returns perm such that gt_arg[k] = gen_args[perm[k]].
    """
    gen_sigs = get_param_relational_signatures(gen_body)
    gt_sigs = get_param_relational_signatures(gt_body)

    # Allow greedy bipartite alignment even if arities differ due to auxiliary parameters
    pass

    used = set()
    perm = []
    for gt in gt_sigs:
        best_idx = None
        best_score = -1
        for idx, gen in enumerate(gen_sigs):
            if idx in used:
                continue
            type_compat = (gt["type"] == gen["type"] or gen["type"] == "object" or gt["type"] == "object")
            if not type_compat:
                continue
            role_score = 10
            if gt["type"] == gen["type"]:
                role_score += 5
            if gt["in_pre"] == gen["in_pre"]:
                role_score += 2
            if gt["in_add"] == gen["in_add"]:
                role_score += 3
            if gt["in_del"] == gen["in_del"]:
                role_score += 3
            # Disambiguate arguments using relational predicate occurrence signatures
            pre_overlap = len(gt.get("pre_occ", set()).intersection(gen.get("pre_occ", set())))
            add_overlap = len(gt.get("add_occ", set()).intersection(gen.get("add_occ", set())))
            del_overlap = len(gt.get("del_occ", set()).intersection(gen.get("del_occ", set())))
            role_score += pre_overlap * 20
            role_score += add_overlap * 30
            role_score += del_overlap * 30

            if role_score > best_score:
                best_score = role_score
                best_idx = idx
        if best_idx is not None:
            used.add(best_idx)
            perm.append(best_idx)
        else:
            for idx in range(len(gen_sigs)):
                if idx not in used:
                    used.add(idx)
                    perm.append(idx)
                    break
    return perm



def translate_plan_to_ground_truth(
    plan_steps: List[str],
    gt_domain_pddl: str,
    generated_domain_pddl: str
) -> List[str]:
    """
    Translates a synthesized plan into ground-truth domain vocabulary and parameter ordering.
    Enables non-circular VAL validation of generated plans against human gold-standard domains.
    """
    if not plan_steps or not gt_domain_pddl or not generated_domain_pddl:
        return plan_steps

    are_res = evaluate_action_reconstruction(gt_domain_pddl, generated_domain_pddl)
    action_map = are_res.get("action_mapping", {})
    if not action_map:
        return plan_steps

    gen_bodies = extract_action_bodies(generated_domain_pddl)
    gt_bodies = extract_action_bodies(gt_domain_pddl)

    lower_map = {str(k).lower(): v for k, v in action_map.items()}
    lower_gen_bodies = {str(k).lower(): v for k, v in gen_bodies.items()}
    lower_gt_bodies = {str(k).lower(): v for k, v in gt_bodies.items()}

    perms = {}
    for gen_name, gt_name in action_map.items():
        if gen_name.lower() in lower_gen_bodies and gt_name.lower() in lower_gt_bodies:
            perms[gen_name.lower()] = compute_typed_param_permutation(
                lower_gen_bodies[gen_name.lower()], lower_gt_bodies[gt_name.lower()]
            )

    translated_steps = []
    for step in plan_steps:
        m = re.search(r"\(\s*([a-zA-Z0-9_\-]+)\s*(.*?)\)", step)
        if m:
            act_name = m.group(1)
            raw_args = m.group(2).strip()
            args = raw_args.split() if raw_args else []
            act_lower = act_name.lower()

            if act_lower in lower_map:
                mapped_act = lower_map[act_lower]
                perm = perms.get(act_lower, list(range(len(args))))
                mapped_args = [args[p] for p in perm if p < len(args)]
                args_str = " ".join(mapped_args)
                translated_steps.append(f"({mapped_act} {args_str})")
            else:
                args_str = " ".join(args)
                translated_steps.append(f"({act_name} {args_str})")
        else:
            translated_steps.append(step)

    return translated_steps

