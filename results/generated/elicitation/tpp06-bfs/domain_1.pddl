(define (domain tpp06-bfs)
  (:requirements :strips :typing)

  (:types
    level locatable place - object
    depot market - place
    goods truck - locatable
  )

  (:predicates
    (at ?x - locatable ?y - place)
    (connected ?x - place ?y - place)
    (loaded ?g - goods ?t - truck ?l - level)
    (ready-to-load ?g - goods ?m - market ?l - level)
    (stored ?g - goods ?l - level)
    (on-sale ?g - goods ?m - market ?l - level)
    (next-to ?x - level ?y - level)
  )

  (:action drive_truck
    :parameters (?t - truck ?from - place ?to - place)
    :precondition (and (at ?t ?from) (connected ?from ?to))
    :effect (and (at ?t ?to) (not (at ?t ?from)))
  )

  (:action load_goods
    :parameters (?g - goods ?t - truck ?m - market ?e - level ?g_next - level ?d - level ?f - level)
    :precondition (and (at ?t ?m) (loaded ?g ?t ?f) (ready-to-load ?g ?m ?e) (next-to ?e ?d) (next-to ?g_next ?f))
    :effect (and (loaded ?g ?t ?g_next) (ready-to-load ?g ?m ?d) (not (loaded ?g ?t ?f)) (not (ready-to-load ?g ?m ?e)))
  )

  (:action unload_goods
    :parameters (?g - goods ?t - truck ?d - depot ?e - level ?g_next - level ?f - level ?target - level)
    :precondition (and (at ?t ?d) (loaded ?g ?t ?e) (stored ?g ?f) (next-to ?g_next ?f) (next-to ?e ?g_next))
    :effect (and (loaded ?g ?t ?g_next) (stored ?g ?target) (not (loaded ?g ?t ?e)) (not (stored ?g ?f)))
  )

  (:action buy_goods
    :parameters (?g - goods ?t - truck ?m - market ?e - level ?d - level ?f - level ?g_next - level)
    :precondition (and (at ?t ?m) (on-sale ?g ?m ?e) (ready-to-load ?g ?m ?f) (next-to ?e ?d) (next-to ?g_next ?f))
    :effect (and (on-sale ?g ?m ?d) (ready-to-load ?g ?m ?g_next) (not (on-sale ?g ?m ?e)) (not (ready-to-load ?g ?m ?f)))
  )

)