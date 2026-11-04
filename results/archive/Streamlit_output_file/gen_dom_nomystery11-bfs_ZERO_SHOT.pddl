(define (domain logistics)
  (:requirements :strips :typing :fluents)
  (:types
    location locatable package truck fuellevel - object
  )
  (:predicates
    (at ?x - locatable ?y - location)
    (in ?x - package ?y - truck)
    (connected ?x - location ?y - location)
    (fuel-cost ?x - fuellevel ?y - location ?z - location)
    (has-fuel ?x - truck ?y - fuellevel)
    (sum ?x - fuellevel ?y - fuellevel ?z - fuellevel)
  )
  (:action load
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (at ?p ?l))
    :effect (and (in ?p ?t) (not (at ?p ?l)))
  )
  (:action unload
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at ?t ?l) (in ?p ?t))
    :effect (and (at ?p ?l) (not (in ?p ?t)))
  )
  (:action drive
    :parameters (?t - truck ?from - location ?to - location ?cost - fuellevel ?current - fuellevel ?new - fuellevel)
    :precondition (and (connected ?from ?to) (fuel-cost ?cost ?from ?to) (has-fuel ?t ?current) (sum ?new ?cost ?current) (at ?t ?from))
    :effect (and (at ?t ?to) (not (at ?t ?from)) (has-fuel ?t ?new) (not (has-fuel ?t ?current)))
  )
)