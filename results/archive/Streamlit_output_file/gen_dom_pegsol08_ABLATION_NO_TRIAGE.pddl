(define (domain pegsolitaire-sequential)
  (:requirements :strips :typing)

  (:types
    location - object
  )

  (:predicates
    (move-ended)
    (IN-LINE ?a - location ?b - location ?c - location)
    (occupied ?l - location)
    (free ?l - location)
    (last-visited ?l - location)
  )

  (:action jump-new-move
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (move-ended) (IN-LINE ?a ?b ?c) (occupied ?a) (occupied ?b) (free ?c))
    :effect (and (not (move-ended)) (not (occupied ?a)) (not (occupied ?b)) (not (free ?c)) (free ?a) (free ?b) (occupied ?c) (last-visited ?c))
  )

  (:action continue-jump
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (last-visited ?a) (IN-LINE ?a ?b ?c) (occupied ?a) (occupied ?b) (free ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (not (free ?c)) (not (last-visited ?a)) (free ?a) (free ?b) (occupied ?c) (last-visited ?c))
  )

  (:action end-move
    :parameters (?a - location)
    :precondition (last-visited ?a)
    :effect (and (move-ended) (not (last-visited ?a)))
  )

)