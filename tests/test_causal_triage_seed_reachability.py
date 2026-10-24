"""
tests/test_causal_triage_seed_reachability.py
Unit tests verifying domain-agnostic causal seed reachability analysis in causal_triage_analyzer.py.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.causal_triage_analyzer import run_causal_triage_analysis


def test_specialized_predicate_substitution():
    """
    Test that when an action requires (at ?r ?from) with [robot, room],
    and :init only has (at-robby robot1 room2) and (at ball1 room2),
    and 'move' produces (at ?r ?to) but requires (at ?r ?from),
    the causal triage analyzer detects the unseeded reachability cycle
    and prescribes replacing 'at' with specialized predicate 'at-robby'.
    """
    domain_bp = {
        "domain_name": "test-domain",
        "types": {"robot": "object", "room": "object", "item": "object"},
        "predicates": ["(at ?o - item ?x - room)", "(at-robby ?r - robot ?x - room)"],
        "actions": [
            {
                "action_name": "move",
                "parameters": {"?r": "robot", "?from": "room", "?to": "room"},
                "preconditions": ["(at ?r ?from)"], # Fault: uses 'at' instead of 'at-robby'
                "effects": ["(at ?r ?to)", "(not (at ?r ?from))"]
            },
            {
                "action_name": "pick",
                "parameters": {"?o": "item", "?x": "room"},
                "preconditions": ["(at ?o ?x)"],
                "effects": ["(not (at ?o ?x))"]
            },
            {
                "action_name": "drop",
                "parameters": {"?o": "item", "?x": "room"},
                "preconditions": [],
                "effects": ["(at ?o ?x)"]
            }
        ]
    }

    problem_bp = {
        "problem_name": "test-prob",
        "objects": {
            "robot1": "robot",
            "room1": "room",
            "room2": "room",
            "ball1": "item"
        },
        "init": [
            "(at-robby robot1 room2)",
            "(at ball1 room2)"
        ],
        "goal": [
            "(at ball1 room1)"
        ]
    }

    raw_errors = ["Fast Downward: Search stopped without finding a solution"]
    res = run_causal_triage_analysis(domain_bp, problem_bp, raw_errors)

    ungroundable = res["ungroundable_preconditions"]
    assert len(ungroundable) >= 1, "Expected at least 1 ungroundable precondition!"
    
    move_fault = next((u for u in ungroundable if u["action_name"] == "move"), None)
    print("DEBUG MOVE FAULT:", move_fault)
    assert move_fault is not None, "Failed to identify ungroundable precondition in action 'move'!"
    assert move_fault["best_match"] == "at-robby", f"Expected best_match 'at-robby', got {move_fault.get('best_match')}"
    assert "at-robby" in move_fault["reason"], f"Expected 'at-robby' in reason message, got: {move_fault['reason']}"
    print("TEST 1 (Specialized Predicate Substitution) PASSED!")


def test_permuted_argument_order():
    """
    Test that when an action uses (pointing ?d ?s) with [direction, satellite],
    but :init has (pointing sat1 dir1) with [satellite, direction],
    the analyzer detects the argument permutation and prescribes swapping arguments.
    """
    domain_bp = {
        "domain_name": "test-satellite",
        "types": {"satellite": "object", "direction": "object"},
        "predicates": ["(pointing ?s - satellite ?d - direction)"],
        "actions": [
            {
                "action_name": "turn_to",
                "parameters": {"?s": "satellite", "?d_new": "direction", "?d_prev": "direction"},
                "preconditions": ["(pointing ?d_prev ?s)"], # Fault: inverted argument order
                "effects": ["(pointing ?s ?d_new)", "(not (pointing ?s ?d_prev))"]
            }
        ]
    }

    problem_bp = {
        "problem_name": "test-prob",
        "objects": {
            "sat1": "satellite",
            "dir1": "direction",
            "dir2": "direction"
        },
        "init": [
            "(pointing sat1 dir1)"
        ],
        "goal": [
            "(pointing sat1 dir2)"
        ]
    }

    raw_errors = ["Fast Downward: Search stopped without finding a solution"]
    res = run_causal_triage_analysis(domain_bp, problem_bp, raw_errors)

    ungroundable = res["ungroundable_preconditions"]
    assert len(ungroundable) >= 1, "Expected at least 1 ungroundable precondition!"
    
    turn_fault = next((u for u in ungroundable if u["action_name"] == "turn_to"), None)
    print("DEBUG TURN FAULT:", turn_fault)
    assert turn_fault is not None, "Failed to identify ungroundable precondition in action 'turn_to'!"
    assert "swap argument order" in turn_fault["reason"].lower() or "order" in turn_fault["reason"].lower()
    print("TEST 2 (Permuted Argument Order) PASSED!")


def test_ground_mutex_clearance_conflict():
    """
    Test that when an action requires (on ?c ?s) and (clear ?s),
    but in :init whenever (on c p) holds, (clear c) holds and (clear p) does NOT hold,
    the analyzer detects that (clear ?s) is mutually contradictory with (on ?c ?s)
    and prescribes binding clear to the item parameter ?c.
    """
    domain_bp = {
        "domain_name": "test-stacking",
        "types": {"crate": "surface", "pallet": "surface", "surface": "object"},
        "predicates": ["(on ?c - crate ?s - surface)", "(clear ?s - surface)"],
        "actions": [
            {
                "action_name": "lift",
                "parameters": {"?c": "crate", "?s": "surface"},
                "preconditions": ["(on ?c ?s)", "(clear ?s)"], # Fault: asserts clear on base surface ?s
                "effects": ["(not (on ?c ?s))", "(clear ?s)"]
            }
        ]
    }
    problem_bp = {
        "objects": {"c1": "crate", "p1": "pallet"},
        "init": ["(on c1 p1)", "(clear c1)"], # p1 is NOT clear
        "goal": ["(clear p1)"]
    }
    raw_errors = ["Fast Downward: Search stopped without finding a solution"]
    res = run_causal_triage_analysis(domain_bp, problem_bp, raw_errors)

    ungroundable = res["ungroundable_preconditions"]
    conflict = next((u for u in ungroundable if u["action_name"] == "lift" and "mutually contradictory" in u["reason"]), None)
    assert conflict is not None, "Failed to identify ground mutex clearance conflict on base surface!"
    assert "(clear ?c)" in conflict["reason"] or "item parameter '?c'" in conflict["reason"]
    print("TEST 3 (Ground Mutex Clearance Conflict) PASSED!")


def test_irreversible_resource_depletion():
    """
    Test that when an action deletes (not (available ?r)),
    and no action in the domain produces (available ...),
    and available is required as a precondition,
    the analyzer flags irreversible resource depletion.
    """
    domain_bp = {
        "domain_name": "test-comm",
        "types": {"rover": "object"},
        "predicates": ["(available ?r - rover)", "(communicated ?r - rover)"],
        "actions": [
            {
                "action_name": "transmit",
                "parameters": {"?r": "rover"},
                "preconditions": ["(available ?r)"],
                "effects": ["(communicated ?r)", "(not (available ?r))"] # Fault: unreplenished delete
            }
        ]
    }
    problem_bp = {
        "objects": {"r1": "rover"},
        "init": ["(available r1)"],
        "goal": ["(communicated r1)"]
    }
    raw_errors = ["Fast Downward: Search stopped without finding a solution"]
    res = run_causal_triage_analysis(domain_bp, problem_bp, raw_errors)

    locks = res.get("irreversible_locks", [])
    assert len(locks) >= 1, "Failed to detect irreversible resource depletion!"
    assert locks[0]["predicate"] == "available"
    assert "irreversibly depleted" in locks[0]["reason"]
    print("TEST 4 (Irreversible Resource Depletion) PASSED!")


def test_static_parameter_aliasing_on_goal_producer():
    """
    Test Invariant 2b: Detects when a goal-producing action aliases a parameter
    with a static precondition whose initial instances exclude the required goal constant.
    """
    domain_bp = {
        "domain_name": "test-rover",
        "types": {"rover": "object", "lander": "object", "waypoint": "object"},
        "predicates": [
            "(at ?r - rover ?w - waypoint)",
            "(at_lander ?l - lander ?w - waypoint)",
            "(has_data ?r - rover ?w - waypoint)",
            "(communicated_data ?w - waypoint)"
        ],
        "actions": [
            {
                "action_name": "communicate",
                "parameters": {"?r": "rover", "?l": "lander", "?w": "waypoint"},
                "preconditions": [
                    "(at ?r ?w)",
                    "(at_lander ?l ?w)", # Fault: ?w is aliased to lander location!
                    "(has_data ?r ?w)"
                ],
                "effects": [
                    "(communicated_data ?w)"
                ]
            }
        ]
    }
    problem_bp = {
        "objects": {"r1": "rover", "l1": "lander", "w0": "waypoint", "w2": "waypoint"},
        "init": [
            "(at r1 w0)",
            "(at_lander l1 w0)", # lander is strictly at w0
            "(has_data r1 w2)"
        ],
        "goal": [
            "(communicated_data w2)" # requires w2, which cannot match w0 in at_lander
        ]
    }
    raw_errors = ["Fast Downward: Search stopped without finding a solution"]
    res = run_causal_triage_analysis(domain_bp, problem_bp, raw_errors)

    ungroundable = res["ungroundable_preconditions"]
    aliased = next((u for u in ungroundable if u["action_name"] == "communicate" and "co-indexed (aliased)" in u["reason"]), None)
    assert aliased is not None, "Failed to identify static parameter aliasing on goal producer!"
    assert "w2" in aliased["reason"]
    assert ("at_lander" in aliased["reason"] or "at" in aliased["reason"])
    print("TEST 5 (Static Parameter Aliasing on Goal Producer) PASSED!")


if __name__ == "__main__":
    test_specialized_predicate_substitution()
    test_permuted_argument_order()
    test_ground_mutex_clearance_conflict()
    test_irreversible_resource_depletion()
    test_static_parameter_aliasing_on_goal_producer()
    print("\nALL CAUSAL SEED REACHABILITY TESTS PASSED SUCCESSFULLY!")
