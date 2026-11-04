(define (domain transport08-bfs)
  (:requirements :strips :typing)

  (:types
    capacity-number locatable location package vehicle - object
  )

  (:predicates
    (at ?x - object ?loc - location)
    (has-capacity ?x - vehicle ?c - capacity-number)
    (at-road ?loc1 - location ?loc2 - location)
    (in ?p - package ?v - vehicle)
    (capacity-predecessor ?c1 - capacity-number ?c2 - capacity-number)
  )

  (:action drive_vehicle
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and (at ?v ?from) (at-road ?from ?to))
    :effect (and (at ?v ?to) (not (at ?v ?from)))
  )

  (:action pick_up_package
    :parameters (?p - package ?v - vehicle ?loc - location ?e - capacity-number ?d - capacity-number)
    :precondition (and (at ?v ?loc) (at ?p ?loc) (capacity-predecessor ?d ?e) (has-capacity ?v ?e))
    :effect (and (in ?p ?v) (has-capacity ?v ?d) (not (at ?p ?loc)) (not (has-capacity ?v ?e)))
  )

  (:action drop_package
    :parameters (?p - package ?v - vehicle ?loc - location ?d - capacity-number ?e - capacity-number)
    :precondition (and (at ?v ?loc) (in ?p ?v) (capacity-predecessor ?d ?e) (has-capacity ?v ?d))
    :effect (and (at ?p ?loc) (has-capacity ?v ?e) (not (in ?p ?v)) (not (has-capacity ?v ?d)))
  )

)