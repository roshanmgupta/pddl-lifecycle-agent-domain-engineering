(define (domain elevators-sequencedstrips)
  (:requirements :strips :typing)

  (:types
    count elevator passenger - object
    fast-elevator slow-elevator - elevator
  )

  (:predicates
    (lift-at ?e - elevator ?c - count)
    (reachable-floor ?x1 - elevator ?x2 - count)
    (has-passengers ?e - elevator ?d - count)
    (boarded ?p - passenger ?e - elevator)
    (next ?c1 - count ?c2 - count)
    (at ?e - object ?src - count)
    (reachable ?e - fast-elevator ?src - count ?dst - count)
    (next-to ?src - count ?dst - count)
    (can-hold ?e - elevator ?e_count - count)
    (above ?x1 - count ?x2 - count)
    (passengers ?x1 - elevator ?x2 - count)
    (passenger-at ?x1 - passenger ?x2 - count)
  )

  (:action move-slow-elevator-up
    :parameters (?e - slow-elevator ?src - count ?dst - count)
    :precondition (and (lift-at ?e ?src) (next ?src ?dst))
    :effect (and (lift-at ?e ?dst) (not (lift-at ?e ?src)))
  )

  (:action move-slow-elevator-down
    :parameters (?e - slow-elevator ?src - count ?dst - count)
    :precondition (and (lift-at ?e ?src) (next ?dst ?src))
    :effect (and (lift-at ?e ?dst) (not (lift-at ?e ?src)))
  )

  (:action move-fast-elevator-up
    :parameters (?e - fast-elevator ?src - count ?dst - count)
    :precondition (and (at ?e ?src) (reachable ?e ?src ?dst) (next-to ?src ?dst))
    :effect (and (at ?e ?dst) (not (at ?e ?src)))
  )

  (:action move-fast-elevator-down
    :parameters (?e - fast-elevator ?src - count ?dst - count)
    :precondition (and (at ?e ?src) (reachable ?e ?src ?dst) (next-to ?dst ?src))
    :effect (and (at ?e ?dst) (not (at ?e ?src)))
  )

  (:action board-passenger
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and (at ?e ?c) (at ?p ?c) (has-passengers ?e ?d) (next-to ?d ?e_count) (can-hold ?e ?e_count))
    :effect (and (boarded ?p ?e) (has-passengers ?e ?e_count) (not (at ?p ?c)) (not (has-passengers ?e ?d)))
  )

  (:action leave-elevator
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e_count - count)
    :precondition (and (at ?e ?c) (boarded ?p ?e) (has-passengers ?e ?d) (next-to ?d ?e_count))
    :effect (and (at ?p ?c) (not (boarded ?p ?e)) (has-passengers ?e ?e_count))
  )

)