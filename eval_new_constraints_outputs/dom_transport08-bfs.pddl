(define (domain transport08-bfs)
  (:requirements :strips :typing)

  (:types
    capacity-number location package vehicle - object
  )

  (:predicates
    (road ?from - location ?to - location)
    (at ?x - object ?loc - location)
    (has-capacity ?v - vehicle ?c - capacity-number)
    (capacity-predecessor ?c1 - capacity-number ?c2 - capacity-number)
    (loaded ?p - package ?v - vehicle)
  )

  (:action load_package
    :parameters (?p - package ?v - vehicle ?loc - location)
    :precondition (and (at ?p ?loc) (at ?v ?loc))
    :effect (and (not (at ?p ?loc)) (loaded ?p ?v))
  )

  (:action unload_package
    :parameters (?p - package ?v - vehicle ?loc - location)
    :precondition (and (loaded ?p ?v) (at ?v ?loc))
    :effect (and (at ?p ?loc) (not (loaded ?p ?v)))
  )

  (:action drive_vehicle
    :parameters (?v - vehicle ?from - location ?to - location)
    :precondition (and (at ?v ?from) (road ?from ?to))
    :effect (and (not (at ?v ?from)) (at ?v ?to))
  )

)