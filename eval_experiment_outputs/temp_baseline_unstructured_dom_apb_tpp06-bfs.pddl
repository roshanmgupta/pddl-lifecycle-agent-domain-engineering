(define (domain tpp06-bfs)
  (:requirements :strips :typing)
  (:types
    place locatable level - object
    depot market - place
    truck goods - locatable
  )
  (:predicates
    (connected ?p1 ?p2 - place)
    (next ?l1 ?l2 - level)
    (ready-to-load ?g - goods ?p - place ?l - level)
    (stored ?g - goods ?l - level)
    (loaded ?g - goods ?t - truck ?l - level)
    (on-sale ?g - goods ?p - place ?l - level)
    (at ?l - locatable ?p - place)
  )
  (:action drive
    :parameters (?t - truck ?from ?to - place)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (at ?t ?to) (not (at ?t ?from)))
  )
  (:action load
    :parameters (?g - goods ?t - truck ?m - market ?e ?g1 - level ?d ?f - level)
    :precondition (and (at ?t ?m) (loaded ?g ?t ?f) (ready-to-load ?g ?m ?e) (next ?e ?d) (next ?g1 ?f))
    :effect (and (loaded ?g ?t ?g1) (ready-to-load ?g ?m ?d) (not (loaded ?g ?t ?f)) (not (ready-to-load ?g ?m ?e)))
  )
  (:action unload
    :parameters (?g - goods ?t - truck ?d - depot ?e ?d1 - level ?g1 ?f - level)
    :precondition (and (at ?t ?d) (loaded ?g ?t ?e) (stored ?g ?f) (next ?e ?d1) (next ?g1 ?f))
    :effect (and (loaded ?g ?t ?d1) (stored ?g ?g1) (not (loaded ?g ?t ?e)) (not (stored ?g ?f)))
  )
  (:action buy
    :parameters (?g - goods ?t - truck ?m - market ?e ?d - level ?g1 ?f - level)
    :precondition (and (at ?t ?m) (on-sale ?g ?m ?e) (ready-to-load ?g ?m ?f) (next ?e ?d) (next ?g1 ?f))
    :effect (and (on-sale ?g ?m ?d) (ready-to-load ?g ?m ?g1) (not (on-sale ?g ?m ?e)) (not (ready-to-load ?g ?m ?f)))
  )
)