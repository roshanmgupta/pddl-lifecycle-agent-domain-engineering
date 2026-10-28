(define (domain robot-domain)
  (:requirements :strips :typing)
  (:types
    object
    robot - object
    room - object
    gripper - object
  )
  (:predicates
    (at ?r - robot ?l - room)
    (free ?r - robot ?g - gripper)
    (carrying ?r - robot ?o - object ?g - gripper)
    (object-at ?o - object ?l - room)
  )
  (:action move
    :parameters (?r - robot ?from - room ?to - room)
    :precondition (and (at ?r ?from))
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )
  (:action pick
    :parameters (?r - robot ?o - object ?g - gripper ?l - room)
    :precondition (and (object-at ?o ?l) (at ?r ?l) (free ?r ?g))
    :effect (and (not (object-at ?o ?l)) (not (free ?r ?g)) (carrying ?r ?o ?g))
  )
  (:action drop
    :parameters (?r - robot ?o - object ?g - gripper ?l - room)
    :precondition (and (carrying ?r ?o ?g) (at ?r ?l))
    :effect (and (not (carrying ?r ?o ?g)) (object-at ?o ?l) (free ?r ?g))
  )
)