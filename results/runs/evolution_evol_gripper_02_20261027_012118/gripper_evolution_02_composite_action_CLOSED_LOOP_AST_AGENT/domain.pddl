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
    (ready ?r - robot)
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

  (:action prepare
    :parameters (?r - robot)
    :precondition (and)
    :effect (ready ?r)
  )

  (:action move_prepared
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (and (at-robby ?r ?from) (ready ?r))
    :effect (and (at-robby ?r ?to) (not (at-robby ?r ?from)))
  )

  (:action pick_prepared
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (at ?obj ?room) (at-robby ?r ?room) (free ?r ?g) (ready ?r))
    :effect (and (carry ?r ?obj ?g) (not (at ?obj ?room)) (not (free ?r ?g)))
  )

  (:action drop_prepared
    :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
    :precondition (and (carry ?r ?obj ?g) (at-robby ?r ?room) (ready ?r))
    :effect (and (at ?obj ?room) (free ?r ?g) (not (carry ?r ?obj ?g)))
  )

)