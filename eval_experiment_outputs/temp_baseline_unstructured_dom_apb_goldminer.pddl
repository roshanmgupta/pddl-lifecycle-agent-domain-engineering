(define (domain gold-miner-typed)
  (:requirements :strips :typing)
  (:types loc)
  
  (:predicates
    (robot-at ?l - loc)
    (connected ?l1 - loc ?l2 - loc)
    (clear ?l - loc)
    (arm-empty)
    (holding-laser)
    (holding-bomb)
    (holding-gold)
    (soft-rock-at ?l - loc)
    (bomb-at ?l - loc)
    (laser-at ?l - loc)
    (gold-at ?l - loc)
  )

  (:action move
    :parameters (?from - loc ?to - loc)
    :precondition (and (robot-at ?from) (connected ?from ?to) (clear ?to))
    :effect (and (not (robot-at ?from)) (robot-at ?to))
  )

  (:action pick-up-laser
    :parameters (?loc - loc)
    :precondition (and (robot-at ?loc) (laser-at ?loc) (arm-empty))
    :effect (and (not (arm-empty)) (holding-laser) (not (laser-at ?loc)))
  )

  (:action pick-up-bomb
    :parameters (?loc - loc)
    :precondition (and (robot-at ?loc) (bomb-at ?loc) (arm-empty))
    :effect (and (not (arm-empty)) (holding-bomb) (not (bomb-at ?loc)))
  )

  (:action put-down-laser
    :parameters (?loc - loc)
    :precondition (and (robot-at ?loc) (holding-laser))
    :effect (and (arm-empty) (laser-at ?loc) (not (holding-laser)))
  )

  (:action detonate-bomb
    :parameters (?locA - loc ?locB - loc)
    :precondition (and (robot-at ?locA) (holding-bomb) (connected ?locA ?locB) (soft-rock-at ?locB))
    :effect (and (arm-empty) (not (holding-bomb)) (not (soft-rock-at ?locB)) (clear ?locB))
  )

  (:action fire-laser
    :parameters (?locA - loc ?locB - loc)
    :precondition (and (robot-at ?locA) (holding-laser) (connected ?locA ?locB))
    :effect (and (not (soft-rock-at ?locB)) (not (gold-at ?locB)) (not (holding-laser)) (clear ?locB))
  )

  (:action pick-gold
    :parameters (?loc - loc)
    :precondition (and (robot-at ?loc) (arm-empty) (gold-at ?loc))
    :effect (and (not (arm-empty)) (holding-gold) (not (gold-at ?loc)))
  )
)