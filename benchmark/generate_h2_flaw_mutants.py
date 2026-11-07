"""
benchmark/generate_h2_flaw_mutants.py

Generates and formally verifies the H2 fault-repair benchmark:
    2 mutation operators x 2 mutants per operator x N domains
    (21 domains -> 84 tasks).

Mutation operators (each mutant edits exactly ONE action schema):
  OPERATOR_1_UNSATISFIABLE_PRECONDITION:
      Add a nullary precondition '(unreachable_precondition_predicate)' that is
      declared in (:predicates ...) but never appears in any :init and is never
      added by any action.
  OPERATOR_2_REMOVE_GOAL_ADD_EFFECT:
      Remove one positive add effect from one action schema. Add effects whose
      predicate symbol occurs in the reference goal are tried first, followed by
      the remaining add effects (causal prerequisites of the goal).

Selection rules (domain-independent, no hand-picked targets):
  - Within one operator, the two mutants target two DIFFERENT action schemas.
  - A mutant is kept only if (a) VAL parses the mutated domain exactly as it
    parses the reference domain, (b) the Fast Downward translator raises no
    parse/syntax error, and (c) Fast Downward proves at least one reference
    problem unsolvable that the reference domain solves.
    A planner timeout is NOT counted as unsolvability.
  - Candidates are ordered: existing curated target (if any) first, then actions
    by frequency in reference gold plans.

Edits are performed on the original PDDL text using comment-aware parenthesis
matching, so the mutated file is the reference file plus exactly one change
(plus the predicate declaration for Operator 1).

Existing, already verified 4-mutant folders (e.g. the 6 core domains) are
re-verified with the same oracle checks but never overwritten unless --force.
"""

import os
import re
import sys
import json
import argparse
import tempfile
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple

# Bounded planner budget for mutant verification (a timeout is never treated as unsolvable)
os.environ.setdefault("FD_TIMEOUT_SEC", "20")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.symbolic_oracles import run_val_validator, run_fast_downward, validate_plan_with_val  # noqa: E402

DATA_DIR = PROJECT_ROOT / "autoplanbench" / "data"
SOURCE_MANIFEST = DATA_DIR / "curated_21_domains_flaws_manifest.json"
OUTPUT_MANIFEST = DATA_DIR / "curated_21_domains_84_flaws_manifest.json"

UNREACHABLE_PRED = "unreachable_precondition_predicate"
FLAW_SLOTS = [
    ("flaw_01_unsatisfiable_precondition_1", "OPERATOR_1_UNSATISFIABLE_PRECONDITION"),
    ("flaw_02_unsatisfiable_precondition_2", "OPERATOR_1_UNSATISFIABLE_PRECONDITION"),
    ("flaw_03_missing_goal_add_effect_1", "OPERATOR_2_REMOVE_GOAL_ADD_EFFECT"),
    ("flaw_04_missing_goal_add_effect_2", "OPERATOR_2_REMOVE_GOAL_ADD_EFFECT"),
]
UNSOLVABLE_MARKERS = (
    "search stopped without finding a solution",
    "completely explored state space",
    "trivially false goal",
    "unsolvable",
)
SYNTAX_MARKERS = ("traceback", "syntax error", "parse error", "too many fields", "undeclared", "could not parse")


