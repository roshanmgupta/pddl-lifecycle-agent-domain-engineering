(define (domain TPP-Propositional)
  (:requirements :strips :typing)

  (:types
    level locatable place - object
    depot market - place
    goods truck - locatable
  )

  (:predicates
    (at ?x - locatable ?y - place)
    (next ?x - level ?y - level)
    (loaded ?g - goods ?t - truck ?l - level)
    (ready-to-load ?g - goods ?m - market ?l - object)
    (stored ?g - goods ?l - level)
    (on-sale ?g - goods ?m - market ?l - level)
    (connected ?from - place ?to - place)
  )

  (:action drive_truck
    :parameters (?t - truck ?from - place ?to - place)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (at ?t ?to) (not (at ?t ?from)))
  )

  (:action load_goods
    :parameters (?g - goods ?t - truck ?m - market ?e - level ?g_next - level ?d - level ?f - level)
    :precondition (and (at ?t ?m) (loaded ?g ?t ?f) (ready-to-load ?g ?m ?e) (next ?e ?d) (next ?g_next ?f))
    :effect (and (loaded ?g ?t ?g_next) (ready-to-load ?g ?m ?d) (not (loaded ?g ?t ?f)) (not (ready-to-load ?g ?m ?e)))
  )

  (:action unload_goods
    :parameters (?g - goods ?t - truck ?d - depot ?e - level ?d_next - level ?g_next - level ?f - level ?c - level)
    :precondition (and (at ?t ?d) (loaded ?g ?t ?e) (stored ?g ?f) (next ?e ?d_next) (next ?c ?f))
    :effect (and (loaded ?g ?t ?d_next) (stored ?g ?g_next) (not (loaded ?g ?t ?e)) (not (stored ?g ?f)))
  )

  (:action buy_goods
    :parameters (?g - goods ?t - truck ?m - market ?e - level ?d - level ?d_next - level ?f - level ?g_next - object)
    :precondition (and (at ?t ?m) (on-sale ?g ?m ?e) (ready-to-load ?g ?m ?f) (next ?e ?d) (next ?d_next ?f))
    :effect (and (on-sale ?g ?m ?d) (ready-to-load ?g ?m ?g_next) (not (on-sale ?g ?m ?e)) (not (ready-to-load ?g ?m ?f)))
  )

)