(define (domain floor-tile)
  (:requirements :typing)

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
    :effect (and (not (robot-has ?r ?c)) (robot-has ?r ?c2))
  )

  (:action paint-up
    :parameters (?r - robot ?y - tile ?x - tile ?c - color)
    :precondition (and (robot-has ?r ?c) (robot-at ?r ?x) (up ?y ?x) (clear ?y))
    :effect (and (not (clear ?y)) (painted ?y ?c))
  )

  (:action paint-down
    :parameters (?r - robot ?y - tile ?x - tile ?c - color)
    :precondition (and (robot-has ?r ?c) (robot-at ?r ?x) (down ?y ?x) (clear ?y))
    :effect (and (not (clear ?y)) (painted ?y ?c))
  )

  (:action up
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (up ?y ?x) (clear ?y))
    :effect (and (robot-at ?r ?y) (not (robot-at ?r ?x)) (clear ?x) (not (clear ?y)))
  )

  (:action down
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (down ?y ?x) (clear ?y))
    :effect (and (robot-at ?r ?y) (not (robot-at ?r ?x)) (clear ?x) (not (clear ?y)))
  )

  (:action right
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (right ?y ?x) (clear ?y))
    :effect (and (robot-at ?r ?y) (not (robot-at ?r ?x)) (clear ?x) (not (clear ?y)))
  )

  (:action left
    :parameters (?r - robot ?x - tile ?y - tile)
    :precondition (and (robot-at ?r ?x) (left ?y ?x) (clear ?y))
    :effect (and (robot-at ?r ?y) (not (robot-at ?r ?x)) (clear ?x) (not (clear ?y)))
  )

)