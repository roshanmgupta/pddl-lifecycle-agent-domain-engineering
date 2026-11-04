(define (domain blocksworld)
  (:requirements :strips :typing)

  (:types
    block table - object
  )

  (:predicates
    (on ?x - block ?y - object)
    (clear ?x - block)
    (holding ?x - block)
    (emptyhand)
  )

  (:action pickup
    :parameters (?x - block ?y - object)
    :precondition (and (on ?x ?y) (clear ?x) (emptyhand))
    :effect (and (not (on ?x ?y)) (not (clear ?x)) (holding ?x) (not (emptyhand)))
  )

  (:action putdown
    :parameters (?x - block ?y - object)
    :precondition (holding ?x)
    :effect (and (on ?x ?y) (clear ?x) (emptyhand) (not (holding ?x)))
  )

  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and (on ?x ?y) (clear ?x) (emptyhand) (not (holding ?x)) (not (clear ?y)))
  )

  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and (on ?x ?y) (clear ?x) (emptyhand))
    :effect (and (holding ?x) (clear ?y) (not (on ?x ?y)) (not (clear ?x)) (not (emptyhand)))
  )

)