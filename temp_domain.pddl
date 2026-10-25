(define (domain TPP-Propositional)
  (:requirements :strips :typing)

  (:types
    level locatable place - object
    depot market - place
    goods truck - locatable
  )

  (:predicates
    (at ?x - locatable ?y - place)
    (connected ?x - place ?y - place)
    (next ?x - level ?y - level)
    (loaded ?x - goods ?y - truck ?z - level)
    (ready-to-load ?x - goods ?y - place ?z - level)
    (stored ?x - goods ?y - level)
    (on-sale ?x - goods ?y - place ?z - level)
  )

  (:action drive
    :parameters (?a - truck ?b - place ?c - place)
    :precondition (and (at ?a ?b) (connected ?b ?c))
    :effect (and (not (at ?a ?b)) (at ?a ?c))
  )

  (:action load
    :parameters (?a - goods ?b - truck ?c - market ?e - level ?g - level ?d - level ?f - level)
    :precondition (and (at ?b ?c) (loaded ?a ?b ?f) (ready-to-load ?a ?c ?e) (next ?e ?d) (next ?g ?f))
    :effect (and (not (loaded ?a ?b ?f)) (not (ready-to-load ?a ?c ?e)) (loaded ?a ?b ?g) (ready-to-load ?a ?c ?d))
  )

  (:action unload
    :parameters (?a - goods ?b - truck ?c - depot ?e - level ?d - level ?g - level ?f - level)
    :precondition (and (at ?b ?c) (loaded ?a ?b ?e) (stored ?a ?f) (next ?e ?d) (next ?g ?f))
    :effect (and (not (loaded ?a ?b ?e)) (not (stored ?a ?f)) (loaded ?a ?b ?d) (stored ?a ?g))
  )

  (:action buy
    :parameters (?b - goods ?a - truck ?c - market ?e - level ?d - level ?g - level ?f - level)
    :precondition (and (at ?a ?c) (on-sale ?b ?c ?e) (ready-to-load ?b ?c ?f) (next ?e ?d) (next ?g ?f))
    :effect (and (not (on-sale ?b ?c ?e)) (not (ready-to-load ?b ?c ?f)) (on-sale ?b ?c ?d) (ready-to-load ?b ?c ?g))
  )

)