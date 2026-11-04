(define (domain elevators-sequencedstrips)
  (:requirements :strips :typing)

  (:types
    count elevator passenger - object
    fast-elevator slow-elevator - elevator
  )

  (:predicates
    (lift-at ?e - elevator ?c - count)
    (above ?c1 - count ?c2 - count)
    (reachable-floor ?e - elevator ?c - count)
    (passenger-at ?p - passenger ?c - count)
    (boarded ?p - passenger ?e - elevator)
    (passengers ?e - elevator ?c - count)
    (can-hold ?e - elevator ?c - count)
    (next ?c1 - count ?c2 - count)
  )

  (:action move_slow_elevator_down
    :parameters (?a - slow-elevator ?b - count ?c - count)
    :precondition (and (lift-at ?a ?b) (above ?c ?b) (reachable-floor ?a ?c))
    :effect (and (not (lift-at ?a ?b)) (lift-at ?a ?c))
  )

  (:action move_slow_elevator_up
    :parameters (?a - slow-elevator ?b - count ?c - count)
    :precondition (and (lift-at ?a ?b) (above ?b ?c) (reachable-floor ?a ?c))
    :effect (and (not (lift-at ?a ?b)) (lift-at ?a ?c))
  )

  (:action move_fast_elevator_down
    :parameters (?a - fast-elevator ?b - count ?c - count)
    :precondition (and (lift-at ?a ?b) (above ?c ?b) (reachable-floor ?a ?c))
    :effect (and (not (lift-at ?a ?b)) (lift-at ?a ?c))
  )

  (:action move_fast_elevator_up
    :parameters (?a - fast-elevator ?b - count ?c - count)
    :precondition (and (lift-at ?a ?b) (above ?b ?c) (reachable-floor ?a ?c))
    :effect (and (not (lift-at ?a ?b)) (lift-at ?a ?c))
  )

  (:action board_passenger
    :parameters (?a - passenger ?b - elevator ?c - count ?d - count ?e - count)
    :precondition (and (lift-at ?b ?c) (passenger-at ?a ?c) (passengers ?b ?d) (next ?d ?e) )
    :effect (and (not (passenger-at ?a ?c)) (not (passengers ?b ?d)) (boarded ?a ?b) (passengers ?b ?e))
  )

  (:action leave_passenger
    :parameters (?a - passenger ?b - elevator ?c - count ?d - count ?e - count)
    :precondition (and (lift-at ?b ?c) (boarded ?a ?b) (passengers ?b ?d) (next ?e ?d) )
    :effect (and (not (boarded ?a ?b)) (not (passengers ?b ?d)) (passenger-at ?a ?c) (passengers ?b ?e))
  )

)