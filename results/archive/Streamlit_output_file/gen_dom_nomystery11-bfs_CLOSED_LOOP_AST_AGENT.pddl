(define (domain transport-strips)
  (:requirements :strips :typing)

  (:types
    fuellevel locatable location - object
    package truck - locatable
  )

  (:predicates
    (at ?a - locatable ?c - location)
    (in ?p - package ?t - truck)
    (connected ?b - location ?c - location)
    (fuel ?t - truck ?f - fuellevel)
    (fuelcost ?e - fuellevel ?b - location ?c - location)
    (sum ?x1 - fuellevel ?x2 - fuellevel ?x3 - fuellevel)
  )

  (:action load_package
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (at ?p ?l))
    :effect (and (in ?p ?t) (not (at ?p ?l)))
  )

  (:action unload_package
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (in ?p ?t))
    :effect (and (at ?p ?l) (not (in ?p ?t)))
  )

  (:action drive_truck
    :parameters (?t - truck ?src - location ?dst - location ?e - fuellevel ?d - fuellevel)
    :precondition (and (connected ?src ?dst) (at ?t ?src))
    :effect (and (at ?t ?dst) (not (at ?t ?src)))
  )

)