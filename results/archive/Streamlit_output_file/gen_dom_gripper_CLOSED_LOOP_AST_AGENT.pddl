(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?r - object ?loc - room)
    (carrying ?r - robot ?b - object ?g - gripper)
    (free ?r - robot ?g - gripper)
    (at ?b - object ?loc - room)
  )

  (:action move_robot
    :parameters (?r - object ?from - room ?to - room)
    :precondition (at-robby ?r ?from)
    :effect (and (at-robby ?r ?to) (not (at-robby ?r ?from)))
  )

  (:action pick_object
    :parameters (?r - robot ?b - object ?g - gripper ?loc - room)
    :precondition (and (at ?b ?loc) (at-robby ?r ?loc) (free ?r ?g))
    :effect (and (carrying ?r ?b ?g) (not (at ?b ?loc)) (not (free ?r ?g)))
  )

  (:action drop_object
    :parameters (?r - robot ?b - object ?g - gripper ?loc - room)
    :precondition (and (carrying ?r ?b ?g) (at-robby ?r ?loc))
    :effect (and (at ?b ?loc) (not (carrying ?r ?b ?g)) (free ?r ?g))
  )

)