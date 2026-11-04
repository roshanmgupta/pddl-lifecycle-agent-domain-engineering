(define (domain floor-tile)
  (:requirements :strips :typing)

  (:types
    color robot tile - object
  )

  (:predicates
    (robot-at ?r - object ?x - object)
    (up ?x - object ?y - object)
    (down ?x - object ?y - object)
    (right ?x - object ?y - object)
    (left ?x - object ?y - object)
    (clear ?x - object)
    (painted ?x - object ?c - object)
    (robot-has ?r - object ?c - object)
    (available-color ?c - object)
    (free-color ?r - object)
  )

  (:action change-color
    :parameters (?r - robot ?c - color ?c2 - color)
    :precondition (and (robot-has ?r ?c) (available-color ?c2))
    :effect (and (robot-has ?r ?c2) (not (robot-has ?r ?c)))
  )

  (:action paint-up
    :parameters (?r - robot ?y - tile ?x - tile ?c - color)
    :precondition (and (robot-has ?r ?c) (robot-at ?r ?x) (clear ?y))
    :effect (and (painted ?y ?c) (not (clear ?y)))
  )

  (:action paint-down
    :parameters (?r - robot ?y - tile ?x - tile ?c - color)
    :precondition (and (robot-has ?r ?c) (robot-at ?r ?x) (down ?y ?x) (up ?x ?y) (clear ?y))
    :effect (and (painted ?y ?c) (not (clear ?y)))
  )

  (:action up
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (up ?x ?y) (clear ?y))
    :effect (and (robot-at ?r ?y) (clear ?x) (not (robot-at ?r ?x)) (not (clear ?y)))
  )

  (:action down
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (down ?x ?y) (clear ?y))
    :effect (and (robot-at ?r ?y) (clear ?x) (not (robot-at ?r ?x)) (not (clear ?y)))
  )

  (:action right
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (right ?x ?y) (clear ?y))
    :effect (and (robot-at ?r ?y) (clear ?x) (not (robot-at ?r ?x)) (not (clear ?y)))
  )

  (:action left
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (left ?x ?y) (clear ?y))
    :effect (and (robot-at ?r ?y) (clear ?x) (not (robot-at ?r ?x)) (not (clear ?y)))
  )

)