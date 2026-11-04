(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?r - object ?x - object)
    (at ?o - object ?x - object)
    (free ?r - object ?g - object)
    (carry ?r - object ?o - object ?g - object)
  )

  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at-robby ?r ?from)
    :effect (and (at-robby ?r ?to) (not (at-robby ?r ?from)))
  )

  (:action pick
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (at ?obj ?room) (at-robby ?r ?room) (free ?r ?g))
    :effect (and (carry ?r ?obj ?g) (not (at ?obj ?room)) (not (free ?r ?g)))
  )

  (:action drop
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (carry ?r ?obj ?g) (at-robby ?r ?room))
    :effect (and (at ?obj ?room) (free ?r ?g) (not (carry ?r ?obj ?g)))
  )

)