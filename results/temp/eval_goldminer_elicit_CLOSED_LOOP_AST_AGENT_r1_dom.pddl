(define (domain gold-miner-typed)
  (:requirements :typing)

  (:types
    LOC loc - object
  )

  (:predicates
    (robot-at ?x - object)
    (bomb-at ?x - object)
    (laser-at ?x - object)
    (soft-rock-at ?x - object)
    (hard-rock-at ?x - object)
    (gold-at ?x - object)
    (arm-empty)
    (holds-bomb)
    (holds-laser)
    (holds-gold)
    (clear ?x - object)
    (connected ?x - object ?y - object)
  )

  (:action move
    :parameters (?x - LOC ?y - LOC)
    :precondition (and (robot-at ?x) (connected ?x ?y) (clear ?y))
    :effect (and (robot-at ?y) (not (robot-at ?x)))
  )

  (:action pickup-laser
    :parameters (?x - LOC)
    :precondition (and (robot-at ?x) (laser-at ?x) (arm-empty))
    :effect (and (holds-laser) (not (arm-empty)) (not (laser-at ?x)))
  )

  (:action pickup-bomb
    :parameters (?x - LOC)
    :precondition (and (robot-at ?x) (bomb-at ?x) (arm-empty))
    :effect (and (holds-bomb) (not (arm-empty)))
  )

  (:action putdown-laser
    :parameters (?x - LOC)
    :precondition (and (robot-at ?x) (holds-laser))
    :effect (and (arm-empty) (laser-at ?x) (not (holds-laser)))
  )

  (:action detonate-bomb
    :parameters (?x - LOC ?y - LOC)
    :precondition (and (robot-at ?x) (holds-bomb) (connected ?x ?y) (soft-rock-at ?y))
    :effect (and (arm-empty) (clear ?y) (not (holds-bomb)) (not (soft-rock-at ?y)))
  )

  (:action fire-laser
    :parameters (?x - LOC ?y - LOC)
    :precondition (and (robot-at ?x) (holds-laser) (connected ?x ?y))
    :effect (and (clear ?y) (not (soft-rock-at ?y)) (not (gold-at ?y)) (not (hard-rock-at ?y)))
  )

  (:action pick-gold
    :parameters (?x - LOC)
    :precondition (and (robot-at ?x) (arm-empty) (gold-at ?x))
    :effect (and (holds-gold) (not (arm-empty)))
  )

)