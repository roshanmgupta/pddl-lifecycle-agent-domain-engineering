(define (domain nomystery11-bfs)
  (:requirements :strips :typing)
  (:types
    locatable - object
    package truck - locatable
    location fuellevel - object
  )
  (:predicates
    (at ?l - locatable ?loc - location)
    (in ?p - package ?t - truck)
    (connected ?from - location ?to - location)
    (fuel-cost ?cost - fuellevel ?from - location ?to - location)
    (fuel-level ?t - truck ?level - fuellevel)
    (sum ?a ?b ?c - fuellevel)
  )
  (:action load
    :parameters (?p - package ?t - truck ?loc - location)
    :precondition (and (at ?t ?loc) (at ?p ?loc))
    :effect (and (in ?p ?t) (not (at ?p ?loc)))
  )
  (:action unload
    :parameters (?p - package ?t - truck ?loc - location)
    :precondition (and (at ?t ?loc) (in ?p ?t))
    :effect (and (at ?p ?loc) (not (in ?p ?t)))
  )
  (:action drive
    :parameters (?t - truck ?from - location ?to - location ?cost - fuellevel ?old-level - fuellevel ?new-level - fuellevel)
    :precondition (and (connected ?from ?to)
                       (fuel-cost ?cost ?from ?to)
                       (fuel-level ?t ?old-level)
                       (sum ?new-level ?cost ?old-level)
                       (at ?t ?from))
    :effect (and (at ?t ?to)
                 (not (at ?t ?from))
                 (fuel-level ?t ?new-level)
                 (not (fuel-level ?t ?old-level)))
  )
)