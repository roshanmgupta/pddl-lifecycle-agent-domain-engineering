(define (domain gold-miner-typed)
  (:requirements :strips :typing)

  (:types
    bomb gold laser loc location robot soft_rock - object
  )

  (:predicates
    (at ?r - robot ?l - location)
    (connected ?l1 - object ?l2 - object)
    (clear ?l - object)
    (holding_laser ?r - robot)
    (holding_bomb ?r - robot)
    (holding_gold ?r - robot)
    (arm-empty)
    (laser-at ?l - object)
    (bomb-at ?l - object)
    (gold-at ?l - object)
    (soft-rock-at ?l - object)
    (robot-at ?x1 - loc)
    (holds-gold)
  )

  (:action move_robot
    :parameters (?r - robot ?from - location ?to - location)
    :precondition (and (at ?r ?from) (connected ?from ?to) (clear ?to))
    :effect (and (not (at ?r ?from)) (at ?r ?to))
  )

  (:action pick_up_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (laser-at ?l))
    :effect (and (not (laser-at ?l)) (holding_laser ?r))
  )

  (:action pick_up_bomb
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (bomb-at ?l))
    :effect (and (not (bomb-at ?l)) (holding_bomb ?r))
  )

  (:action put_down_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (holding_laser ?r))
    :effect (and (not (holding_laser ?r)) (laser-at ?l))
  )

  (:action detonate_bomb
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding_bomb ?r) (connected ?l1 ?l2) (soft-rock-at ?l2))
    :effect (and (not (holding_bomb ?r)) (clear ?l2) (not (soft-rock-at ?l2)))
  )

  (:action fire_laser
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding_laser ?r) (connected ?l1 ?l2))
    :effect (and (clear ?l2) (not (soft-rock-at ?l2)) (not (gold-at ?l2)))
  )

  (:action pick_gold
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (gold-at ?l))
    :effect (and (not (gold-at ?l)) (holding_gold ?r))
  )

)