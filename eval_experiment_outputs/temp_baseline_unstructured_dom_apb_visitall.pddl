(define (domain visitall)
  (:requirements :strips)
  (:types place - object)
  (:predicates 
    (robot-at ?l - place)
    (visited ?l - place)
    (connected ?from ?to - place)
  )
  (:action move
    :parameters (?from ?to - place)
    :precondition (and (robot-at ?from) (connected ?from ?to))
    :effect (and 
              (robot-at ?to)
              (not (robot-at ?from))
              (visited ?to)
            )
  )
)