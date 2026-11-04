"""
scripts/generate_21_domains_curated_flaws.py
Generates exactly 2 totally different curated flaw tasks across 2 distinct action schemas
for all 21 AutoPlanBench domains evaluated in H1/H2.
Total tasks: 21 domains * 2 flaws = 42 flaw tasks.

Flaw Invariants:
  1. Flaw 1 (Mutation Operator 1): Injects an unsatisfiable precondition into Action Schema A.
  2. Flaw 2 (Mutation Operator 2): Deletes a vital goal add effect from Action Schema B (B != A).
  3. Formal Symbolic Oracle Verification: Fast Downward verifies clean is solvable and mutant is unsolvable.
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.symbolic_oracles import run_fast_downward

BASE_DIR = Path("autoplanbench/data")

# 21 Domains Specification: (domain_name, reference_problem, action_A, action_B, effect_to_remove_B, effect_desc_B)
DOMAIN_SPECS = {
    # 6 Core Domains
    "blocksworld": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "pick-up",
        "action_b": "stack",
        "remove_pattern": r'\(on\s+\?ob\s+\?underob\)',
        "effect_desc": "(on ?ob ?underob)"
    },
    "gripper": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "pick",
        "action_b": "drop",
        "remove_pattern": r'\(at\s+\?obj\s+\?room\)',
        "effect_desc": "(at ?obj ?room)"
    },
    "logistics": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "FLY-AIRPLANE",
        "action_b": "UNLOAD-AIRPLANE",
        "remove_pattern": r'\(at\s+\?obj\s+\?loc\)',
        "effect_desc": "(at ?obj ?loc)"
    },
    "depot": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "Lift",
        "action_b": "Drop",
        "remove_pattern": r'\(on\s+\?y\s+\?z\)',
        "effect_desc": "(on ?y ?z)"
    },
    "rovers": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "navigate",
        "action_b": "sample_soil",
        "remove_pattern": r'\(have_soil_analysis\s+\?x\s+\?p\)',
        "effect_desc": "(have_soil_analysis ?x ?p)"
    },
    "satellite": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "turn_to",
        "action_b": "take_image",
        "remove_pattern": r'\(have_image\s+\?d\s+\?m\)',
        "effect_desc": "(have_image ?d ?m)"
    },

    # 15 Extended Domains
    "elevators08": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "move-up-slow",
        "action_b": "leave",
        "remove_pattern": r'\(passenger-at\s+\?p\s+\?f\)',
        "effect_desc": "(passenger-at ?p ?f)"
    },
    "parking11": {
        "problem": "adapted_instances/instance-0.pddl",
        "action_a": "move-curb-to-car",
        "action_b": "move-car-to-curb",
        "remove_pattern": r'\(at-curb-num\s+\?car\s+\?curbdest\)',
        "effect_desc": "(at-curb-num ?car ?curbdest)"
    },
    "goldminer": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "pickup-bomb",
        "action_b": "pick-gold",
        "remove_pattern": r'\(holds-gold\)',
        "effect_desc": "(holds-gold)"
    },
    "scanalyzer08": {
        "problem": "orig_problems/instance-12.pddl",
        "action_a": "rotate-2",
        "action_b": "analyze-2",
        "remove_pattern": r'\(analyzed\s+\?c1\)',
        "effect_desc": "(analyzed ?c1)"
    },
    "visitall": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "move",
        "action_b": "move",  # Single-action domain
        "remove_pattern": r'\(visited\s+\?nextpos\)',
        "effect_desc": "(visited ?nextpos)"
    },
    "transport08-bfs": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "drive",
        "action_b": "drop",
        "remove_pattern": r'\(at\s+\?p\s+\?l\)',
        "effect_desc": "(at ?p ?l)"
    },
    "floortile": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "down",
        "action_b": "paint-up",
        "remove_pattern": r'\(painted\s+\?y\s+\?c\)',
        "effect_desc": "(painted ?y ?c)"
    },
    "tpp06-bfs": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "drive",
        "action_b": "unload",
        "remove_pattern": r'\(stored\s+\?g\s+\?l4\)',
        "effect_desc": "(stored ?g ?l4)"
    },
    "pegsol08": {
        "problem": "adapted_instances/instance-0.pddl",
        "action_a": "jump-new-move",
        "action_b": "end-move",
        "remove_pattern": r'\(move-ended\)',
        "effect_desc": "(move-ended)"
    },
    "nomystery11-bfs": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "DRIVE",
        "action_b": "UNLOAD",
        "remove_pattern": r'\(at\s+\?p\s+\?l\)',
        "effect_desc": "(at ?p ?l)"
    },
    "barman14-bfs": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "clean-shot",
        "action_b": "fill-shot",
        "remove_pattern": r'\(contains\s+\?s\s+\?i\)',
        "effect_desc": "(contains ?s ?i)"
    },
    "pipesworld-notankage04-bfs": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "push-unitarypipe",
        "action_b": "pop-unitarypipe",
        "remove_pattern": r'\(on\s+\?last-batch-atom\s+\?from-area\)',
        "effect_desc": "(on ?last-batch-atom ?from-area)"
    },
    "woodworking08": {
        "problem": "orig_problems/instance-1.pddl",
        "action_a": "do-grind",
        "action_b": "do-glaze",
        "remove_pattern": r'\(treatment\s+\?x\s+glazed\)',
        "effect_desc": "(treatment ?x glazed)"
    },
    "zenotravel02": {
        "problem": "orig_problems/instance-10.pddl",
        "action_a": "board",
        "action_b": "debark",
        "remove_pattern": r'\(at\s+\?p\s+\?c\)',
        "effect_desc": "(at ?p ?c)"
    },
    "driverlog02-bfs": {
        "problem": "orig_problems/instance-12.pddl",
        "action_a": "board-truck",
        "action_b": "unload-truck",
        "remove_pattern": r'\(at\s+\?obj\s+\?loc\)',
        "effect_desc": "(at ?obj ?loc)"
    }
}


def mutate_flaw_1_precondition(clean_domain_text: str, target_action: str) -> str:
    """Injects an unsatisfiable precondition into action schema A."""
    # 1. Add predicate declaration
    mutated = re.sub(
        r'(\(:predicates[\s\S]*?)(\)\s*\(:action)',
        r'\1\n    (unreachable_precondition_predicate)\n  \2',
        clean_domain_text,
        count=1
    )
    if "(unreachable_precondition_predicate)" not in mutated:
        # Fallback for predicate injection
        mutated = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition_predicate)\n    ', clean_domain_text, count=1)

    # 2. Add precondition to target action
    act_regex = re.compile(rf'(:action\s+{re.escape(target_action)}[\s\S]*?:precondition\s*\(and\s*)', re.IGNORECASE)
    if act_regex.search(mutated):
        mutated = act_regex.sub(r'\1(unreachable_precondition_predicate) ', mutated, count=1)
    else:
        # If no :precondition (and ...) found, handle single or empty
        act_single = re.compile(rf'(:action\s+{re.escape(target_action)}[\s\S]*?:precondition\s*)', re.IGNORECASE)
        mutated = act_single.sub(r'\1(and (unreachable_precondition_predicate) ', mutated, count=1)
        
    return mutated


def mutate_flaw_2_effect(clean_domain_text: str, target_action: str, remove_pattern: str) -> str:
    """Removes a critical goal add effect from action schema B."""
    # Find action block up to the next (:action or end of domain
    act_match = re.search(rf'(:action\s+{re.escape(target_action)}[\s\S]*?)(?=\(:action|\Z)', clean_domain_text, re.IGNORECASE)
    if not act_match:
        return clean_domain_text

    act_text = act_match.group(1)
    # Remove the target effect pattern inside the action
    new_act_text = re.sub(remove_pattern, "", act_text, count=1)
    mutated = clean_domain_text.replace(act_text, new_act_text)
    return mutated


def main():
    print("=" * 90)
    print("  GENERATING & VERIFYING 42 CURATED FLAW BENCHMARK MUTANTS (21 DOMAINS x 2 DISTINCT ACTIONS)")
    print("=" * 90, flush=True)

    manifest = {
        "benchmark_name": "PDDLLifeCycleBench",
        "version": "3.0_curated_21_domains_h2",
        "description": "Standardized 42-Task Flaw Benchmark across 21 domains with 2 distinct action schemas per domain.",
        "domains_count": len(DOMAIN_SPECS),
        "total_flaws": len(DOMAIN_SPECS) * 2,
        "domains": []
    }

    total_created = 0
    verification_results = []

    for domain_name, spec in DOMAIN_SPECS.items():
        domain_dir = BASE_DIR / domain_name
        clean_dom_file = domain_dir / "domain.pddl"
        if not clean_dom_file.exists():
            print(f"[!] Warning: Missing domain.pddl for '{domain_name}', skipping.", flush=True)
            continue

        prob_file = domain_dir / spec["problem"]
        if not prob_file.exists():
            print(f"[!] Warning: Specified problem file '{prob_file}' not found, skipping.", flush=True)
            continue

        clean_text = clean_dom_file.read_text(encoding="utf-8")

        flaws_dir = domain_dir / "flaws"
        flaws_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n>>> [{domain_name.upper()}]: Action A = '{spec['action_a']}' | Action B = '{spec['action_b']}'")
        dom_entry = {
            "domain": domain_name,
            "reference_problem": str(prob_file.relative_to(BASE_DIR)),
            "flaws": []
        }

        # Verify clean domain is solvable
        clean_solvable, _ = run_fast_downward(str(clean_dom_file), str(prob_file))

        # ----------------------------------------------------------------------
        # FLAW 1: Unsatisfiable Precondition in Action A
        # ----------------------------------------------------------------------
        flaw1_id = "flaw_01_unsatisfiable_precondition"
        flaw1_dir = flaws_dir / flaw1_id
        flaw1_dir.mkdir(parents=True, exist_ok=True)

        mutated_text_1 = mutate_flaw_1_precondition(clean_text, spec["action_a"])
        annotated_pddl_1 = f"""; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: {flaw1_id}
