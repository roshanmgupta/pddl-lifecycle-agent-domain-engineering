(define (domain goldminer)
  (:requirements :strips :typing)

  (:types
    bomb gold laser location robot rock - object
    soft-rock - rock
    clear-location - location
  )

  (:predicates
    (connected ?x - location ?y - location)
    (at ?x - object ?l - location)
    (holding ?r - robot ?g - gold)
    (empty-arm ?r - robot)
    (clear ?l - location)
  )

  (:action pick_up_gold
    :parameters (?r - robot ?g - gold ?l - location)
    :precondition (and (at ?r ?l) (clear ?l) (empty-arm ?r))
    :effect (and (holding ?r ?g) (not (empty-arm ?r)))
  )

)