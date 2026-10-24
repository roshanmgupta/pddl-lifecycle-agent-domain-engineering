(define (domain visitall)
  (:requirements :strips :typing)

  (:types
    place - object
  )

  (:predicates
    (at ?robot - place ?from - place)
    (visited ?p - place)
    (connected ?p1 - place ?p2 - place)
  )

  (:action move_robot
    :parameters (?robot - place ?from - place ?to - place)
    :precondition (and (at ?robot ?from) (connected ?from ?to))
    :effect (and (at ?robot ?to) (not (at ?robot ?from)))
  )

  (:action visit_place
    :parameters (?r - place ?p - place)
    :precondition (and (at ?r ?p) (not (visited ?p)))
    :effect (visited ?p)
  )

)