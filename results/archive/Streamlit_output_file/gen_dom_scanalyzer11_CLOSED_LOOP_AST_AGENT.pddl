(define (domain scanalyzer3d)
  (:requirements :strips :typing)

  (:types
    car cycle_length_2 cycle_length_4 segment - object
  )

  (:predicates
    (on ?c - car ?s - segment)
    (analyzed ?c - car)
    (CYCLE-4 ?a - segment ?b - segment ?c - object ?d - object)
    (CYCLE-4-WITH-ANALYSIS ?a - segment ?b - segment ?c - object ?d - object)
  )

  (:action analyze-cycle-length-2
    :parameters (?c - car ?d - car ?a - segment ?b - segment ?seg-in-1a - object ?seg-in-1b - object)
    :precondition (and (CYCLE-4-WITH-ANALYSIS ?a ?b ?seg-in-1a ?seg-in-1b) (on ?c ?a) (on ?d ?b))
    :effect (and (on ?c ?b) (on ?d ?a) (analyzed ?c) (not (on ?c ?a)) (not (on ?d ?b)))
  )

  (:action analyze-cycle-length-4
    :parameters (?e - car ?f - car ?g - car ?h - car ?a - segment ?b - segment ?c - segment ?d - segment)
    :precondition (and (CYCLE-4 ?a ?b ?c ?d) (on ?e ?a) (on ?f ?b) (on ?g ?c) (on ?h ?d))
    :effect (and (on ?e ?d) (on ?f ?a) (on ?g ?b) (on ?h ?c) (analyzed ?e) (not (on ?e ?a)) (not (on ?f ?b)) (not (on ?g ?c)) (not (on ?h ?d)))
  )

  (:action rotate-cars-length-2
    :parameters (?c - car ?d - car ?a - segment ?b - segment ?seg-in-1a - object ?seg-in-1b - object)
    :precondition (and (CYCLE-4 ?a ?b ?seg-in-1a ?seg-in-1b) (on ?c ?a) (on ?d ?b) (CYCLE-4-WITH-ANALYSIS ?a ?b ?seg-in-1a ?seg-in-1b))
    :effect (and (on ?c ?b) (on ?d ?a) (not (on ?c ?a)) (not (on ?d ?b)))
  )

  (:action rotate-cars-length-4
    :parameters (?e - car ?f - car ?g - car ?h - car ?a - segment ?b - segment ?c - segment ?d - segment)
    :precondition (and (CYCLE-4 ?a ?b ?c ?d) (on ?e ?a) (on ?f ?b) (on ?g ?c) (on ?h ?d))
    :effect (and (on ?e ?d) (on ?f ?a) (on ?g ?b) (on ?h ?c) (not (on ?e ?a)) (not (on ?f ?b)) (not (on ?g ?c)) (not (on ?h ?d)))
  )

)