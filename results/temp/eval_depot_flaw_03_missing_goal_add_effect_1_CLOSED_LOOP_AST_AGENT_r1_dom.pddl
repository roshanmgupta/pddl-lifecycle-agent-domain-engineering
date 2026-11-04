(define (domain depots)
  (:requirements :strips :typing)

  (:types
    locatable place - object
    depot distributor - place
    hoist surface truck - locatable
    crate pallet - surface
  )

  (:predicates
    (at ?x - object ?y - object)
    (on ?x - object ?y - object)
    (in ?x - object ?y - object)
    (lifting ?x - object ?y - object)
    (available ?x - object)
    (clear ?x - object)
  )

  (:action Drive
    :parameters (?x - truck ?y - place ?z - place)
    :precondition (at ?x ?y)
    :effect (and (not (at ?x ?y)) (at ?x ?z))
  )

  (:action Lift
    :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
    :precondition (and (at ?x ?p) (available ?x) (at ?y ?p) (on ?y ?z) (clear ?y))
    :effect (and (lifting ?x ?y) (not (at ?y ?p)) (not (on ?y ?z)) (not (clear ?y)) (clear ?z) (not (available ?x)))
  )

  (:action Drop
    :parameters (?x - hoist ?y - crate ?z - surface ?p - place)
    :precondition (and (at ?x ?p) (at ?z ?p) (clear ?z) (lifting ?x ?y))
    :effect (and (available ?x) (not (lifting ?x ?y)) (at ?y ?p) (on ?y ?z) (clear ?y) (not (clear ?z)))
  )

  (:action Load
    :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
    :precondition (and (at ?x ?p) (at ?z ?p) (lifting ?x ?y))
    :effect (and (in ?y ?z) (available ?x) (not (lifting ?x ?y)))
  )

  (:action Unload
    :parameters (?x - hoist ?y - crate ?z - truck ?p - place)
    :precondition (and (at ?x ?p) (at ?z ?p) (available ?x) (in ?y ?z))
    :effect (and (lifting ?x ?y) (not (in ?y ?z)) (not (available ?x)))
  )

)