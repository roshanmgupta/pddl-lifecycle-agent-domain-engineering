(define (domain scanalyzer3d)
  (:requirements :strips :typing)

  (:types
    car segment - object
  )

  (:predicates
    (on ?c - object ?s - object)
    (analyzed ?c - object)
    (CYCLE-2 ?s1 - object ?s2 - object)
    (CYCLE-4 ?s1 - object ?s2 - object ?s3 - object ?s4 - object)
    (CYCLE-2-WITH-ANALYSIS ?s1 - object ?s2 - object)
    (CYCLE-4-WITH-ANALYSIS ?s1 - object ?s2 - object ?s3 - object ?s4 - object)
  )

  (:action analyze-2
    :parameters (?s1 - segment ?s2 - segment ?c1 - car ?c2 - car)
    :precondition (and (CYCLE-2-WITH-ANALYSIS ?s1 ?s2) (on ?c1 ?s1) (on ?c2 ?s2))
    :effect (and (not (on ?c1 ?s1)) (not (on ?c2 ?s2)) (on ?c1 ?s2) (on ?c2 ?s1) (analyzed ?c1))
  )

  (:action analyze-4
    :parameters (?s1 - segment ?s2 - segment ?s3 - segment ?s4 - segment ?c1 - car ?c2 - car ?c3 - car ?c4 - car)
    :precondition (and (CYCLE-4-WITH-ANALYSIS ?s1 ?s2 ?s3 ?s4) (on ?c1 ?s1) (on ?c2 ?s2) (on ?c3 ?s3) (on ?c4 ?s4))
    :effect (and (not (on ?c1 ?s1)) (not (on ?c2 ?s2)) (not (on ?c3 ?s3)) (not (on ?c4 ?s4)) (on ?c1 ?s4) (on ?c2 ?s1) (on ?c3 ?s2) (on ?c4 ?s3) (analyzed ?c1))
  )

  (:action rotate-2
    :parameters (?s1 - segment ?s2 - segment ?c1 - car ?c2 - car)
    :precondition (and (CYCLE-2 ?s1 ?s2) (on ?c1 ?s1) (on ?c2 ?s2))
    :effect (and (not (on ?c1 ?s1)) (not (on ?c2 ?s2)) (on ?c1 ?s2) (on ?c2 ?s1))
  )

  (:action rotate-4
    :parameters (?s1 - segment ?s2 - segment ?s3 - segment ?s4 - segment ?c1 - car ?c2 - car ?c3 - car ?c4 - car)
    :precondition (and (CYCLE-4 ?s1 ?s2 ?s3 ?s4) (on ?c1 ?s1) (on ?c2 ?s2) (on ?c3 ?s3) (on ?c4 ?s4))
    :effect (and (not (on ?c1 ?s1)) (not (on ?c2 ?s2)) (not (on ?c3 ?s3)) (not (on ?c4 ?s4)) (on ?c1 ?s4) (on ?c2 ?s1) (on ?c3 ?s2) (on ?c4 ?s3))
  )

)