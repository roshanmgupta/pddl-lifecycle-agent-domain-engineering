(define (domain tpp06-bfs)
  (:requirements :strips :typing)

  (:types
    depot goods level market truck - object
  )

  (:predicates
    (next-to ?l1 - level ?l2 - level)
    (ready-to-load ?g - goods ?m - market ?l_load - level)
    (stored ?g - goods ?l - level)
    (loaded ?g - goods ?t - truck ?l_truck - level)
    (connected ?d - depot ?m - market)
    (on-sale ?g - goods ?m - market ?l - level)
    (at ?t - truck ?l - level)
  )

  (:action load_goods
    :parameters (?g - goods ?m - market ?t - truck ?l_load - level)
    :precondition (and (ready-to-load ?g ?m ?l_load) (stored ?g ?l_load) (at ?t ?l_load))
    :effect (and (not (ready-to-load ?g ?m ?l_load)) (not (stored ?g ?l_load)) (loaded ?g ?t ?l_load))
  )

  (:action move_goods
    :parameters (?g - goods ?l_from - level ?l_to - level ?t - truck)
    :precondition (and (loaded ?g ?t ?l_from) (next-to ?l_from ?l_to))
    :effect (and (not (loaded ?g ?t ?l_from)) (stored ?g ?l_to))
  )

)