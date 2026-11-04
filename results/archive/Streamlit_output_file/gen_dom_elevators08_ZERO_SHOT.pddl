(define (domain elevator-domain)
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
    (at-passenger ?p - passenger ?c - count)
    (boarded ?p - passenger ?e - elevator)
    (passengers ?e - elevator ?d - count)
    (reachable ?e - elevator ?c - count)
    (next ?d - count ?e - count)
    (can-hold ?e - elevator ?c - count)
    (above ?b - count ?c - count)
  )
  
  (:action move-slow-down
    :parameters (?e - slow-elevator ?b - count ?c - count)
    :precondition (and (at-elevator ?e ?b) (above ?b ?c) (reachable ?e ?c))
    :effect (and (at-elevator ?e ?c) (not (at-elevator ?e ?b)))
  )
  
  (:action move-slow-up
    :parameters (?e - slow-elevator ?b - count ?c - count)
    :precondition (and (at-elevator ?e ?b) (above ?c ?b) (reachable ?e ?c))
    :effect (and (at-elevator ?e ?c) (not (at-elevator ?e ?b)))
  )
  
  (:action move-fast-down
    :parameters (?e - fast-elevator ?b - count ?c - count)
    :precondition (and (at-elevator ?e ?b) (above ?b ?c) (reachable ?e ?c))
    :effect (and (at-elevator ?e ?c) (not (at-elevator ?e ?b)))
  )
  
  (:action move-fast-up
    :parameters (?e - fast-elevator ?b - count ?c - count)
    :precondition (and (at-elevator ?e ?b) (above ?c ?b) (reachable ?e ?c))
    :effect (and (at-elevator ?e ?c) (not (at-elevator ?e ?b)))
  )
  
  (:action board
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e-count - count)
    :precondition (and (at-elevator ?e ?c) (at-passenger ?p ?c) (passengers ?e ?d) 
                       (next ?d ?e-count) (can-hold ?e ?e-count))
    :effect (and (boarded ?p ?e) (passengers ?e ?e-count) 
                 (not (at-passenger ?p ?c)) (not (passengers ?e ?d)))
  )
  
  (:action leave
    :parameters (?p - passenger ?e - elevator ?c - count ?d - count ?e-count - count)
    :precondition (and (at-elevator ?e ?c) (boarded ?p ?e) (passengers ?e ?d) (next ?e-count ?d))
    :effect (and (at-passenger ?p ?c) (passengers ?e ?e-count) 
                 (not (boarded ?p ?e)) (not (passengers ?e ?d)))
  )
)