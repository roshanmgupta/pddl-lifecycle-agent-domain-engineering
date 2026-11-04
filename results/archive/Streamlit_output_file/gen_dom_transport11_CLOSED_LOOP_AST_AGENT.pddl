(define (domain transport)
  (:requirements :strips :typing)

  (:types
    capacity-number locatable location package vehicle - object
  )

  (:predicates
    (at ?a - object ?b - location)
    (capacity ?a - vehicle ?e - capacity-number)
    (capacity-predecessor ?d - capacity-number ?e - capacity-number)
    (road ?b - location ?c - location)
    (in ?c - package ?a - vehicle)
  )

  (:action drive_vehicle
    :parameters (?a - vehicle ?b - location ?c - location)
    :precondition (and (at ?a ?b) (road ?b ?c))
    :effect (and (at ?a ?c) (not (at ?a ?b)))
  )

  (:action pick_up_package
    :parameters (?a - vehicle ?b - location ?c - package ?e - capacity-number ?d - capacity-number)
    :precondition (and (at ?a ?b) (at ?c ?b) (capacity-predecessor ?d ?e) (capacity ?a ?e))
    :effect (and (in ?c ?a) (capacity ?a ?d) (not (at ?c ?b)) (not (capacity ?a ?e)))
  )

  (:action drop_package
    :parameters (?a - vehicle ?b - location ?c - package ?d - capacity-number ?e - capacity-number)
    :precondition (and (at ?a ?b) (at ?c ?b) (capacity-predecessor ?d ?e) (capacity ?a ?d))
    :effect (and (at ?c ?b) (capacity ?a ?e) (not (in ?c ?a)) (not (capacity ?a ?d)))
  )

)