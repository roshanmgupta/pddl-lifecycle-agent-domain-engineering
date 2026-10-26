(define (domain grid-visit-all)
  (:requirements :strips)
  (:types place - object)
  (:predicates 
    (at-robot ?loc - place)
    (visited ?loc - place)
    (connected ?from ?to - place)
  )
  (:action move
    :parameters (?from ?to - place)
    :precondition (and 
                    (at-robot ?from)
                    (connected ?from ?to)
                  )
    :effect (and 
              (not (at-robot ?from))
              (at-robot ?to)
              (visited ?to)
            )
  )
)