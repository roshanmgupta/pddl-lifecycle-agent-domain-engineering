(define (domain visitall)
  (:requirements :strips :typing)

  (:types
    place - object
  )

  (:predicates
    (at ?r - place ?loc - place)
    (visited ?loc - place)
    (connected ?loc1 - place ?loc2 - place)
  )

  (:action move_robot
    :parameters (?r - place ?from - place ?to - place)
    :precondition (and (at ?r ?from) (connected ?from ?to))
    :effect (and (at ?r ?to) (visited ?to) (not (at ?r ?from)))
  )

)