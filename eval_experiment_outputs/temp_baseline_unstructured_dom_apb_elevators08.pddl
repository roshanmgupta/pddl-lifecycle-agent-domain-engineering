(define (domain elevator)
  (:requirements :strips :typing :action-costs)
  (:types
    count - object
    passenger - object
    elevator - object
    slow-elevator - elevator
    fast-elevator - elevator
  )
  (:predicates
    (at-elevator ?e - elevator ?c - count)
    (at-floor ?p - passenger ?c - count)
    (boarded ?p - passenger ?e - elevator)
    (passengers ?e - elevator ?n - count)
    (reachable ?e - elevator ?c - count)
    (can-hold ?e - elevator ?n - count)
    (next ?n1 - count ?n2 - count)
    (above ?c1 - count ?c2 - count)
  )
  (:action move-slow-down
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and
                   (at-elevator ?e ?from)
                   (above ?from ?to)
                   (reachable ?e ?to)
                  )
    :effect (and
              (not (at-elevator ?e ?from))
              (at-elevator ?e ?to)
             )
  )
  (:action move-slow-up
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and
                   (at-elevator ?e ?from)
                   (above ?to ?from)
                   (reachable ?e ?to)
                  )
    :effect (and
              (not (at-elevator ?e ?from))
              (at-elevator ?e ?to)
             )
  )
  (:action move-fast-down
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and
                   (at-elevator ?e ?from)
                   (above ?from ?to)
                   (reachable ?e ?to)
                  )
    :effect (and
              (not (at-elevator ?e ?from))
              (at-elevator ?e ?to)
             )
  )
  (:action move-fast-up
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and
                   (at-elevator ?e ?from)
                   (above ?to ?from)
                   (reachable ?e ?to)
                  )
    :effect (and
              (not (at-elevator ?e ?from))
              (at-elevator ?e ?to)
             )
  )
  (:action board
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and
                   (at-elevator ?e ?c)
                   (at-floor ?p ?c)
                   (passengers ?e ?d)
                   (next ?d ?e_count)
                   (can-hold ?e ?e_count)
                  )
    :effect (and
              (not (at-floor ?p ?c))
              (boarded ?p ?e)
              (not (passengers ?e ?d))
              (passengers ?e ?e_count)
             )
  )
  (:action leave
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and
                   (at-elevator ?e ?c)
                   (boarded ?p ?e)
                   (passengers ?e ?d)
                   (next ?e_count ?d)
                  )
    :effect (and
              (at-floor ?p ?c)
              (not (boarded ?p ?e))
              (not (passengers ?e ?d))
              (passengers ?e ?e_count)
             )
  )
)