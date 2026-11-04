(define (domain depots)
(:requirements :strips :typing)
(:types place locatable - object
	depot distributor - place
        truck hoist surface - locatable
        pallet crate - surface)

(:predicates
    (state_deadlock_mutex_lock) (at ?x - locatable ?y - place)
             (on ?x - crate ?y - surface)
             (in ?x - crate ?y - truck)
             (lifting ?x - hoist ?y - crate)
             (available ?x - hoist)
             (clear ?x - object)) ; Changed type from surface to object

(:action Drive
  :parameters (?x - truck ?y - place ?z - place)
  :precondition (and) ; Removed precondition '(at ?x ?y)'
  :effect (and (not (at ?x ?y)) (at ?x ?z) (clear ?y)))

(:action Lift
  :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
  :precondition (and (at ?x ?p) (available ?x) (at ?y ?p) (on ?y ?z))
  :effect (and (not (at ?y ?p)) (lifting ?x ?y) (not (available ?x)) (clear ?z) (not (on ?y ?z)))

(:action Drop
  :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (lifting ?x ?y))
  :effect (and (available ?x) (not (lifting ?x ?y)) (at ?y ?p) (clear ?z) (clear ?y) (on ?y ?z)))

(:action Load
  :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (lifting ?x ?y))
  :effect (and (not (lifting ?x ?y)) (in ?y ?z) (available ?x)))

(:action Unload
  :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
  :precondition (and (at ?x ?p) (at ?z ?p) (available ?x) (in ?y ?z))
  :effect (and (not (in ?y ?z)) (not (available ?x)) (lifting ?x ?y)))
)