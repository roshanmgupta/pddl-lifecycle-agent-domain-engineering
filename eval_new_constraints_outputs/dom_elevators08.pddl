(define (domain elevators08)
  (:requirements :strips :typing)

  (:types
    count elevator floor passenger - object
    fast-elevator slow-elevator - elevator
  )

  (:predicates
    (next-to ?x - floor ?y - floor)
    (above ?x - floor ?y - floor)
    (at ?e - object ?f - floor)
    (has-passengers ?e - elevator ?n - object)
    (can-hold ?e - elevator ?n - object)
    (reachable ?e - elevator ?f - floor)
    (at-passenger ?p - passenger ?f - floor)
  )

  (:action move_elevator
    :parameters (?e - elevator ?from - floor ?to - floor)
    :precondition (and (at ?e ?from) (reachable ?e ?to))
    :effect (and (at ?e ?to) (not (at ?e ?from)))
  )

  (:action load_passenger
    :parameters (?e - elevator ?p - passenger ?f - floor ?m - object ?n - object)
    :precondition (and (at ?p ?f) (at ?e ?f) (has-passengers ?e ?n) (can-hold ?e ?m))
    :effect (and (not (at ?p ?f)) (has-passengers ?e ?n) (can-hold ?e ?m))
  )

  (:action unload_passenger
    :parameters (?e - elevator ?p - passenger ?f - floor ?n - object)
    :precondition (and (at ?e ?f) (has-passengers ?e ?n))
    :effect (and (at ?p ?f) (not (has-passengers ?e ?n)))
  )

)