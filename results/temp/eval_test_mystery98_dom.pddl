(define (domain mystery-strips)
  (:requirements :strips)

  (:predicates
    (province ?x)
    (planet ?x)
    (food ?x)
    (pleasure ?x)
    (pain ?x)
    (eats ?n1 ?n2)
    (craves ?v ?n)
    (fears ?c ?v)
    (locale ?n ?a)
    (harmony ?v ?s)
    (attacks ?i ?j)
    (orbits ?i ?j)
  )

  (:action overcome
    :parameters (?c ?v ?n ?s1 ?s2)
    :precondition (and (pain ?c) (pleasure ?v) (craves ?c ?n) (craves ?v ?n) (food ?n) (harmony ?v ?s2) (planet ?s2) (orbits ?s1 ?s2) (planet ?s1))
    :effect (and (fears ?c ?v) (harmony ?v ?s1) (not (craves ?c ?n)) (not (harmony ?v ?s2)))
  )

  (:action feast
    :parameters (?v ?n1 ?n2 ?l1 ?l2)
    :precondition (and (pleasure ?v) (food ?n1) (craves ?v ?n1) (eats ?n1 ?n2) (food ?n2) (locale ?n1 ?l2) (attacks ?l1 ?l2))
    :effect (and (craves ?v ?n2) (locale ?n1 ?l1) (not (craves ?v ?n1)) (not (locale ?n1 ?l2)))
  )

  (:action succumb
    :parameters (?c ?v ?n ?s1 ?s2)
    :precondition (and (pain ?c) (pleasure ?v) (fears ?c ?v) (craves ?v ?n) (food ?n) (harmony ?v ?s1) (orbits ?s1 ?s2))
    :effect (and (craves ?c ?n) (harmony ?v ?s2) (not (fears ?c ?v)) (not (harmony ?v ?s1)))
  )

)