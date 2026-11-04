(define (domain gold-miner-typed)
  (:requirements :strips :typing)

  (:types
    location physical_entity - object
    connected_location loc - location
    bomb gold hard_rock laser robot soft_rock - physical_entity
  )

  (:predicates
    (robot-at ?r - loc)
    (holding ?r - loc ?e - object)
    (arm-empty)
    (connected ?l1 - loc ?l2 - loc)
    (clear ?l - loc)
    (gold-at ?l - loc)
    (soft-rock-at ?l - loc)
    (bomb-at ?l - loc)
    (laser-at ?l - loc)
    (hard-rock-at ?connected_l - loc)
    (holds-gold)
  )

  (:action move_robot
    :parameters (?r - loc ?from - loc ?to - loc)
    :precondition (and (robot-at ?from) (connected ?from ?to) (clear ?to))
    :effect (and (robot-at ?to) (not (robot-at ?from)))
  )

  (:action pick_up_laser
    :parameters (?r - loc ?l - loc ?laser - object)
    :precondition (and (robot-at ?l) (laser-at ?l) (arm-empty))
    :effect (and (holding ?r ?laser) (not (arm-empty)) (not (laser-at ?l)))
  )

  (:action pick_up_bomb
    :parameters (?r - loc ?l - loc ?bomb - object)
    :precondition (and (robot-at ?l) (bomb-at ?l) (arm-empty))
    :effect (and (holding ?r ?bomb) (not (arm-empty)) (not (bomb-at ?l)))
  )

  (:action put_down_laser
    :parameters (?r - loc ?l - loc ?laser - object)
    :precondition (and (robot-at ?l) (holding ?r ?laser))
    :effect (and (arm-empty) (laser-at ?l) (not (holding ?r ?laser)))
  )

  (:action detonate_bomb
    :parameters (?r - loc ?l - loc ?connected_l - loc ?bomb - object)
    :precondition (and (robot-at ?l) (holding ?r ?bomb) (connected ?l ?connected_l) (soft-rock-at ?connected_l))
    :effect (and (arm-empty) (clear ?connected_l) (not (holding ?r ?bomb)) (not (soft-rock-at ?connected_l)))
  )

  (:action fire_laser
    :parameters (?r - loc ?l - loc ?connected_l - loc ?laser - object)
    :precondition (and (robot-at ?l) (holding ?r ?laser) (connected ?l ?connected_l))
    :effect (and (clear ?connected_l) (not (soft-rock-at ?connected_l)) (not (gold-at ?connected_l)) (not (hard-rock-at ?connected_l)))
  )

  (:action pick_gold
    :parameters (?r - loc ?l - loc ?gold - object)
    :precondition (and (robot-at ?l) (arm-empty) (gold-at ?l))
    :effect (and (holding ?r ?gold) (not (arm-empty)) (holds-gold))
  )

)