(define (domain pipesworld-notankage04-bfs)
  (:requirements :strips :typing)

  (:types
    area batch-atom pipe product - object
    normal-pipe unitary-pipe - pipe
    pop-updated-pipe push-updated-pipe - normal-pipe
  )

  (:predicates
    (normal ?p - pipe)
    (unitary ?p - pipe)
    (may-interface ?p1 - object ?p2 - object)
    (on ?b - batch-atom ?a - area)
    (first-in ?b - batch-atom ?p - pipe)
    (last-in ?b - batch-atom ?p - pipe)
    (connected ?a1 - area ?a2 - area)
    (product ?b - object ?x - object)
    (push-updated ?a - normal-pipe)
    (pop-updated ?a - normal-pipe)
  )

  (:action push-start-pipe
    :parameters (?a - normal-pipe ?b - batch-atom ?src - area ?dst - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (normal ?a) (first-in ?e ?a) (connected ?src ?dst) (on ?b ?src) (not (unitary ?a)) (product ?b ?f) (product ?e ?g) (may-interface ?f ?g))
    :effect (and (push-updated ?a) (first-in ?b ?a) (last-in ?e ?a) (not (normal ?a)) (not (first-in ?e ?a)) (not (on ?b ?src)))
  )

  (:action push-end-pipe
    :parameters (?a - push-updated-pipe ?d - batch-atom ?e - batch-atom ?src - area ?dst - area)
    :precondition (and (connected ?src ?dst) (not (unitary ?a)) (last-in ?d ?a) (last-in ?e ?a))
    :effect (and (normal ?a) (last-in ?e ?a) (on ?d ?dst) (not (push-updated ?a)) (not (last-in ?d ?a)))
  )

  (:action pop-start-pipe
    :parameters (?a - normal-pipe ?b - batch-atom ?src - area ?dst - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (normal ?a) (last-in ?e ?a) (connected ?src ?dst) (on ?b ?dst) (not (unitary ?a)) (product ?b ?f) (product ?e ?g) (may-interface ?f ?g))
    :effect (and (pop-updated ?a) (last-in ?b ?a) (not (normal ?a)) (not (last-in ?e ?a)) (not (on ?b ?dst)))
  )

  (:action pop-end-pipe
    :parameters (?a - pop-updated-pipe ?d - batch-atom ?e - batch-atom ?src - area ?dst - area)
    :precondition (and (connected ?src ?dst) (not (unitary ?a)) (first-in ?d ?a) (first-in ?e ?a))
    :effect (and (normal ?a) (first-in ?e ?a) (on ?d ?src) (not (pop-updated ?a)) (not (first-in ?d ?a)))
  )

  (:action push-unitary-pipe
    :parameters (?a - unitary-pipe ?b - batch-atom ?src - area ?dst - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (first-in ?e ?a) (connected ?src ?dst) (on ?b ?src) (unitary ?a) (product ?b ?f) (product ?e ?g) (may-interface ?f ?g))
    :effect (and (first-in ?b ?a) (last-in ?b ?a) (on ?e ?dst) (not (first-in ?e ?a)) (not (last-in ?e ?a)) (not (on ?b ?src)))
  )

  (:action pop-unitary-pipe
    :parameters (?a - unitary-pipe ?b - batch-atom ?src - area ?dst - area ?e - batch-atom ?f - product ?g - product)
    :precondition (and (last-in ?e ?a) (connected ?src ?dst) (on ?b ?dst) (unitary ?a) (product ?b ?f) (product ?e ?g) (may-interface ?f ?g))
    :effect (and (last-in ?b ?a) (first-in ?b ?a) (on ?e ?src) (not (last-in ?e ?a)) (not (first-in ?e ?a)) (not (on ?b ?dst)))
  )

)