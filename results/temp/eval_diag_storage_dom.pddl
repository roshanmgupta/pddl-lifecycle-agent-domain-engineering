(define (domain Storage-Propositional)
  (:requirements :typing)

  (:types
    hoist place surface - object
    area crate - surface
    container depot - place
    storearea transitarea - area
  )

  (:predicates
    (clear ?s - object)
    (in ?x1 - surface ?x2 - place)
    (available ?h - object)
    (lifting ?h - object ?c - object)
    (at ?h - object ?a - object)
    (on ?c - object ?s - object)
    (connected ?a1 - object ?a2 - object)
    (compatible ?c1 - object ?c2 - object)
  )

  (:action lift
    :parameters (?h - hoist ?c - crate ?a1 - storearea ?a2 - area ?p - place)
    :precondition (and (available ?h) (at ?h ?a1) (on ?c ?a1) (clear ?c))
    :effect (and (not (available ?h)) (not (on ?c ?a1)) (clear ?a1) (lifting ?h ?c))
  )

  (:action drop
    :parameters (?h - hoist ?c - crate ?a1 - storearea ?a2 - area ?p - place)
    :precondition (and (lifting ?h ?c) (at ?h ?a1) (clear ?a1))
    :effect (and (available ?h) (on ?c ?a1) (clear ?a1) (not (lifting ?h ?c)) (in ?c ?p))
  )

  (:action move
    :parameters (?h - hoist ?from - storearea ?to - storearea)
    :precondition (and (at ?h ?from) (connected ?from ?to))
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action go-out
    :parameters (?h - hoist ?from - storearea ?to - transitarea)
    :precondition (and (at ?h ?from) (connected ?from ?to))
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )

  (:action go-in
    :parameters (?h - hoist ?from - transitarea ?to - storearea)
    :precondition (and (at ?h ?from) (connected ?from ?to))
    :effect (and (not (at ?h ?from)) (at ?h ?to))
  )

)