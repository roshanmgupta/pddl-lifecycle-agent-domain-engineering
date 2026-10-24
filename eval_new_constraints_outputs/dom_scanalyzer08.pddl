(define (domain scanalyzer08)
  (:requirements :strips :typing)

  (:types
    car in out segment - object
  )

  (:predicates
    (in-cycle ?seg-in - segment ?seg-out - object)
    (on ?car - car ?seg - segment)
    (analyzed ?car - car)
    (has-analysis ?seg - segment)
  )

  (:action analyze_car
    :parameters (?car - car ?seg - segment ?seg-out - object)
    :precondition (and (on ?car ?seg) (in-cycle ?seg ?seg-out) (has-analysis ?seg))
    :effect (analyzed ?car)
  )

)