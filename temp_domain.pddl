(define (domain scanalyzer3d)
  (:requirements :strips :typing)

  (:types
    car physical_entity segment - object
  )

  (:predicates
    (CYCLE-2 ?a - segment ?b - segment)
    (CYCLE-2-WITH-ANALYSIS ?a - segment ?b - segment)
    (on ?car - car ?seg - segment)
    (analyzed ?car - car)
  )

  (:action analyze_cycle_length_2
    :parameters (?c - car ?d - car ?a - segment ?b - segment)
    :precondition (and (CYCLE-2-WITH-ANALYSIS ?a ?b) (on ?c ?a) (on ?d ?b))
    :effect (and (on ?c ?b) (on ?d ?a) (analyzed ?c) (not (on ?c ?a)) (not (on ?d ?b)))
  )

  (:action analyze_cycle_length_4
    :parameters (?e - car ?f - car ?g - car ?h - car ?a - segment ?b - segment ?c - segment ?d - segment)
    :precondition (and (CYCLE-2-WITH-ANALYSIS ?a ?b) (on ?e ?a) (on ?f ?b) (on ?g ?c) (on ?h ?d))
    :effect (and (on ?e ?d) (on ?f ?a) (on ?g ?b) (on ?h ?c) (analyzed ?e) (not (on ?e ?a)) (not (on ?f ?b)) (not (on ?g ?c)) (not (on ?h ?d)))
  )

  (:action rotate_cars_length_2
    :parameters (?c - car ?d - car ?a - segment ?b - segment)
    :precondition (and (CYCLE-2 ?a ?b) (on ?c ?a) (on ?d ?b))
    :effect (and (on ?c ?b) (on ?d ?a) (not (on ?c ?a)) (not (on ?d ?b)))
  )

  (:action rotate_cars_length_4
    :parameters (?e - car ?f - car ?g - car ?h - car ?a - segment ?b - segment ?c - segment ?d - segment)
    :precondition (and (CYCLE-2-WITH-ANALYSIS ?a ?b) (on ?e ?a) (on ?f ?b) (on ?g ?c) (on ?h ?d))
    :effect (and (on ?e ?d) (on ?f ?a) (on ?g ?b) (on ?h ?c) (not (on ?e ?a)) (not (on ?f ?b)) (not (on ?g ?c)) (not (on ?h ?d)))
  )

)