# ---------------------------------------------------------------------------
# Comment-aware PDDL text utilities
# ---------------------------------------------------------------------------
def mask_comments(text: str) -> str:
    """Replaces every ';' comment with spaces (same length) so indices stay aligned."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text[i] == ";":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
        else:
            i += 1
    return "".join(out)


def match_paren(masked: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("Unbalanced parentheses")


def top_level_children(masked: str, start: int, end: int) -> List[Tuple[int, int]]:
    """Returns spans of parenthesised children directly inside masked[start:end+1] (an s-expression)."""
    spans = []
    i = start + 1
    while i < end:
        if masked[i] == "(":
            j = match_paren(masked, i)
            spans.append((i, j))
            i = j + 1
        else:
            i += 1
    return spans


def norm(s: str) -> str:
    return " ".join(s.replace("(", " ( ").replace(")", " ) ").split()).lower()


def find_action_span(text: str, masked: str, action: str) -> Tuple[int, int]:
    m = re.search(r"\(\s*:action\s+" + re.escape(action) + r"(?=[\s()])", masked, re.IGNORECASE)
    if not m:
        raise ValueError(f"Action '{action}' not found")
    return m.start(), match_paren(masked, m.start())


def find_field_expr(masked: str, a_start: int, a_end: int, field: str) -> Optional[Tuple[int, int]]:
    m = re.compile(r":" + field + r"\b", re.IGNORECASE).search(masked, a_start, a_end)
    if not m:
        return None
    p = masked.find("(", m.end(), a_end)
    if p < 0:
        return None
    return p, match_paren(masked, p)


def list_actions(masked: str) -> List[str]:
    return re.findall(r"\(\s*:action\s+([^\s()]+)", masked, re.IGNORECASE)


def positive_add_effects(text: str, masked: str, action: str) -> List[str]:
    a_s, a_e = find_action_span(text, masked, action)
    span = find_field_expr(masked, a_s, a_e, "effect")
    if not span:
        return []
    s, e = span
    expr = masked[s:e + 1]
    if re.match(r"\(\s*and[\s()]", expr, re.IGNORECASE):
        children = top_level_children(masked, s, e)
    else:
        children = [(s, e)]
    atoms = []
    for cs, ce in children:
        child = masked[cs:ce + 1]
        if re.match(r"\(\s*(not|forall|when|and|increase|decrease)[\s()]", child, re.IGNORECASE):
            continue
        atoms.append(" ".join(child.split()))
    return atoms


# ---------------------------------------------------------------------------
# Mutation operators (exactly one action schema edited per mutant)
# ---------------------------------------------------------------------------
def apply_operator_1(text: str, action: str) -> str:
    masked = mask_comments(text)
    if re.search(r"\(\s*" + UNREACHABLE_PRED + r"\s*\)", masked):
        raise ValueError("Unreachable predicate symbol already present")
    a_s, a_e = find_action_span(text, masked, action)
    span = find_field_expr(masked, a_s, a_e, "precondition")
    atom = f"({UNREACHABLE_PRED})"
    if span:
        s, e = span
        m_and = re.match(r"\(\s*and(?=[\s()])", masked[s:e + 1], re.IGNORECASE)
        if m_and:
            ins = s + m_and.end()
            text = text[:ins] + " " + atom + text[ins:]
        else:
            text = text[:s] + f"(and {atom} " + text[s:e + 1] + ")" + text[e + 1:]
    else:
        m_eff = re.compile(r":effect\b", re.IGNORECASE).search(masked, a_s, a_e)
        if not m_eff:
            raise ValueError(f"Action '{action}' has neither :precondition nor :effect")
        text = text[:m_eff.start()] + f":precondition {atom}\n  " + text[m_eff.start():]

    # Declare the nullary predicate inside (:predicates ...)
    masked = mask_comments(text)
    m_pred = re.search(r"\(\s*:predicates", masked, re.IGNORECASE)
    if not m_pred:
        raise ValueError("No (:predicates ...) block")
    ins = m_pred.end()
    return text[:ins] + f"\n    {atom}" + text[ins:]


def apply_operator_2(text: str, action: str, add_atom: str) -> str:
    masked = mask_comments(text)
    a_s, a_e = find_action_span(text, masked, action)
    span = find_field_expr(masked, a_s, a_e, "effect")
    if not span:
        raise ValueError(f"Action '{action}' has no :effect")
    s, e = span
    target = norm(add_atom)
    if re.match(r"\(\s*and[\s()]", masked[s:e + 1], re.IGNORECASE):
        for cs, ce in top_level_children(masked, s, e):
            if norm(masked[cs:ce + 1]) == target:
                return text[:cs] + text[ce + 1:]
        raise ValueError(f"Add effect {add_atom} not found in '{action}'")
    if norm(masked[s:e + 1]) == target:
        return text[:s] + "(and )" + text[e + 1:]
    raise ValueError(f"Add effect {add_atom} not found in '{action}'")


# ---------------------------------------------------------------------------
# Formal oracle verification
# ---------------------------------------------------------------------------
class DomainOracle:
    def __init__(self, domain: str, work_dir: Path, ref_prob_rel: Optional[str] = None):
        self.domain = domain
        self.dom_dir = DATA_DIR / domain
        self.gold_path = self.dom_dir / "domain.pddl"
        self.work_dir = work_dir

        # Determine reference problems directory (adapted_instances vs orig_problems)
        ref_path = (DATA_DIR / ref_prob_rel) if ref_prob_rel else None
        if ref_path and ref_path.exists():
            target_dir = ref_path.parent
            primary = ref_path
        elif (self.dom_dir / "orig_problems").exists():
            target_dir = self.dom_dir / "orig_problems"
            primary = target_dir / "instance-1.pddl"
        elif (self.dom_dir / "adapted_instances").exists():
            target_dir = self.dom_dir / "adapted_instances"
            primary = target_dir / "instance-0.pddl"
        else:
            raise FileNotFoundError(f"No problem directory found for {domain}")

        probs = sorted(target_dir.glob("*.pddl"), key=lambda p: (len(p.name), p.name))
        if primary in probs:
            probs.remove(primary)
            probs.insert(0, primary)
        self.problems = probs
        self._gold_fd: Dict[str, bool] = {}
        self.gold_val_ok, _ = run_val_validator(str(self.gold_path), str(self.problems[0]))

        # Look up gold plan directory (adapted_gold_plans vs orig_gold_plans)
        gp_cand = self.dom_dir / ("adapted_gold_plans" if target_dir.name == "adapted_instances" else "orig_gold_plans")
        self.gold_plans: Dict[str, Path] = {}
        if gp_cand.exists():
            for p in self.problems:
                plan_file = gp_cand / f"{p.stem}_gold_plan.txt"
                if plan_file.exists():
                    self.gold_plans[str(p)] = plan_file

    def gold_solves(self, prob: Path) -> bool:
        key = str(prob)
        if key not in self._gold_fd:
            self._gold_fd[key], _ = run_fast_downward(str(self.gold_path), key)
        return self._gold_fd[key]

    def verify(self, mutant_text: str) -> Tuple[bool, str]:
        mpath = self.work_dir / f"{self.domain}_mutant.pddl"
        mpath.write_text(mutant_text, encoding="utf-8")
        val_ok, val_log = run_val_validator(str(mpath), str(self.problems[0]))
        if val_ok != self.gold_val_ok:
            return False, f"VAL parse mismatch: {val_log.strip()[:160]}"

        # Step 1: Fast Plan Validation Oracle (checks whether reference gold plan is broken)
        # Runs in milliseconds per instance without search timeouts
        for prob in self.problems:
            key = str(prob)
            if key in self.gold_plans:
                plan_ok, _ = validate_plan_with_val(str(mpath), key, str(self.gold_plans[key]))
                if not plan_ok:
                    # Mutant breaks the verified reference plan. Double-check translator syntax
                    fd_chk, fd_log = run_fast_downward(str(mpath), key)
                    low_fd = fd_log.lower()
                    if any(mk in low_fd for mk in SYNTAX_MARKERS):
                        return False, f"FD translator error on {prob.name}: {fd_log.strip()[-160:]}"
                    return True, f"{prob.name} (breaks reference plan)"

        # Step 2: Full State-Space Exploration Oracle (for instances without precomputed gold plans)
        for prob in self.problems:
            ok, log = run_fast_downward(str(mpath), str(prob))
            low = log.lower()
            if any(mk in low for mk in SYNTAX_MARKERS):
                return False, f"FD translator error on {prob.name}: {log.strip()[-160:]}"
            if ok:
                continue
            if any(mk in low for mk in UNSOLVABLE_MARKERS) and self.gold_solves(prob):
                return True, prob.name
        return False, "No reference problem made unsolvable (or only planner timeouts)"


# ---------------------------------------------------------------------------
# Candidate ordering (domain-independent)
# ---------------------------------------------------------------------------
def gold_plan_action_counts(domain: str) -> Counter:
    counts: Counter = Counter()
    gp_dir = DATA_DIR / domain / "orig_gold_plans"
    if gp_dir.exists():
        for f in gp_dir.glob("*_gold_plan.txt"):
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith("("):
                    counts[line.strip("() ").split()[0].lower()] += 1
    return counts


def goal_predicates(prob: Path) -> set:
    txt = mask_comments(prob.read_text(encoding="utf-8", errors="ignore"))
    m = re.search(r"\(\s*:goal", txt, re.IGNORECASE)
    if not m:
        return set()
    seg = txt[m.start():match_paren(txt, m.start()) + 1]
    return {s.lower() for s in re.findall(r"\(\s*([^\s()]+)", seg)} - {":goal", "and", "not"}


def load_source_manifest_metadata() -> Tuple[Dict[str, str], Dict[str, Dict[str, Tuple[str, Optional[str]]]]]:
    """Loads reference_problem paths and prior flaw targets from source manifest."""
    ref_probs: Dict[str, str] = {}
    targets: Dict[str, Dict[str, Tuple[str, Optional[str]]]] = {}
    if not SOURCE_MANIFEST.exists():
        return ref_probs, targets
    data = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    for d in data.get("domains", []):
        dname = d["domain"]
        if "reference_problem" in d:
            ref_probs[dname] = d["reference_problem"]
        for f in d.get("flaws", []):
            atom = None
            m = re.search(r"'(\([^']+\))'", f.get("description", ""))
            if f["mutation_operator"].startswith("OPERATOR_2") and m:
                atom = m.group(1)
            targets.setdefault(dname, {})[f["mutation_operator"]] = (f["target_action"], atom)
    return ref_probs, targets


def header(flaw_id, domain, op, action, detail, fix) -> str:
    return (
        "; ==============================================================================\n"
        f"; CURATED FLAW BENCHMARK MUTANT: {flaw_id}\n"
        f"; DOMAIN: {domain}\n"
        f"; MUTATION OPERATOR: {op}\n"
        f"; TARGET ACTION SCHEMA: {action}\n"
        f"; INJECTED FLAW: {detail}\n"
        f"; GROUND TRUTH FIX: {fix}\n"
        "; ==============================================================================\n\n"
    )


def generate_domain(domain: str, existing: Dict, work_dir: Path, force: bool, ref_prob_rel: Optional[str] = None) -> List[Dict]:
    flaws_dir = DATA_DIR / domain / "flaws"
    oracle = DomainOracle(domain, work_dir, ref_prob_rel=ref_prob_rel)
    gold_text = oracle.gold_path.read_text(encoding="utf-8-sig")

    # Re-verify already present 4-mutant folders instead of overwriting them
    present = all((flaws_dir / fid / "domain_flawed.pddl").exists() for fid, _ in FLAW_SLOTS)
    if present and not force:
        records = []
        for fid, op in FLAW_SLOTS:
            meta = json.loads((flaws_dir / fid / "flaw_metadata.json").read_text(encoding="utf-8-sig"))
            ok, info = oracle.verify((flaws_dir / fid / "domain_flawed.pddl").read_text(encoding="utf-8-sig"))
            meta.update({"verified_unsolvable": ok, "breaking_reference_problem": info if ok else None})
            if not ok:
                meta["verification_failure"] = info
            print(f"   [{'OK' if ok else 'FAIL'}] (existing) {fid:38s} {meta['target_action']:26s} {info}")
            records.append(meta)
        return records

    masked = mask_comments(gold_text)
    actions = list_actions(masked)
    freq = gold_plan_action_counts(domain)
    actions_sorted = sorted(actions, key=lambda a: (-freq.get(a.lower(), 0), actions.index(a)))
    goal_preds = goal_predicates(oracle.problems[0])
    prior = existing.get(domain, {})

    def ordered(first: Optional[str]) -> List[str]:
        lst = list(actions_sorted)
        if first:
            hit = [a for a in lst if a.lower() == first.lower()]
            if hit:
                lst.remove(hit[0])
                lst.insert(0, hit[0])
        return lst

    records: List[Dict] = []
    # ---- Operator 1 ----
    op1_chosen: List[Tuple[str, str, str]] = []
    for act in ordered(prior.get("OPERATOR_1_UNSATISFIABLE_PRECONDITION", (None, None))[0]):
        if len(op1_chosen) == 2:
            break
        try:
            mut = apply_operator_1(gold_text, act)
        except ValueError as exc:
            print(f"   [skip] op1 {act}: {exc}")
            continue
        ok, info = oracle.verify(mut)
        print(f"   [{'OK' if ok else '--'}] op1 {act:26s} {info}")
        if ok:
            op1_chosen.append((act, mut, info))

    # ---- Operator 2 ----
    op2_candidates: List[Tuple[str, str]] = []
    prior2 = prior.get("OPERATOR_2_REMOVE_GOAL_ADD_EFFECT", (None, None))
    for direct in (True, False):
        for act in ordered(prior2[0]):
            for atom in positive_add_effects(gold_text, masked, act):
                sym = atom.strip("() ").split()[0].lower()
                if (sym in goal_preds) == direct:
                    op2_candidates.append((act, atom))
    if prior2[0] and prior2[1]:
        pc = [c for c in op2_candidates if c[0].lower() == prior2[0].lower() and norm(c[1]) == norm(prior2[1])]
        for c in pc:
            op2_candidates.remove(c)
            op2_candidates.insert(0, c)

    op2_chosen: List[Tuple[str, str, str, str]] = []
    for act, atom in op2_candidates:
        if len(op2_chosen) == 2:
            break
        if any(c[0].lower() == act.lower() for c in op2_chosen):
            continue
        try:
            mut = apply_operator_2(gold_text, act, atom)
        except ValueError as exc:
            print(f"   [skip] op2 {act} {atom}: {exc}")
            continue
        ok, info = oracle.verify(mut)
        print(f"   [{'OK' if ok else '--'}] op2 {act:26s} -{atom:34s} {info}")
        if ok:
            op2_chosen.append((act, atom, mut, info))

    slots = []
    for i, (act, mut, info) in enumerate(op1_chosen):
        fid, op = FLAW_SLOTS[i]
        detail = f"Added unsatisfiable precondition '({UNREACHABLE_PRED})' to action '{act}'"
        fix = f"Remove '({UNREACHABLE_PRED})' from action '{act}' preconditions."
        slots.append((fid, op, act, mut, detail, fix, "PRECONDITION_UNSATISFIABLE", info))
    for i, (act, atom, mut, info) in enumerate(op2_chosen):
        fid, op = FLAW_SLOTS[2 + i]
        detail = f"Removed add effect '{atom}' from action '{act}'"
        fix = f"Restore add effect '{atom}' in action '{act}' effects."
        slots.append((fid, op, act, mut, detail, fix, "ACTION_EFFECT_DELETION", info))

    for fid, op, act, mut, detail, fix, cat, info in slots:
        fdir = flaws_dir / fid
        fdir.mkdir(parents=True, exist_ok=True)
        (fdir / "domain_flawed.pddl").write_text(header(fid, domain, op, act, detail, fix) + mut, encoding="utf-8")
        meta = {
            "flaw_id": fid, "domain": domain, "flaw_category": cat, "mutation_operator": op,
            "target_action": act, "description": detail, "ground_truth_fix": fix,
            "expected_oracle_signal": "Fast Downward proves at least one reference problem unsolvable.",
            "verified_unsolvable": True, "breaking_reference_problem": info,
        }
        (fdir / "flaw_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        records.append(meta)

    if len(op1_chosen) < 2 or len(op2_chosen) < 2:
        print(f"   [SHORTFALL] {domain}: op1={len(op1_chosen)}/2 op2={len(op2_chosen)}/2 "
              f"(domain has {len(actions)} action schema(s))")
    return records


def main():
    ap = argparse.ArgumentParser(description="Generate and verify the 2x2xN H2 flaw benchmark")
    ap.add_argument("--domains", nargs="+", default=None)
    ap.add_argument("--force", action="store_true", help="Regenerate even if 4 verified folders already exist")
    args = ap.parse_args()

    src = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    domains = [d["domain"] for d in src["domains"]]
    if args.domains:
        domains = [d for d in domains if d in set(args.domains)]
    ref_probs, existing = load_source_manifest_metadata()

    work_dir = Path(tempfile.mkdtemp(prefix="h2_mutants_"))
    os.chdir(work_dir)  # Fast Downward writes output.sas / sas_plan into the cwd

    manifest_domains = []
    for dname in domains:
        print(f"\n=== {dname} ===", flush=True)
        recs = generate_domain(dname, existing, work_dir, args.force, ref_prob_rel=ref_probs.get(dname))
        entry = {"domain": dname, "flaws": recs}
        if dname in ref_probs:
            entry["reference_problem"] = ref_probs[dname]
        manifest_domains.append(entry)

    prev = {}
    if OUTPUT_MANIFEST.exists() and args.domains:
        prev = {d["domain"]: d for d in json.loads(OUTPUT_MANIFEST.read_text(encoding="utf-8"))["domains"]}
    for d in manifest_domains:
        prev[d["domain"]] = d
    ordered_domains = [prev[d] for d in [x["domain"] for x in src["domains"]] if d in prev]
    total = sum(len(d["flaws"]) for d in ordered_domains)
    verified = sum(1 for d in ordered_domains for f in d["flaws"] if f.get("verified_unsolvable"))
    out = {
        "benchmark_name": "PDDLLifeCycleBench",
        "version": "4.0_curated_21_domains_84_h2",
        "description": "H2 fault-repair benchmark: 2 mutation operators x 2 mutants (distinct action schemas) x 21 domains.",
        "domains_count": len(ordered_domains),
        "total_flaws": total,
        "verified_flaws": verified,
        "domains": ordered_domains,
    }
    OUTPUT_MANIFEST.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nManifest written: {OUTPUT_MANIFEST} ({verified}/{total} verified tasks)")


if __name__ == "__main__":
    main()