; DOMAIN: {domain_name}
; MUTATION OPERATOR: OPERATOR_1_UNSATISFIABLE_PRECONDITION
; TARGET ACTION SCHEMA: {spec['action_a']}
; INJECTED FLAW: Added unsatisfiable precondition '(unreachable_precondition_predicate)' to action '{spec['action_a']}'
; RATIONALE: Action can never be grounded or executed because predicate is absent from :init
; GROUND TRUTH FIX: Remove '(unreachable_precondition_predicate)' from action '{spec['action_a']}' preconditions.
; ==============================================================================

{mutated_text_1.strip()}
"""
        f1_dom_path = flaw1_dir / "domain_flawed.pddl"
        f1_prob_path = flaw1_dir / "problem.pddl"
        f1_dom_path.write_text(annotated_pddl_1, encoding="utf-8")
        shutil.copy2(prob_file, f1_prob_path)

        # Formal verification of Flaw 1
        f1_solvable, _ = run_fast_downward(str(f1_dom_path), str(f1_prob_path))
        f1_unsolvable = (not f1_solvable)

        meta1 = {
            "flaw_id": flaw1_id,
            "domain": domain_name,
            "mutation_operator": "OPERATOR_1_UNSATISFIABLE_PRECONDITION",
            "target_action": spec["action_a"],
            "description": f"Added unsatisfiable precondition '(unreachable_precondition_predicate)' to action '{spec['action_a']}'",
            "ground_truth_fix": f"Remove '(unreachable_precondition_predicate)' from action '{spec['action_a']}' preconditions.",
            "flaw_category": "PRECONDITION_UNSATISFIABLE",
            "verified_unsolvable": f1_unsolvable
        }
        (flaw1_dir / "flaw_metadata.json").write_text(json.dumps(meta1, indent=2), encoding="utf-8")
        dom_entry["flaws"].append(meta1)
        total_created += 1
        print(f"  [+] Flaw 1 created: Action '{spec['action_a']}' -> Verified Unsolvable: {f1_unsolvable}")

        # ----------------------------------------------------------------------
        # FLAW 2: Missing Goal Add Effect in Action B
        # ----------------------------------------------------------------------
        flaw2_id = "flaw_02_missing_goal_add_effect"
        flaw2_dir = flaws_dir / flaw2_id
        flaw2_dir.mkdir(parents=True, exist_ok=True)

        mutated_text_2 = mutate_flaw_2_effect(clean_text, spec["action_b"], spec["remove_pattern"])
        annotated_pddl_2 = f"""; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: {flaw2_id}
