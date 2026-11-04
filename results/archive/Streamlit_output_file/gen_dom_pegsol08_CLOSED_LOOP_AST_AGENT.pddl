(define (domain pegsolitaire-sequential)
  (:requirements :strips :typing)

  (:types
    location physical_entity - object
    mobile_unit - physical_entity
  )

  (:predicates
    (move-ended)
    (last-visited-location ?x - location)
    (occupied ?x - location)
    (free ?x - location)
    (IN-LINE ?a - location ?b - location ?c - location)
  )

  (:action jump-new-move
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (move-ended) (occupied ?a) (occupied ?b) (free ?c) (IN-LINE ?a ?b ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (not (free ?c)) (not (move-ended)) (last-visited-location ?c))
  )

  (:action continue-jump
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (last-visited-location ?a) (occupied ?a) (occupied ?b) (free ?c) (IN-LINE ?a ?b ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (not (free ?c)) (last-visited-location ?c))
  )

  (:action end-move
    :parameters (?a - location)
    :precondition (last-visited-location ?a)
    :effect (and (move-ended) (not (last-visited-location ?a)))
  )

)