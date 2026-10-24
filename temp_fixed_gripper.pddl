(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    ball gripper robot room - object
  )

  (:predicates
    (at ?b - object ?loc - room)
    (carrying ?r - robot ?b - object ?g - gripper)
    (free ?r - robot ?g - gripper)
    (clear ?loc - room)
    (at-robby ?x1 - robot ?x2 - room)
  )

  (:action move_robot
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at-robby ?r ?from)
    :effect (and (at-robby ?r ?to) (not (at-robby ?r ?from)) (clear ?from))
  )

  (:action pick_object
    :parameters (?r - robot ?b - object ?g - gripper ?loc - room)
    :precondition (and (at ?b ?loc) (at-robby ?r ?loc) (free ?r ?g))
    :effect (and (carrying ?r ?b ?g) (not (at ?b ?loc)) (not (free ?r ?g)))
  )

  (:action drop_object
    :parameters (?r - robot ?b - object ?g - gripper ?loc - room)
    :precondition (and (carrying ?r ?b ?g) (at-robby ?r ?loc))
    :effect (and (at ?b ?loc) (free ?r ?g) (not (carrying ?r ?b ?g)))
  )

)