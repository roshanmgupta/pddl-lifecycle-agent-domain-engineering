(define (domain gripper-strips)
  (:requirements :strips :typing)

  (:types
    gripper robot room - object
  )

  (:predicates
    (at-robby ?r - robot ?l - room)
    (free ?r - robot ?g - gripper)
    (at ?o - object ?l - room)
    (holding ?r - robot ?g - gripper ?o - object)
  )

  (:action move_robot
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at-robby ?r ?from)
    :effect (and (not (at-robby ?r ?from)) (at-robby ?r ?to))
  )

  (:action pick_object
    :parameters (?r - robot ?g - gripper ?o - object ?l - room)
    :precondition (and (at-robby ?r ?l) (free ?r ?g) (at ?o ?l))
    :effect (and (not (free ?r ?g)) (not (at ?o ?l)) (holding ?r ?g ?o))
  )

  (:action drop_object
    :parameters (?r - robot ?g - gripper ?o - object ?l - room)
    :precondition (and (at-robby ?r ?l) (holding ?r ?g ?o))
    :effect (and (free ?r ?g) (at ?o ?l) (not (holding ?r ?g ?o)))
  )

)