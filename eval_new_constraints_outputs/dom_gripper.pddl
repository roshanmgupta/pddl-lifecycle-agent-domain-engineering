(define (domain gripper)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at ?b - object ?room - object)
    (free ?r - robot ?g - gripper)
  )

  (:action move_robot
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at ?r ?from)
    :effect (and (at ?r ?to) (not (at ?r ?from)))
  )

  (:action pick_up_ball
    :parameters (?r - robot ?b - object ?g - gripper ?room - object)
    :precondition (and (at ?r ?room) (at ?b ?room) (free ?r ?g))
    :effect (and (not (at ?b ?room)) (not (free ?r ?g)))
  )

  (:action drop_ball
    :parameters (?r - robot ?b - object ?g - gripper ?room - room)
    :precondition (and (not (free ?r ?g)) (at ?r ?room))
    :effect (and (at ?b ?room) (free ?r ?g))
  )

)