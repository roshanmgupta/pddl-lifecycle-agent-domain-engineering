(define (domain transport)
  (:requirements :strips :typing)

  (:types
    capacity-number locatable location - object
    package vehicle - locatable
  )

  (:predicates
    (at ?x - locatable ?y - location)
    (road ?from - location ?to - location)
    (capacity-predecessor ?prev - capacity-number ?next - capacity-number)
    (capacity ?v - vehicle ?c - capacity-number)
    (in ?p - package ?v - vehicle)
  )

  (:action drive
    :parameters (?a - vehicle ?b - location ?c - location)
    :precondition (and (at ?a ?b) (road ?b ?c))
    :effect (and (not (at ?a ?b)) (at ?a ?c))
  )

  (:action pick_up
    :parameters (?a - vehicle ?b - location ?c - package ?d - capacity-number ?e - capacity-number)
    :precondition (and (at ?a ?b) (at ?c ?b) (capacity-predecessor ?d ?e) (capacity ?a ?e))
    :effect (and (not (at ?c ?b)) (in ?c ?a) (not (capacity ?a ?e)) (capacity ?a ?d))
  )

  (:action drop
    :parameters (?a - vehicle ?b - location ?c - package ?d - capacity-number ?e - capacity-number)
    :precondition (and (at ?a ?b) (in ?c ?a) (capacity-predecessor ?d ?e) (capacity ?a ?d))
    :effect (and (not (in ?c ?a)) (at ?c ?b) (not (capacity ?a ?d)) (capacity ?a ?e))
  )

)