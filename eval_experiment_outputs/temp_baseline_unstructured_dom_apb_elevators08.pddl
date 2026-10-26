(define (domain elevators-sequencedstrips)
  (:requirements :strips :typing :negative-preconditions)
  (:types
    count - object
    passenger - object
    elevator - object
    slow-elevator - elevator
    fast-elevator - elevator
  )

  (:predicates
    (next ?a ?b - count)
    (above ?a ?b - count)
    (lift-at ?e - elevator ?f - count)
    (passengers ?e - elevator ?n - count)
    (can-hold ?e - elevator ?n - count)
    (reachable-floor ?e - elevator ?f - count)
    (passenger-at ?p - passenger ?f - count)
    (boarded ?p - passenger ?e - elevator)
  )

  (:action move-slow-down
    :parameters (?e - slow-elevator ?from ?to - count)
    :precondition (and
                   (lift-at ?e ?from)
                   (above ?from ?to)
                   (reachable-floor ?e ?to)
                 )
    :effect (and
              (not (lift-at ?e ?from))
              (lift-at ?e ?to)
            )
  )

  (:action move-slow-up
    :parameters (?e - slow-elevator ?from ?to - count)
    :precondition (and
                   (lift-at ?e ?from)
                   (above ?to ?from)
                   (reachable-floor ?e ?to)
                 )
    :effect (and
              (not (lift-at ?e ?from))
              (lift-at ?e ?to)
            )
  )

  (:action move-fast-down
    :parameters (?e - fast-elevator ?from ?to - count)
    :precondition (and
                   (lift-at ?e ?from)
                   (above ?from ?to)
                   (reachable-floor ?e ?to)
                 )
    :effect (and
              (not (lift-at ?e ?from))
              (lift-at ?e ?to)
            )
  )

  (:action move-fast-up
    :parameters (?e - fast-elevator ?from ?to - count)
    :precondition (and
                   (lift-at ?e ?from)
                   (above ?to ?from)
                   (reachable-floor ?e ?to)
                 )
    :effect (and
              (not (lift-at ?e ?from))
              (lift-at ?e ?to)
            )
  )

  (:action board
    :parameters (?p - passenger ?e - elevator ?f - count ?d ?e_count - count)
    :precondition (and
                   (lift-at ?e ?f)
                   (passenger-at ?p ?f)
                   (passengers ?e ?d)
                   (next ?d ?e_count)
                   (can-hold ?e ?e_count)
                 )
    :effect (and
              (not (passenger-at ?p ?f))
              (not (passengers ?e ?d))
              (boarded ?p ?e)
              (passengers ?e ?e_count)
            )
  )

  (:action leave
    :parameters (?p - passenger ?e - elevator ?f - count ?d ?e_count - count)
    :precondition (and
                   (lift-at ?e ?f)
                   (boarded ?p ?e)
                   (passengers ?e ?d)
                   (next ?e_count ?d)
                 )
    :effect (and
              (not (boarded ?p ?e))
              (not (passengers ?e ?d))
              (passenger-at ?p ?f)
              (passengers ?e ?e_count)
            )
  )
)