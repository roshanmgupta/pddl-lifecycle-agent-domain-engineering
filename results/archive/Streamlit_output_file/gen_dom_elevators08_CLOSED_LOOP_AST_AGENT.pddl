(define (domain elevators-sequencedstrips)
  (:requirements :strips :typing)

  (:types
    count elevator passenger - object
    fast-elevator slow-elevator - elevator
  )

  (:predicates
    (lift-at ?e - elevator ?c - count)
    (passenger-at ?p - passenger ?c - count)
    (passengers ?e - elevator ?d - count)
    (can-hold ?e - elevator ?e_count - count)
    (passenger-boarded ?p - passenger ?e - elevator)
    (reachable-floor ?e - elevator ?c - count)
    (above ?c1 - count ?c2 - count)
    (next ?x1 - count ?x2 - count)
  )

  (:action move-slow-elevator-up
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and (lift-at ?e ?from) (above ?from ?to) (reachable-floor ?e ?to))
    :effect (and (lift-at ?e ?to) (not (lift-at ?e ?from)))
  )

  (:action move-slow-elevator-down
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and (lift-at ?e ?from) (above ?to ?from) (reachable-floor ?e ?to))
    :effect (and (lift-at ?e ?to) (not (lift-at ?e ?from)))
  )

  (:action move-fast-elevator-up
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and (lift-at ?e ?from) (above ?from ?to) (reachable-floor ?e ?to))
    :effect (and (lift-at ?e ?to) (not (lift-at ?e ?from)))
  )

  (:action move-fast-elevator-down
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and (lift-at ?e ?from) (above ?to ?from) (reachable-floor ?e ?to))
    :effect (and (lift-at ?e ?to) (not (lift-at ?e ?from)))
  )

  (:action board-passenger
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and (lift-at ?e ?c) (passenger-at ?p ?c) (passengers ?e ?d) (can-hold ?e ?e_count))
    :effect (and (passenger-boarded ?p ?e) (passengers ?e ?e_count) (not (passenger-at ?p ?c)) (not (passengers ?e ?d)))
  )

  (:action leave-elevator
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and (lift-at ?e ?c) (passenger-boarded ?p ?e) (passengers ?e ?d))
    :effect (and (passenger-at ?p ?c) (not (passenger-boarded ?p ?e)) (passengers ?e ?e_count) (not (passengers ?e ?d)))
  )

)