(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    object - object
    room - object
    robot - object
    gripper - object
  )
  (:predicates
    (at ?r - robot ?rm - room)
    (free ?r - robot ?g - gripper)
    (carrying ?r - robot ?o - object ?g - gripper)
    (object-at ?o - object ?rm - room)
  )
  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (and (at ?r ?from))
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )
  (:action pick
    :parameters (?r - robot ?o - object ?g - gripper ?rm - room)
    :precondition (and (object-at ?o ?rm) (at ?r ?rm) (free ?r ?g))
    :effect (and (not (object-at ?o ?rm)) (not (free ?r ?g)) (carrying ?r ?o ?g))
  )
  (:action drop
    :parameters (?r - robot ?o - object ?g - gripper ?rm - room)
    :precondition (and (carrying ?r ?o ?g) (at ?r ?rm))
    :effect (and (not (carrying ?r ?o ?g)) (object-at ?o ?rm) (free ?r ?g))
  )
)