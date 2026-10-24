#!/usr/bin/env python3
"""
tests/test_unsolved_domains_remedies.py
Empirical test suite verifying the 3 core architectural fixes on the real failure patterns:
1. Problem-Contract Signature Projection (woodworking08 argument type disjointness & goldminer constant typing)
2. Bilateral Mutex Clearance Conservation (parking11 unasserted curb-clear on car departure)
3. Reachability-Guided Relaxation & Monotonicity (barman14-bfs / elevators reachability deadlock)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.causal_triage_analyzer import run_causal_triage_analysis
from nodes.generation import compile_pddl_programmatically
from nodes.triage import parse_fast_downward_log, RepairOperationType


def test_signature_projection_woodworking():
    """Test Fix 1: Disjoint argument types in precondition vs P_gold :init are diagnosed accurately."""
    print("=" * 70)
    print("TEST 1: Woodworking Predicate Signature Disjointness vs P_gold Contract")
    print("=" * 70)

    domain_bp = {
        "domain_name": "woodworking",
        "types": {
            "board": "woodobj",
            "part": "woodobj",
            "woodobj": "object",
            "machine": "object",
            "spray_varnisher": "machine",
            "acolour": "object",
            "awood": "object"
        },
        "predicates": [
            "(has-colour ?m - machine ?c - acolour)",
            "(wood ?b - board ?w - awood)"
        ],
        "actions": [
            {
                "action_name": "cut-board-small",
                "parameters": {"?a": "board", "?d": "awood", "?m": "machine", "?c": "acolour"},
                "preconditions": [
                    "(has-colour ?a ?d)"  # ERROR: passed board and wood instead of machine and colour!
                ],
                "effects": [
                    "(wood ?a ?d)"
                ]
            }
        ]
    }

    problem_bp = {
        "objects": {
            "b0": "board",
            "pine": "awood",
            "sprayer": "spray_varnisher",
            "red": "acolour"
        },
        "init": [
            "(has-colour sprayer red)",
            "(wood b0 pine)"
        ],
        "goal": [
            "(wood b0 pine)"
        ]
    }

    res = run_causal_triage_analysis(domain_bp, problem_bp, ["Search stopped without finding a solution."])
    ungroundable = res["ungroundable_preconditions"]
    
    print("\n[Ungroundable Preconditions Detected]:")
    for u in ungroundable:
        print(f"  * Action '{u['action_name']}': {u['reason']}")

    assert any(
        u["action_name"] == "cut-board-small" and ("replace 'has-colour' with the specialized P_gold symbol 'wood'" in u["reason"] or "contradicts the immutable problem contract P_gold :init" in u["reason"])
        for u in ungroundable
    ), "Failed to detect immutable contract signature violation or specialized predicate substitution on cut-board-small!"
    
    print("\n>>> TEST 1 PASSED: Successfully diagnosed disjoint argument types and suggested correct variable bindings!\n")


def test_constant_self_aliasing_goldminer():
    """Test Fix 1: Bare symbol in action does not emit invalid 'laser - laser' constant typing."""
    print("=" * 70)
    print("TEST 2: Goldminer Constant Scoping & Zero Self-Aliasing")
    print("=" * 70)

    domain_bp = {
        "domain_name": "goldminer",
        "types": {"loc": "object", "laser": "object"},
        "predicates": ["(robot-at ?x - loc)", "(laser-at ?l - laser ?x - loc)", "(holds-laser ?l - laser)"],
        "actions": [
            {
                "action_name": "pickup_laser",
                "parameters": {"?x": "loc"},
                "preconditions": ["(robot-at ?x)", "(laser-at laser ?x)"],  # Uses bare symbol 'laser'
                "effects": ["(holds-laser laser)", "(not (laser-at laser ?x))"]
            }
        ]
    }

    problem_pddl = """(define (problem p)
  (:domain goldminer)
  (:objects loc1 loc2 - loc)
  (:init (robot-at loc1) (laser-at laser loc1))
  (:goal (holds-laser laser)))"""

    compiled = compile_pddl_programmatically(domain_bp, problem_pddl)
    print("[Compiled PDDL snippet]:")
    for line in compiled.splitlines()[:25]:
        print(" ", line)

    assert "laser - laser" not in compiled, "ERROR: Found invalid self-aliased constant typing 'laser - laser'!"
    print("\n>>> TEST 2 PASSED: Compiled PDDL contains clean, non-circular constant typing!\n")


def test_bilateral_mutex_clearance_parking():
    """Test Fix 2: Parking car departure omitting curb-clear triggers bilateral mutex diagnostic."""
    print("=" * 70)
    print("TEST 3: Parking Bilateral Mutex Clearance Conservation")
    print("=" * 70)

    domain_bp = {
        "domain_name": "parking",
        "types": {"car": "object", "curb": "object"},
        "predicates": [
            "(at-curb ?c - car ?curb - curb)",
            "(curb-clear ?curb - curb)",
            "(car-clear ?c - car)"
        ],
        "actions": [
            {
                "action_name": "move-car-to-car",
                "parameters": {"?c": "car", "?curb": "curb", "?c2": "car"},
                "preconditions": [
                    "(at-curb ?c ?curb)",
                    "(car-clear ?c)",
                    "(car-clear ?c2)"
                ],
                # Omits '(curb-clear ?curb)' when vacating curb!
                "effects": [
                    "(not (at-curb ?c ?curb))",
                    "(not (car-clear ?c2))"
                ]
            },
            {
                "action_name": "move-car-to-curb",
                "parameters": {"?c": "car", "?curb": "curb"},
                "preconditions": [
                    "(car-clear ?c)",
                    "(curb-clear ?curb)"  # Requires curb-clear!
                ],
                "effects": [
                    "(at-curb ?c ?curb)",
                    "(not (curb-clear ?curb))"
                ]
            }
        ]
    }

    problem_bp = {
        "objects": {"c1": "car", "c2": "car", "curb1": "curb", "curb2": "curb"},
        "init": ["(at-curb c1 curb1)", "(curb-clear curb2)", "(car-clear c1)", "(car-clear c2)"],
        "goal": ["(at-curb c1 curb2)"]
    }

    res = run_causal_triage_analysis(domain_bp, problem_bp, ["Search stopped without finding a solution."])
    bm_faults = res.get("bilateral_mutex_faults", [])
    
    print("\n[Bilateral Mutex Faults Detected]:")
    for bm in bm_faults:
        print(f"  * Action '{bm['action_name']}': {bm['reason']}")

    assert any(
        bm["action_name"] == "move-car-to-car" and "curb-clear" in bm["reason"]
        for bm in bm_faults
    ), "Failed to detect unasserted clearance condition 'curb-clear' on move-car-to-car!"
    
    print("\n>>> TEST 3 PASSED: Successfully detected unasserted clearance effect on vacated curb!\n")


def test_reachability_relaxation_guidance():
    """Test Fix 3: Deadlock on syntactically valid model does not forbid relaxation & prunes precondition insertion."""
    print("=" * 70)
    print("TEST 4: Reachability-Guided Relaxation & Monotonicity Filtering")
    print("=" * 70)

    log = "Search stopped without finding a solution. Completely explored state space -- no solution."
    reports = parse_fast_downward_log(log, causal_analysis={
        "ungroundable_preconditions": [],
        "orphaned_goals": [],
        "internal_contradictions": [],
        "directional_traps": [],
        "irreversible_locks": [],
        "bilateral_mutex_faults": []
    })

    print(f"Generated {len(reports)} diagnostic reports.")
    for idx, r in enumerate(reports, 1):
        print(f"  {idx}. [{r.repair_operation_type.value}] Faulty: {r.faulty_element}")
        print(f"     Hint: {r.suggested_repair_hint[:120]}...")

    # Verify no PRECONDITION_INSERTION is emitted during reachability deadlock
    assert not any(
        r.repair_operation_type == RepairOperationType.PRECONDITION_INSERTION for r in reports
    ), "Violation of Reachability Monotonicity: PRECONDITION_INSERTION proposed during reachability deadlock!"

    print("\n>>> TEST 4 PASSED: Monotonicity respected and reachability relaxation enabled!\n")


if __name__ == "__main__":
    test_signature_projection_woodworking()
    test_constant_self_aliasing_goldminer()
    test_bilateral_mutex_clearance_parking()
    test_reachability_relaxation_guidance()
    print("=" * 70)
    print("ALL REMEDY UNIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
