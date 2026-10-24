(define (domain elevators-sequencedstrips)
  (:requirements :strips :typing)
  (:types 
    count - object
    passenger - object
    elevator - object
    fast-elevator - elevator
    slow-elevator - elevator
  )

  (:predicates 
    (next ?x - count ?y - count)
    (above ?x - count ?y - count)
    (lift-at ?e - elevator ?c - count)
    (passengers ?e - elevator ?d - count)
    (can-hold ?e - elevator ?c - count)
    (reachable-floor ?e - elevator ?c - count)
    (passenger-at ?p - passenger ?c - count)
    (has-boarded ?p - passenger ?e - elevator)
  )

  (:action move-slow-elevator-up
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and 
      (lift-at ?e ?from) 
      (above ?from ?to) 
      (reachable-floor ?e ?to)
    )
    :effect (and 
      (lift-at ?e ?to) 
      (not (lift-at ?e ?from))
    )
  )

  (:action move-slow-elevator-down
    :parameters (?e - slow-elevator ?from - count ?to - count)
    :precondition (and 
      (lift-at ?e ?from) 
      (above ?from ?to) 
      (reachable-floor ?e ?to)
    )
    :effect (and 
      (lift-at ?e ?to) 
      (not (lift-at ?e ?from))
    )
  )

  (:action move-fast-elevator-up
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and 
      (lift-at ?e ?from) 
      (above ?from ?to) 
      (reachable-floor ?e ?to)
    )
    :effect (and 
      (lift-at ?e ?to) 
      (not (lift-at ?e ?from))
    )
  )

  (:action move-fast-elevator-down
    :parameters (?e - fast-elevator ?from - count ?to - count)
    :precondition (and 
      (lift-at ?e ?from) 
      (above ?from ?to) 
      (reachable-floor ?e ?to)
    )
    :effect (and 
      (lift-at ?e ?to) 
      (not (lift-at ?e ?from))
    )
  )

  (:action board-passenger
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e - count)
    :precondition (and 
      (lift-at ?e ?c) 
      (passenger-at ?p ?c) 
      (passengers ?e ?d) 
      (can-hold ?e ?e) 
      (next ?d ?e)
    )
    :effect (and 
      (has-boarded ?p ?e) 
      (passengers ?e ?e) 
      (not (passenger-at ?p ?c)) 
      (not (passengers ?e ?d))
    )
  )

  (:action leave-elevator
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e - count)
    :precondition (and 
      (lift-at ?e ?c) 
      (has-boarded ?p ?e) 
      (passengers ?e ?d) 
      (next ?d ?e)
    )
    :effect (and 
      (passenger-at ?p ?c) 
      (passengers ?e ?e) 
      (not (has-boarded ?p ?e)) 
      (not (passengers ?e ?d))
    )
  )
)