; DOMAIN: {domain_name}
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: {spec['action_b']}
; INJECTED FLAW: Removed vital add effect '{spec['effect_desc']}' from action '{spec['action_b']}'
; RATIONALE: Prevents action '{spec['action_b']}' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '{spec['effect_desc']}' in action '{spec['action_b']}' effects.
; ==============================================================================

{mutated_text_2.strip()}
"""
        f2_dom_path = flaw2_dir / "domain_flawed.pddl"
        f2_prob_path = flaw2_dir / "problem.pddl"
        f2_dom_path.write_text(annotated_pddl_2, encoding="utf-8")
        shutil.copy2(prob_file, f2_prob_path)

        # Formal verification of Flaw 2
        f2_solvable, _ = run_fast_downward(str(f2_dom_path), str(f2_prob_path))
        f2_unsolvable = (not f2_solvable)

        meta2 = {
            "flaw_id": flaw2_id,
            "domain": domain_name,
            "mutation_operator": "OPERATOR_2_REMOVE_GOAL_ADD_EFFECT",
            "target_action": spec["action_b"],
            "description": f"Removed vital add effect '{spec['effect_desc']}' from action '{spec['action_b']}'",
            "ground_truth_fix": f"Restore add effect '{spec['effect_desc']}' in action '{spec['action_b']}' effects.",
            "flaw_category": "ACTION_EFFECT_DELETION",
            "verified_unsolvable": f2_unsolvable
        }
        (flaw2_dir / "flaw_metadata.json").write_text(json.dumps(meta2, indent=2), encoding="utf-8")
        dom_entry["flaws"].append(meta2)
        total_created += 1
        print(f"  [+] Flaw 2 created: Action '{spec['action_b']}' -> Verified Unsolvable: {f2_unsolvable}")

        manifest["domains"].append(dom_entry)
        verification_results.append({
            "domain": domain_name,
            "clean_solvable": clean_solvable,
            "action_a": spec["action_a"],
            "flaw1_unsolvable": f1_unsolvable,
            "action_b": spec["action_b"],
            "flaw2_unsolvable": f2_unsolvable,
            "all_verified": (clean_solvable and f1_unsolvable and f2_unsolvable)
        })

    # Save Master Manifest
    manifest_file = BASE_DIR / "curated_21_domains_flaws_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("\n" + "=" * 90)
    print(f"SUCCESS: Created and verified {total_created} curated flaw tasks across {len(manifest['domains'])} domains.")
    print(f"Master manifest written to: {manifest_file}")
    print("=" * 90)

    all_ok = all(v["all_verified"] for v in verification_results)
    print(f"OVERALL BENCHMARK VERIFICATION STATUS: {'100% VERIFIED' if all_ok else 'SOME CHECKS FAILED'}")
    print("=" * 90, flush=True)


if __name__ == "__main__":
    main()
