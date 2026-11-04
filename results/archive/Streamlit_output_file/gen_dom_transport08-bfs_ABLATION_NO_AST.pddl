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
    (capacity-predecessor ?c1 ?c2 - capacity-number)
    (road ?from ?to - location)
    (at ?obj - locatable ?loc - location)
    (in ?pkg - package ?veh - vehicle)
    (capacity ?veh - vehicle ?cap - capacity-number)
  )
  (:action drive
    :parameters (?v - vehicle ?from ?to - location)
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
    :parameters (?v - vehicle ?p - package ?loc - location ?new-cap ?old-cap - capacity-number)
    :precondition (and
                   (at ?v ?loc)
                   (at ?p ?loc)
                   (capacity-predecessor ?new-cap ?old-cap)
                   (capacity ?v ?old-cap)
                 )
    :effect (and
              (not (at ?p ?loc))
              (not (capacity ?v ?old-cap))
              (in ?p ?v)
              (capacity ?v ?new-cap)
            )
  )
  (:action drop
    :parameters (?v - vehicle ?p - package ?loc - location ?old-cap ?new-cap - capacity-number)
    :precondition (and
                   (at ?v ?loc)
                   (in ?p ?v)
                   (capacity-predecessor ?old-cap ?new-cap)
                   (capacity ?v ?old-cap)
                 )
    :effect (and
              (not (in ?p ?v))
              (not (capacity ?v ?old-cap))
              (at ?p ?loc)
              (capacity ?v ?new-cap)
            )
  )
)