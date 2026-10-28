(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?r - robot ?x - room)
    (at ?o - object ?x - room)
    (free ?r - robot ?g - gripper)
    (carry ?r - robot ?o - object ?g - gripper)
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

  (:action cooperative_transfer
    :parameters (?r1 - robot ?r2 - robot ?obj - object ?g1 - gripper ?g2 - gripper ?room - room)
    :precondition (and (at-robby ?r1 ?room) (at-robby ?r2 ?room) (carry ?r1 ?obj ?g1) (free ?r2 ?g2))
    :effect (and (carry ?r2 ?obj ?g2) (free ?r1 ?g1) (not (carry ?r1 ?obj ?g1)) (not (free ?r2 ?g2)))
  )

)