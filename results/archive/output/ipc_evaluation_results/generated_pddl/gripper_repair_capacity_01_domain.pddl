(define (domain gripper_domain)
  (:requirements :strips :typing)

  (:types
    gripper object - object
  )

  (:predicates
    (free ?g - gripper)
    (holding ?g - gripper ?o - object)
  )

  (:action pick
    :parameters (?g - gripper ?o - object)
    :precondition (free ?g)
    :effect (and (not (free ?g)) (holding ?g ?o))
  )

)