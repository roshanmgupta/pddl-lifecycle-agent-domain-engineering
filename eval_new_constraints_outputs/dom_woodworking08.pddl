(define (domain woodworking08)
  (:requirements :strips :typing)

  (:types
    aboardsize acolour awood board part woodworking-tool - object
    glazer grinder highspeed-saw immersion-varnisher planer saw spray-varnisher - woodworking-tool
  )

  (:predicates
    (has-colour ?i - object ?c - acolour)
    (is-empty ?x - highspeed-saw)
    (is-unused ?p - part)
    (goal-size ?p - part ?size - aboardsize)
    (is-available ?p - part)
    (is-made-of ?p - part ?w - awood)
    (has-surface-condition ?p - part ?condition - object)
    (is-undergoing-treatment ?p - part ?treatment - object)
    (successor ?s1 - aboardsize ?s2 - aboardsize)
  )

  (:action change-treatment
    :parameters (?p - part ?old-treatment - object ?new-treatment - object)
    :precondition (is-undergoing-treatment ?p ?old-treatment)
    :effect (and (not (is-undergoing-treatment ?p ?old-treatment)) (is-undergoing-treatment ?p ?new-treatment))
  )

  (:action set-colour
    :parameters (?g - object ?c - acolour)
    :precondition (and)
    :effect (has-colour ?g ?c)
  )

  (:action set-surface-condition
    :parameters (?p - part ?condition - object)
    :precondition (and)
    :effect (has-surface-condition ?p ?condition)
  )

  (:action set-availability
    :parameters (?p - part)
    :precondition (and)
    :effect (is-available ?p)
  )

  (:action set-made-of
    :parameters (?p - part ?w - awood)
    :precondition (and)
    :effect (is-made-of ?p ?w)
  )

)