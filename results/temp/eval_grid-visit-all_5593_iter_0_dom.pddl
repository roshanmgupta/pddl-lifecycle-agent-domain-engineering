(define (domain grid-visit-all)
  (:requirements :typing)

  (:types
    place - object
  )

  (:predicates
    (connected ?x - object ?y - object)
    (at-robot ?x - object)
    (visited ?x - object)
  )

  (:action move
    :parameters (?curpos - place ?nextpos - place)
    :precondition (and (at-robot ?curpos) (connected ?curpos ?nextpos))
    :effect (and (at-robot ?nextpos) (visited ?nextpos) (not (at-robot ?curpos)))
  )

)