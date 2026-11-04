(define (domain pipesworld_strips)
  (:requirements :strips :typing)

  (:types
    area batch-atom pipe product tank-slot - object
  )

  (:constants
    gasoleo lco oc1b oca1 rat-a - product
  )

  (:predicates
    (unitary ?a - pipe)
    (being-push-updated ?a - pipe)
    (being-pop-updated ?a - pipe)
    (first ?b - batch-atom ?a - pipe)
    (last ?d - batch-atom ?a - pipe)
    (on ?b - batch-atom ?c - area)
    (connect ?x1 - area ?x2 - area ?x3 - pipe)
    (occupied ?h - tank-slot)
    (location-of ?f - product ?c - object)
    (may-interface ?f - product ?g - product)
    (not-occupied ?g - tank-slot)
    (is-product ?b - batch-atom ?f - product)
    (follows ?d - batch-atom ?e - batch-atom)
    (normal ?x1 - pipe)
    (tank-slot-product-location ?x1 - tank-slot ?x2 - product ?x3 - area)
    (-occupied ?x1 - tank-slot)
  )

  (:action push-start-pipe
    :parameters (?a - pipe ?c - area ?d - area ?b - batch-atom ?e - batch-atom ?f - product ?g - product ?h - tank-slot)
    :precondition (and (unitary ?a) (connect ?c ?d ?a) (first ?e ?a) (on ?b ?c) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g) (occupied ?h))
    :effect (and (being-push-updated ?a) (first ?b ?a) (last ?e ?a) (not (unitary ?a)) (not (first ?e ?a)) (not (on ?b ?c)) (not (occupied ?h)))
  )

  (:action push-end-pipe
    :parameters (?a - pipe ?b - area ?c - area ?d - batch-atom ?e - batch-atom ?f - product ?g - tank-slot)
    :precondition (and (being-pop-updated ?a) (connect ?b ?c ?a) (last ?d ?a) (is-product ?d ?f))
    :effect (and (unitary ?a) (last ?e ?a) (on ?d ?c) (occupied ?g) (not (being-pop-updated ?a)) (not (last ?d ?a)))
  )

  (:action pop-start-pipe
    :parameters (?a - pipe ?c - area ?d - area ?b - batch-atom ?e - batch-atom ?f - product ?g - product ?h - tank-slot)
    :precondition (and (unitary ?a) (connect ?c ?d ?a) (last ?e ?a) (on ?b ?d) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g) (occupied ?h))
    :effect (and (being-push-updated ?a) (last ?b ?a) (follows ?e ?b) (not (unitary ?a)) (not (last ?e ?a)) (not (on ?b ?d)) (not (occupied ?h)))
  )

  (:action pop-end-pipe
    :parameters (?a - pipe ?b - area ?c - area ?d - batch-atom ?e - batch-atom ?f - product ?g - tank-slot)
    :precondition (and (being-pop-updated ?a) (connect ?b ?c ?a) (first ?d ?a))
    :effect (and (unitary ?a) (first ?e ?a) (on ?d ?b) (occupied ?g) (not (being-pop-updated ?a)) (not (first ?d ?a)))
  )

  (:action push-batch-through-unitary-pipe
    :parameters (?a - pipe ?c - area ?d - area ?b - batch-atom ?e - batch-atom ?f - product ?g - product ?h - tank-slot ?i - tank-slot)
    :precondition (and (first ?e ?a) (on ?b ?c) (unitary ?a) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g) (location-of ?f ?h) (occupied ?h) (location-of ?g ?i))
    :effect (and (first ?b ?a) (last ?b ?a) (not (occupied ?h)) (on ?e ?d) (occupied ?i) (not (first ?e ?a)) (not (last ?e ?a)) (not (on ?b ?c)))
  )

  (:action pop-batch-through-unitary-pipe
    :parameters (?a - pipe ?c - area ?d - area ?b - batch-atom ?e - batch-atom ?f - product ?g - product ?h - tank-slot ?i - tank-slot)
    :precondition (and (first ?e ?a) (on ?b ?d) (unitary ?a) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g) (location-of ?f ?d) (occupied ?i) (location-of ?g ?c))
    :effect (and (last ?b ?a) (first ?b ?a) (not (occupied ?i)) (on ?e ?c) (occupied ?h) (not (first ?e ?a)) (not (last ?e ?a)) (not (on ?b ?d)))
  )

)