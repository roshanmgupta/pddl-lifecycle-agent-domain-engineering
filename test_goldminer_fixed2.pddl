(define (domain gold-miner-typed)
  (:requirements :strips :typing)

  (:constants laser bomb gold - object)
  (:types
    LOC - object
    bomb gold hard_rock laser location robot soft_rock - object
  )

  (:predicates
    (at ?r - robot ?l - location)
    (connected ?l1 - object ?l2 - object)
    (holding_laser ?r - robot)
    (holding_bomb ?r - robot)
    (holding_gold ?r - robot)
    (arm-empty)
    (clear ?l - object)
    (soft-rock-at ?l - object)
    (hard_rock_at ?l - location)
    (laser-at ?l - object)
    (bomb-at ?l - object)
    (gold-at ?l - object)
    (robot-at ?x1 - loc)
    (holds-gold)
  )

  (:action move_robot
    :parameters (?r - robot ?from - location ?to - location)
    :precondition (and (at ?r ?from) (connected ?from ?to) (clear ?to))
    :effect (and (at ?r ?to) (not (at ?r ?from)))
  )

  (:action pick_up_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (laser-at ?l) (arm-empty))
    :effect (and (holding_laser ?r) (not (arm-empty)) (not (laser-at ?l)))
  )

  (:action pick_up_bomb
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (bomb-at ?l) (arm-empty))
    :effect (and (holding_bomb ?r) (not (arm-empty)) (not (bomb-at ?l)))
  )

  (:action put_down_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (holding_laser ?r))
    :effect (and (arm-empty) (laser-at ?l) (not (holding_laser ?r)))
  )

  (:action detonate_bomb
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding_bomb ?r) (connected ?l1 ?l2) (soft-rock-at ?l2))
    :effect (and (arm-empty) (clear ?l2) (not (holding_bomb ?r)) (not (soft-rock-at ?l2)))
  )

  (:action fire_laser
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding_laser ?r) (connected ?l1 ?l2))
    :effect (and (clear ?l2) (not (soft-rock-at ?l2)) (not (gold-at ?l2)) (not (hard_rock_at ?l2)))
  )

  (:action pick_gold
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (arm-empty) (gold-at ?l))
    :effect (and (holding_gold ?r) (not (arm-empty)) (not (gold-at ?l)))
  )

)