(define (domain jump_move_domain)
  (:requirements :strips :typing)

  (:types
    location move - object
  )

  (:predicates
    (move-ended ?m - object)
    (in-line ?a - location ?b - location ?c - location)
    (occupied ?loc - location)
    (free ?loc - location)
    (last-visited ?loc - location)
  )

  (:action jump_new_move
    :parameters (?a - location ?b - location ?c - location ?m - object)
    :precondition (and (move-ended ?m) (in-line ?a ?b ?c) (occupied ?a) (occupied ?b) (free ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (occupied ?c) (last-visited ?c) (not (move-ended ?m)) (not (free ?c)) (free ?a) (free ?b))
  )

  (:action continue_jump
    :parameters (?a - location ?b - location ?c - location)
    :precondition (and (last-visited ?a) (in-line ?a ?b ?c) (occupied ?a) (occupied ?b) (free ?c))
    :effect (and (not (occupied ?a)) (not (occupied ?b)) (occupied ?c) (last-visited ?c) (not (free ?c)) (free ?a) (free ?b))
  )

  (:action end_move
    :parameters (?a - location ?m - object)
    :precondition (last-visited ?a)
    :effect (and (move-ended ?m) (not (last-visited ?a)))
  )

)