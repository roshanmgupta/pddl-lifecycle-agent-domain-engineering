(define (domain TPP-Propositional)
  (:requirements :strips :typing)
  (:types
    place locatable level - object
    depot market - place
    truck goods - locatable
  )

  (:predicates
    (next ?l1 ?l2 - level)
    (connected ?p1 ?p2 - place)
    (at ?t - truck ?p - place)
    (loaded ?g - goods ?t - truck ?l - level)
    (ready-to-load ?g - goods ?m - market ?l - level)
    (stored ?g - goods ?l - level)
    (on-sale ?g - goods ?m - market ?l - level)
  )

  (:action drive
    :parameters (?t - truck ?from - place ?to - place)
    :precondition (and
                   (at ?t ?from)
                   (connected ?from ?to)
                  )
    :effect (and
              (not (at ?t ?from))
              (at ?t ?to)
            )
  )

  (:action load
    :parameters (?g - goods ?t - truck ?m - market ?e ?g_level ?d ?f - level)
    :precondition (and
                   (at ?t ?m)
                   (loaded ?g ?t ?f)
                   (ready-to-load ?g ?m ?e)
                   (next ?e ?d)
                   (next ?g_level ?f)
                  )
    :effect (and
              (not (loaded ?g ?t ?f))
              (not (ready-to-load ?g ?m ?e))
              (loaded ?g ?t ?g_level)
              (ready-to-load ?g ?m ?d)
            )
  )

  (:action unload
    :parameters (?g - goods ?t - truck ?d - depot ?e ?d_level ?g_level ?f - level)
    :precondition (and
                   (at ?t ?d)
                   (loaded ?g ?t ?e)
                   (stored ?g ?f)
                   (next ?e ?d_level)
                   (next ?g_level ?f)
                  )
    :effect (and
              (not (loaded ?g ?t ?e))
              (not (stored ?g ?f))
              (loaded ?g ?t ?d_level)
              (stored ?g ?g_level)
            )
  )

  (:action buy
    :parameters (?g - goods ?t - truck ?m - market ?e ?d ?g_level ?f - level)
    :precondition (and
                   (at ?t ?m)
                   (on-sale ?g ?m ?e)
                   (ready-to-load ?g ?m ?f)
                   (next ?e ?d)
                   (next ?g_level ?f)
                  )
    :effect (and
              (not (on-sale ?g ?m ?e))
              (not (ready-to-load ?g ?m ?f))
              (on-sale ?g ?m ?d)
              (ready-to-load ?g ?m ?g_level)
            )
  )
)