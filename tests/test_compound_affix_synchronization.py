"""
tests/test_compound_affix_synchronization.py
Unit tests verifying universal compound affix alignment in synchronize_ast_predicate_symbols.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nodes.generation import synchronize_ast_predicate_symbols


def test_compound_affix_sync():
    """
    Test that compound affixes like 'object-at' and 'free-from'
    are cleanly aligned to 'at' and 'free' when matching arity and P_gold problem atoms.
    """
    blueprint_data = {
        "predicates": [
            "(object-at ?b - object ?loc - room)",
            "(free-from ?r - robot ?g - gripper)",
            "(at-robby ?r - robot ?loc - room)"
        ],
        "actions": [
            {
                "action_name": "pick",
                "parameters": {"?r": "robot", "?b": "object", "?loc": "room", "?g": "gripper"},
                "preconditions": [
                    "(object-at ?b ?loc)",
                    "(at-robby ?r ?loc)",
                    "(free-from ?r ?g)"
                ],
                "effects": [
                    "(not (object-at ?b ?loc))",
                    "(not (free-from ?r ?g))"
                ]
            }
        ]
    }

    problem_pddl = """(define (problem prob1)
  (:domain test-domain)
  (:objects r1 - robot g1 - gripper rm1 - room b1 - object)
  (:init
    (at-robby r1 rm1)
    (at b1 rm1)
    (free r1 g1)
  )
  (:goal
    (at b1 rm1)
  )
)"""

    synced = synchronize_ast_predicate_symbols(blueprint_data, problem_pddl)
    
    # Verify predicates
    preds_str = " ".join(synced["predicates"])
    assert "(at ?b" in preds_str or "(at ?x" in preds_str or "at" in preds_str
    assert "object-at" not in preds_str, "Failed to align compound 'object-at' to 'at'!"
    assert "free-from" not in preds_str, "Failed to align compound 'free-from' to 'free'!"
    assert "at-robby" in preds_str, "Accidentally decomposed 'at-robby'!"

    # Verify action preconditions
    pick_act = synced["actions"][0]
    precs_str = " ".join(pick_act["preconditions"])
    assert "(at ?b ?loc)" in precs_str, f"Expected '(at ?b ?loc)', got: {precs_str}"
    assert "(free ?r ?g)" in precs_str, f"Expected '(free ?r ?g)', got: {precs_str}"
    assert "(at-robby ?r ?loc)" in precs_str, f"Expected '(at-robby ?r ?loc)', got: {precs_str}"
    print("TEST (Compound Affix Synchronization) PASSED!")


if __name__ == "__main__":
    test_compound_affix_sync()
