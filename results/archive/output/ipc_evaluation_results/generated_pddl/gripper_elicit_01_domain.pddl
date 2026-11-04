(define (domain robot_gripper_domain)
  (:requirements :strips :typing)

  (:types
    ball gripper robot room - object
  )

  (:predicates
    (at ?r - robot ?ro - room)
    (empty ?g - gripper)
    (holding ?g - gripper ?b - ball)
    (in ?b - ball ?ro - room)
  )

  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (at ?r ?from)
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )

  (:action pick
    :parameters (?r - robot ?g - gripper ?b - ball ?ro - room)
    :precondition (and (at ?r ?ro) (in ?b ?ro) (empty ?g))
    :effect (and (not (in ?b ?ro)) (not (empty ?g)) (holding ?g ?b))
  )

  (:action drop
    :parameters (?r - robot ?g - gripper ?b - ball ?ro - room)
    :precondition (and (at ?r ?ro) (holding ?g ?b))
    :effect (and (not (holding ?g ?b)) (in ?b ?ro) (empty ?g))
  )

)