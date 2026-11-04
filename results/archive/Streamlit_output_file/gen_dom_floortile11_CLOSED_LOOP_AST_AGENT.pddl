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
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (right ?t1 - tile ?t2 - tile)
    (left ?t1 - tile ?t2 - tile)
    (available-color ?new_color - color)
  )

  (:action change_color
    :parameters (?r - robot ?old_color - color ?new_color - color)
    :precondition (and (robot-has ?r ?old_color) (available-color ?new_color))
    :effect (and (robot-has ?r ?new_color) (not (robot-has ?r ?old_color)))
  )

  (:action paint_tile_up
    :parameters (?r - robot ?t_up - tile ?t_down - tile ?color - color)
    :precondition (and (robot-has ?r ?color) (robot-at ?r ?t_down) (up ?t_up ?t_down) (clear ?t_up))
    :effect (and (painted ?t_up ?color) (not (clear ?t_up)))
  )

  (:action paint_tile_down
    :parameters (?r - robot ?t_down - tile ?t_up - tile ?color - color)
    :precondition (and (robot-has ?r ?color) (robot-at ?r ?t_up) (down ?t_down ?t_up) (clear ?t_down))
    :effect (and (painted ?t_down ?color) (not (clear ?t_down)))
  )

  (:action move_robot_up
    :parameters (?r - robot ?t_from - tile ?t_to - tile)
    :precondition (and (robot-at ?r ?t_from) (up ?t_to ?t_from) (clear ?t_to))
    :effect (and (robot-at ?r ?t_to) (not (robot-at ?r ?t_from)) (not (clear ?t_to)) (clear ?t_from))
  )

  (:action move_robot_down
    :parameters (?r - robot ?t_from - tile ?t_to - tile)
    :precondition (and (robot-at ?r ?t_from) (down ?t_to ?t_from) (clear ?t_to))
    :effect (and (robot-at ?r ?t_to) (not (robot-at ?r ?t_from)) (not (clear ?t_to)) (clear ?t_from))
  )

  (:action move_robot_right
    :parameters (?r - robot ?t_from - tile ?t_to - tile)
    :precondition (and (robot-at ?r ?t_from) (right ?t_to ?t_from) (clear ?t_to))
    :effect (and (robot-at ?r ?t_to) (not (robot-at ?r ?t_from)) (not (clear ?t_to)) (clear ?t_from))
  )

  (:action move_robot_left
    :parameters (?r - robot ?t_from - tile ?t_to - tile)
    :precondition (and (robot-at ?r ?t_from) (left ?t_to ?t_from) (clear ?t_to))
    :effect (and (robot-at ?r ?t_to) (not (robot-at ?r ?t_from)) (not (clear ?t_to)) (clear ?t_from))
  )

)