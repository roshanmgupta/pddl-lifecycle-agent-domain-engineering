(define (domain transport-strips)
  (:requirements :typing)

  (:types
    fuellevel locatable location - object
    package truck - locatable
  )

  (:predicates
    (connected ?l1 - object ?l2 - object)
    (at ?o - object ?l - object)
    (in ?p - object ?t - object)
    (fuel ?t - object ?level - object)
    (fuelcost ?level - object ?l1 - object ?l2 - object)
    (sum ?a - object ?b - object ?c - object)
  )

  (:action LOAD
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (at ?p ?l))
    :effect (and (not (at ?p ?l)) (in ?p ?t))
  )

  (:action UNLOAD
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (in ?p ?t))
    :effect (and (not (in ?p ?t)) (at ?p ?l))
  )

  (:action DRIVE
    :parameters (?t - truck ?l1 - location ?l2 - location ?fuelpost - fuellevel ?fueldelta - fuellevel ?fuelpre - fuellevel)
    :precondition (and (connected ?l1 ?l2) (fuelcost ?fueldelta ?l1 ?l2) (fuel ?t ?fuelpre) (sum ?fuelpost ?fueldelta ?fuelpre) (at ?t ?l1))
    :effect (and (not (at ?t ?l1)) (at ?t ?l2) (not (fuel ?t ?fuelpre)) (fuel ?t ?fuelpost))
  )

)