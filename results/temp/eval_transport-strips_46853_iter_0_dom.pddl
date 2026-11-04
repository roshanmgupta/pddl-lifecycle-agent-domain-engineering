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
    :precondition (and (at ?p ?l) (at ?t ?l))
    :effect (and (in ?p ?t) (not (at ?p ?l)))
  )

  (:action UNLOAD
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (in ?p ?t))
    :effect (and (at ?p ?l) (not (in ?p ?t)))
  )

  (:action DRIVE
    :parameters (?t - truck ?l1 - location ?l2 - location ?fuelpost - fuellevel ?fueldelta - fuellevel ?fuelpre - fuellevel)
    :precondition (and (connected ?l1 ?l2) (fuelcost ?fueldelta ?l1 ?l2) (fuel ?t ?fuelpre) (sum ?fuelpost ?fueldelta ?fuelpre) (at ?t ?l1))
    :effect (and (at ?t ?l2) (fuel ?t ?fuelpost) (not (at ?t ?l1)) (not (fuel ?t ?fuelpre)))
  )

)