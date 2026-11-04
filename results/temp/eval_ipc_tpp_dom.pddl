(define (domain TPP-Propositional)
  (:requirements :strips :typing)

  (:types
    level locatable place - object
    depot market - place
    goods truck - locatable
  )

  (:predicates
    (loaded ?g - object ?t - object ?l - object)
    (ready-to-load ?g - object ?m - object ?l - object)
    (stored ?g - object ?l - object)
    (on-sale ?g - object ?m - object ?l - object)
    (next ?l1 - object ?l2 - object)
    (at ?t - object ?p - object)
    (connected ?p1 - object ?p2 - object)
  )

  (:action drive
    :parameters (?t - truck ?from - place ?to - place)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (not (at ?t ?from)) (at ?t ?to))
  )

  (:action load
    :parameters (?g - goods ?t - truck ?m - market ?l1 - level ?l2 - level ?l3 - level ?l4 - level)
    :precondition (at ?t ?m)
    :effect (and (not (ready-to-load ?g ?m ?l1)) (loaded ?g ?t ?l2))
  )

  (:action unload
    :parameters (?g - goods ?t - truck ?d - depot ?l1 - level ?l2 - level ?l3 - level ?l4 - level)
    :precondition (and (at ?t ?d) (loaded ?g ?t ?l1) (next ?l1 ?l2))
    :effect (and (not (loaded ?g ?t ?l1)) (stored ?g ?l2))
  )

  (:action buy
    :parameters (?t - truck ?g - goods ?m - market ?l1 - level ?l2 - level ?l3 - level ?l4 - level)
    :precondition (and (at ?t ?m) (on-sale ?g ?m ?l1) (next ?l1 ?l2))
    :effect (and (not (on-sale ?g ?m ?l1)) (stored ?g ?l2))
  )

)