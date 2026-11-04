(define (domain floor-tile)
  (:requirements :strips :typing)

  (:types
    color location robot tile - object
  )

  (:predicates
    (robot-has ?r - robot ?c - color)
    (robot-at ?r - robot ?t - tile)
    (painted ?t - tile ?c - color)
    (clear ?t - tile)
    (available-color ?c - color)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (right ?t1 - tile ?t2 - tile)
    (left ?t1 - tile ?t2 - tile)
  )

  (:action change_color
    :parameters (?r - robot ?old_color - color ?new_color - color)
    :precondition (and (robot-has ?r ?old_color) (available-color ?new_color))
    :effect (and (robot-has ?r ?new_color) (not (robot-has ?r ?old_color)))
  )

  (:action paint_tile
    :parameters (?r - robot ?t - tile ?color - color ?location - tile)
    :precondition (and (robot-has ?r ?color) (robot-at ?r ?location) (clear ?t) (up ?t ?location))
    :effect (and (painted ?t ?color) (not (clear ?t)))
  )

  (:action move_robot
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and (robot-at ?r ?from) (up ?to ?from) (clear ?to))
    :effect (and (robot-at ?r ?to) (not (robot-at ?r ?from)) (not (clear ?to)))
  )

  (:action move_robot_up
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and (robot-at ?r ?from) (up ?to ?from) (clear ?to))
    :effect (and (robot-at ?r ?to) (not (robot-at ?r ?from)) (not (clear ?to)))
  )

  (:action move_robot_down
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and (robot-at ?r ?from) (down ?to ?from) (clear ?to))
    :effect (and (robot-at ?r ?to) (not (robot-at ?r ?from)) (not (clear ?to)))
  )

  (:action move_robot_right
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and (robot-at ?r ?from) (clear ?to))
    :effect (and (robot-at ?r ?to) (not (robot-at ?r ?from)) (not (clear ?to)))
  )

  (:action move_robot_left
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and (robot-at ?r ?from) (clear ?to))
    :effect (and (robot-at ?r ?to) (not (robot-at ?r ?from)) (not (clear ?to)))
  )

)