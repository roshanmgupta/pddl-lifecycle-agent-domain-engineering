(define (domain transport)
  (:requirements :strips :typing)
  (:types
    location - object
    vehicle - object
    package - object
    capacity-number - object
    locatable - object
  )
  (:predicates
    (at ?v - locatable ?l - location)
    (road ?from - location ?to - location)
    (in ?p - package ?v - vehicle)
    (capacity ?v - vehicle ?c - capacity-number)
    (capacity-predecessor ?c1 - capacity-number ?c2 - capacity-number)
  )
  (:action drive
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and (at ?v ?from) (road ?from ?to))
    :effect (and (at ?v ?to) (not (at ?v ?from)))
  )
  (:action pick-up
    :parameters (?v - vehicle ?l - location ?p - package ?e - capacity-number ?d - capacity-number)
    :precondition (and (at ?v ?l) (at ?p ?l) (capacity-predecessor ?d ?e) (capacity ?v ?e))
    :effect (and (in ?p ?v) (capacity ?v ?d) (not (at ?p ?l)) (not (capacity ?v ?e)))
  )
  (:action drop
    :parameters (?v - vehicle ?l - location ?p - package ?d - capacity-number ?e - capacity-number)
    :precondition (and (at ?v ?l) (in ?p ?v) (capacity-predecessor ?d ?e) (capacity ?v ?d))
    :effect (and (at ?p ?l) (capacity ?v ?e) (not (in ?p ?v)) (not (capacity ?v ?d)))
  )
)