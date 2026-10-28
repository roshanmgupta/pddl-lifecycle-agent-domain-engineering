(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?o - object ?x - object)
    (free ?r - robot ?g - gripper)
    (carry ?r - robot ?o - object ?g - gripper)
  )

  (:action move
    :parameters (?r - robot ?from - object ?to - room)
    :precondition (at-robby ?r ?from)
    :effect (and (at-robby ?r ?to) (not (at-robby ?r ?from)))
  )

  (:action pick
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (at-robby ?obj ?room) (at-robby ?r ?room) (free ?r ?g))
    :effect (and (carry ?r ?obj ?g) (not (at-robby ?obj ?room)) (not (free ?r ?g)))
  )

  (:action drop
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (carry ?r ?obj ?g) (at-robby ?r ?room))
    :effect (and (at-robby ?obj ?room) (free ?r ?g) (not (carry ?r ?obj ?g)))
  )

  (:action cooperative_transfer
    :parameters (?a - robot ?b - robot ?c - object ?d - gripper ?e - gripper ?f - room)
    :precondition (and (at-robby ?a ?f) (at-robby ?b ?f) (carry ?a ?c ?d) (free ?b ?e))
    :effect (and (carry ?b ?c ?e) (free ?a ?d) (not (carry ?a ?c ?d)) (not (free ?b ?e)))
  )

)