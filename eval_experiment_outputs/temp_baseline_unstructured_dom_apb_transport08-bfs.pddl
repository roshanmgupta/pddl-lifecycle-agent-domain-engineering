(define (domain transport)
  (:requirements :strips :typing)
  (:types
    location - object
    vehicle - locatable
    package - locatable
    locatable - object
    capacity-number - object
  )
  (:predicates
    (at ?x - locatable ?y - location)
    (road ?from - location ?to - location)
    (capacity ?v - vehicle ?c - capacity-number)
    (capacity-predecessor ?c1 - capacity-number ?c2 - capacity-number)
    (in ?p - package ?v - vehicle)
  )
  (:action drive
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and 
                   (at ?v ?from)
                   (road ?from ?to)
                  )
    :effect (and 
              (not (at ?v ?from))
              (at ?v ?to)
            )
  )
  (:action pick-up
    :parameters (?v - vehicle ?p - package ?loc - location ?new-cap - capacity-number ?old-cap - capacity-number)
    :precondition (and 
                   (at ?v ?loc)
                   (at ?p ?loc)
                   (capacity ?v ?old-cap)
                   (capacity-predecessor ?new-cap ?old-cap)
                  )
    :effect (and 
              (not (at ?p ?loc))
              (not (capacity ?v ?old-cap))
              (in ?p ?v)
              (capacity ?v ?new-cap)
            )
  )
  (:action drop
    :parameters (?v - vehicle ?p - package ?loc - location ?new-cap - capacity-number ?old-cap - capacity-number)
    :precondition (and 
                   (at ?v ?loc)
                   (in ?p ?v)
                   (capacity ?v ?old-cap)
                   (capacity-predecessor ?old-cap ?new-cap)
                  )
    :effect (and 
              (not (in ?p ?v))
              (not (capacity ?v ?old-cap))
              (at ?p ?loc)
              (capacity ?v ?new-cap)
            )
  )
)