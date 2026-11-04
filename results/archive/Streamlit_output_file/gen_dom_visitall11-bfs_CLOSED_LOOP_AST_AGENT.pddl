(define (domain grid-visit-all)
  (:requirements :strips :typing)

  (:types
    place - object
  )

  (:predicates
    (at-robot ?p - place)
    (connected ?p1 - place ?p2 - place)
    (visited ?p - place)
  )

  (:action move_robot
    :parameters (?from - place ?to - place)
    :precondition (and (at-robot ?from) (connected ?from ?to))
    :effect (and (at-robot ?to) (visited ?to) (not (at-robot ?from)))
  )

)