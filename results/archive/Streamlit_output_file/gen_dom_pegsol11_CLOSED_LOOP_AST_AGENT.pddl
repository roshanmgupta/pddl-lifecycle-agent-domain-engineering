(define (domain pegsolitaire-sequential)
  (:requirements :strips :typing)

  (:types
    location - object
  )

  (:predicates
    (move-ended)
    (occupied ?loc - location)
    (free ?loc - object)
    (IN-LINE ?a - location ?b - location ?c - location)
  )

  (:action jump-new-move
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (move-ended) (IN-LINE ?a ?b ?c) (occupied ?a) (occupied ?b) (free ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (occupied ?c) (not (move-ended)) (not (free ?c)))
  )

  (:action continue-jump
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (occupied ?a) (IN-LINE ?a ?b ?c) (occupied ?b) (free ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (occupied ?c) (not (free ?c)))
  )

  (:action end-move
    :parameters (?a - location)
    :precondition (occupied ?a)
    :effect (and (move-ended) (not (occupied ?a)))
  )

)