(define (domain pipesworld_strips)
  (:requirements :strips :typing)

  (:types
    area batch-atom pipe product - object
  )

  (:constants
    gasoleo lco oc1b oca1 rat-a - product
  )

  (:predicates
    (normal ?a - object)
    (unitary ?a - pipe)
    (is-push-updated ?a - pipe)
    (is-pop-updated ?a - object)
    (on ?b - batch-atom ?c - area)
    (first ?b - batch-atom ?a - object)
    (last ?b - batch-atom ?a - pipe)
    (follows ?d - batch-atom ?e - batch-atom)
    (connect ?c - area ?d - area ?a - object)
    (is-product ?b - batch-atom ?f - product)
    (may-interface ?f - product ?g - product)
    (is-unitary ?a - object)
  )

  (:action push-start
    :parameters (?a - pipe ?b - batch-atom ?c - area ?d - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (normal ?a) (first ?e ?a) (connect ?c ?d ?a) (on ?b ?c) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g))
    :effect (and (is-push-updated ?a) (first ?b ?a) (follows ?e ?b) (not (normal ?a)) (not (first ?e ?a)) (not (on ?b ?c)))
  )

  (:action push-end
    :parameters (?a - pipe ?d - batch-atom ?e - batch-atom ?b - area ?c - area)
    :precondition (and (is-push-updated ?a) (last ?d ?a) (connect ?b ?c ?a) (follows ?d ?e))
    :effect (and (normal ?a) (last ?e ?a) (on ?d ?c) (not (is-push-updated ?a)) (not (follows ?d ?e)) (not (last ?d ?a)))
  )

  (:action pop-start
    :parameters (?a - pipe ?b - batch-atom ?e - batch-atom ?f - product ?g - product ?c - area ?d - area)
    :precondition (and (normal ?a) (last ?e ?a) (connect ?c ?d ?a) (on ?b ?d) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g))
    :effect (and (is-pop-updated ?a) (last ?b ?a) (follows ?e ?b) (not (normal ?a)) (not (last ?e ?a)) (not (on ?b ?d)))
  )

  (:action pop-end
    :parameters (?d - batch-atom ?e - batch-atom ?b - area ?c - area ?a - object)
    :precondition (and (is-pop-updated ?a) (first ?d ?a) (connect ?b ?c ?a))
    :effect (and (normal ?a) (first ?e ?a) (on ?d ?b) (not (is-pop-updated ?a)) (not (first ?d ?a)))
  )

  (:action push-unitary
    :parameters (?a - pipe ?b - batch-atom ?c - area ?d - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (first ?e ?a) (connect ?c ?d ?a) (on ?b ?c) (unitary ?a) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g))
    :effect (and (first ?b ?a) (last ?b ?a) (on ?e ?d) (not (first ?e ?a)) (not (last ?e ?a)) (not (on ?b ?c)))
  )

  (:action pop-unitary
    :parameters (?a - pipe ?b - batch-atom ?c - area ?d - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (last ?e ?a) (connect ?c ?d ?a) (on ?b ?d) (unitary ?a) (is-product ?b ?f) (is-product ?e ?g) (may-interface ?f ?g))
    :effect (and (last ?b ?a) (first ?b ?a) (on ?e ?c) (not (last ?e ?a)) (not (first ?e ?a)) (not (on ?b ?d)))
  )

)