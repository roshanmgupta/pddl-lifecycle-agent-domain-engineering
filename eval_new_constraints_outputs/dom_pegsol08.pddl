(define (domain pegsol08)
  (:requirements :strips :typing)

  (:types
    location - object
  )

  (:predicates
    (in-line ?x - location ?y - location ?z - location)
    (free ?x - location)
    (occupied ?x - location)
  )

)