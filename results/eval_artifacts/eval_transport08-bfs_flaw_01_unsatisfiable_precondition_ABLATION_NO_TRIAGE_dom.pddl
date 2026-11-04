(define (domain transport)
  (:requirements :strips :typing)

  (:types
    capacity-number locatable location target - object
    package vehicle - locatable
  )

  (:predicates
    (road ?l1 - object ?l2 - object)
    (at ?x - object ?v - object)
    (in ?x - object ?v - object)
    (capacity ?v - object ?s1 - object)
    (capacity-predecessor ?s1 - object ?s2 - object)
  )

  (:action drive
    :parameters (?v - vehicle ?l1 - location ?l2 - location)
    :precondition (and (at ?v ?l1) (road ?l1 ?l2))
    :effect (and (not (at ?v ?l1)) (at ?v ?l2))
  )

  (:action pick-up
    :parameters (?v - vehicle ?l - location ?p - package ?s1 - capacity-number ?s2 - capacity-number)
    :precondition (and (at ?v ?l) (at ?p ?l) (capacity-predecessor ?s1 ?s2) (capacity ?v ?s1))
    :effect (and (not (at ?p ?l)) (in ?p ?v) (capacity ?v ?s2) (not (capacity ?v ?s1)))
  )

  (:action drop
    :parameters (?v - vehicle ?l - location ?p - package ?s1 - capacity-number ?s2 - capacity-number)
    :precondition (and (at ?v ?l) (in ?p ?v) (capacity-predecessor ?s1 ?s2) (capacity ?v ?s1))
    :effect (and (not (in ?p ?v)) (at ?p ?l) (capacity ?v ?s2) (not (capacity ?v ?s1)))
  )

)