(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?r - robot ?l - room)
    (free ?r - robot ?g - gripper)
    (carrying ?r - robot ?o - object ?g - gripper)
    (at ?o - object ?l - room)
  )

  (:action move_robot
    :parameters (?a - robot ?b - room ?c - room)
    :precondition (at-robby ?a ?b)
    :effect (and (not (at-robby ?a ?b)) (at-robby ?a ?c))
  )

  (:action pick_object
    :parameters (?a - robot ?b - object ?d - gripper ?c - room)
    :precondition (and (at ?b ?c) (at-robby ?a ?c) (free ?a ?d))
    :effect (and (not (at ?b ?c)) (not (free ?a ?d)) (carrying ?a ?b ?d))
  )

  (:action drop_object
    :parameters (?a - robot ?b - object ?d - gripper ?c - room)
    :precondition (and (carrying ?a ?b ?d) (at-robby ?a ?c))
    :effect (and (not (carrying ?a ?b ?d)) (at ?b ?c) (free ?a ?d))
  )

)