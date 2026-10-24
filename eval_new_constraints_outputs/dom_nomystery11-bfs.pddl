(define (domain nomystery11-bfs)
  (:requirements :strips :typing)

  (:types
    fuellevel location package truck - object
  )

  (:predicates
    (connected ?x - location ?y - location)
    (fuel-cost ?from - fuellevel ?to - location)
    (at ?p - object ?l - location)
    (has-fuel ?t - truck ?f - fuellevel)
  )

  (:action move_truck
    :parameters (?t - truck ?from - location ?to - location)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (at ?t ?to) (not (at ?t ?from)))
  )

  (:action load_package
    :parameters (?t - truck ?p - package ?l - location)
    :precondition (and (at ?t ?l) (at ?p ?l))
    :effect (not (at ?p ?l))
  )

  (:action unload_package
    :parameters (?t - truck ?p - package ?l - location)
    :precondition (and (at ?t ?l) (not (at ?p ?l)))
    :effect (at ?p ?l)
  )

)