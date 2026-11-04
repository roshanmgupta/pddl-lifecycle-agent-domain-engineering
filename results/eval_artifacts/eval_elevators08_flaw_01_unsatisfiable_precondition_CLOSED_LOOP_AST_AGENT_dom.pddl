(define (domain elevators-sequencedstrips)
  (:requirements :typing)

  (:types
    count elevator passenger - object
    fast-elevator slow-elevator - elevator
  )

  (:predicates
    (passenger-at ?person - object ?floor - object)
    (boarded ?person - object ?lift - object)
    (lift-at ?lift - object ?floor - object)
    (reachable-floor ?lift - object ?floor - object)
    (above ?floor1 - object ?floor2 - object)
    (passengers ?lift - object ?n - object)
    (can-hold ?lift - object ?n - object)
    (next ?n1 - object ?n2 - object)
  )

  (:action move-up-slow
    :parameters (?lift - slow-elevator ?f1 - count ?f2 - count)
    :precondition (and (lift-at ?lift ?f1) (above ?f1 ?f2) (reachable-floor ?lift ?f2))
    :effect (and (lift-at ?lift ?f2) (not (lift-at ?lift ?f1)))
  )

  (:action move-down-slow
    :parameters (?lift - slow-elevator ?f1 - count ?f2 - count)
    :precondition (and (lift-at ?lift ?f1) (above ?f2 ?f1) (reachable-floor ?lift ?f2))
    :effect (and (lift-at ?lift ?f2) (not (lift-at ?lift ?f1)))
  )

  (:action move-up-fast
    :parameters (?lift - fast-elevator ?f1 - count ?f2 - count)
    :precondition (and (lift-at ?lift ?f1) (above ?f1 ?f2) (reachable-floor ?lift ?f2))
    :effect (and (lift-at ?lift ?f2) (not (lift-at ?lift ?f1)))
  )

  (:action move-down-fast
    :parameters (?lift - fast-elevator ?f1 - count ?f2 - count)
    :precondition (and (lift-at ?lift ?f1) (above ?f2 ?f1) (reachable-floor ?lift ?f2))
    :effect (and (lift-at ?lift ?f2) (not (lift-at ?lift ?f1)))
  )

  (:action board
    :parameters (?p - passenger ?lift - elevator ?f - count ?n1 - count ?n2 - count)
    :precondition (and (lift-at ?lift ?f) (passenger-at ?p ?f) (passengers ?lift ?n1) (next ?n1 ?n2) (can-hold ?lift ?n2))
    :effect (and (not (passenger-at ?p ?f)) (boarded ?p ?lift) (not (passengers ?lift ?n1)) (passengers ?lift ?n2))
  )

  (:action leave
    :parameters (?p - passenger ?lift - elevator ?f - count ?n1 - count ?n2 - count)
    :precondition (and (lift-at ?lift ?f) (boarded ?p ?lift) (passengers ?lift ?n1) (next ?n2 ?n1))
    :effect (and (passenger-at ?p ?f) (not (boarded ?p ?lift)) (not (passengers ?lift ?n1)) (passengers ?lift ?n2))
  )

)