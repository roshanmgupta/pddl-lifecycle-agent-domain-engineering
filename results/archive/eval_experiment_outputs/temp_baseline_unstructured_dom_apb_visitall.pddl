(define (domain grid-visit-all)
  (:requirements :typing)
  (:types place)
  (:predicates
    (connected ?x ?y - place)
    (at-robot ?x - place)
    (visited ?x - place)
  )
  (:action move
    :parameters (?curpos - place ?nextpos - place)
    :precondition (and (at-robot ?curpos) (connected ?curpos ?nextpos))
    :effect (and (at-robot ?nextpos) (visited ?nextpos) (not (at-robot ?curpos)))
  )
)