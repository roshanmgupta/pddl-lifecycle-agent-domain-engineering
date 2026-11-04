; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_03_missing_goal_add_effect_1
; DOMAIN: depot
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: Drop
; INJECTED FLAW: Removed required goal add effect '(on ?y ?z)' from action 'Drop'
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: Restore add effect '(on ?y ?z)' in action 'Drop' effects.
; ==============================================================================

(define (domain depots)
(:requirements :strips :typing)
(:types place locatable - object
	depot distributor - place
        truck hoist surface - locatable
        pallet crate - surface)

(:predicates (at ?x - locatable ?y - place)
             (on ?x - crate ?y - surface)
             (in ?x - crate ?y - truck)
             (lifting ?x - hoist ?y - crate)
             (available ?x - hoist)
             (clear ?x - surface))

(:action Drive
  :parameters (?x - truck ?y - place ?z - place)
  :precondition (and (at ?x ?y))
  :effect (and (not (at ?x ?y)) (at ?x ?z)))

(:action Lift
  :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
  :precondition (and (at ?x ?p) (available ?x) (at ?y ?p) (on ?y ?z) (clear ?y))
  :effect (and (not (at ?y ?p)) (lifting ?x ?y) (not (clear ?y)) (not (available ?x)) (clear ?z) (not (on ?y ?z))))

(:action Drop
  :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (clear ?z) (lifting ?x ?y))
  :effect (and (available ?x) (not (lifting ?x ?y)) (at ?y ?p) (not (clear ?z)) (clear ?y)))

(:action Load
  :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (lifting ?x ?y))
  :effect (and (not (lifting ?x ?y)) (in ?y ?z) (available ?x)))

(:action Unload
  :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (available ?x) (in ?y ?z))
  :effect (and (not (in ?y ?z)) (not (available ?x)) (lifting ?x ?y)))
)
