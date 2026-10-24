(define (domain gold-miner-typed)
  (:requirements :strips :typing)

  (:constants laser bomb gold - object)
  (:types
    bomb gold hard_rock laser location robot soft_rock - object
  )

  (:predicates
    (at ?r - robot ?l - location)
    (connected ?l1 - object ?l2 - object)
    (holding ?r - robot ?o - object)
    (clear ?l - object)
    (arm-empty ?r - robot)
    (has-soft-rock ?l - location)
    (has-hard-rock ?l - location)
    (has-laser ?l - location)
    (has-bomb ?l - location)
    (has-gold ?l - location)
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
    :effect (and (at ?r ?to) (not (at ?r ?from)))
  )

  (:action pick_up_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (laser-at ?l) (arm-empty ?r))
    :effect (and (holding ?r laser) (not (arm-empty ?r)) (not (laser-at ?l)))
  )

  (:action pick_up_bomb
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (bomb-at ?l) (arm-empty ?r))
    :effect (and (holding ?r bomb) (not (arm-empty ?r)))
  )

  (:action put_down_laser
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (holding ?r laser))
    :effect (and (arm-empty ?r) (laser-at ?l) (not (holding ?r laser)))
  )

  (:action detonate_bomb
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding ?r bomb) (connected ?l1 ?l2) (has-soft-rock ?l2))
    :effect (and (arm-empty ?r) (clear ?l2) (not (holding ?r bomb)) (not (has-soft-rock ?l2)))
  )

  (:action fire_laser
    :parameters (?r - robot ?l1 - location ?l2 - location)
    :precondition (and (at ?r ?l1) (holding ?r laser) (connected ?l1 ?l2))
    :effect (and (clear ?l2) (not (has-soft-rock ?l2)) (not (has-gold ?l2)) (not (has-hard-rock ?l2)))
  )

  (:action pick_gold
    :parameters (?r - robot ?l - location)
    :precondition (and (at ?r ?l) (arm-empty ?r) (gold-at ?l))
    :effect (and (holding ?r gold) (not (arm-empty ?r)))
  )

)