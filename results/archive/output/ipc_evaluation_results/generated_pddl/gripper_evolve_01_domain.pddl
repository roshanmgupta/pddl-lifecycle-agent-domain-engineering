(define (domain gripper_domain)
  (:requirements :strips :typing)

  (:types
    doorway robot room - object
  )

  (:predicates
    (at ?r - robot ?ro - room)
    (connected ?ro1 - room ?ro2 - room ?d - doorway)
  )

  (:action move
    :parameters (?r - robot ?from - room ?to - room ?d - doorway)
    :precondition (and (at ?r ?from) (connected ?from ?to ?d))
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )

)