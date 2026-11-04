(define (domain floor-tile)
  (:requirements :strips :typing)

  (:types
    color location robot tile - object
  )

  (:predicates
    (robot-has ?r - robot ?c - color)
    (robot-at ?r - robot ?l - object)
    (clear ?t - tile)
    (painted ?t - tile ?c - color)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (right ?t1 - tile ?t2 - tile)
    (left ?t1 - tile ?t2 - tile)
    (available-color ?c - color)
  )

  (:action change_color
    :parameters (?r - robot ?old_color - color ?new_color - color)
    :precondition (and (robot-has ?r ?old_color) (available-color ?new_color))
    :effect (and (robot-has ?r ?new_color) (not (robot-has ?r ?old_color)))
  )

  (:action paint_tile_up
    :parameters (?r - robot ?tile_up - tile ?tile_down - tile ?color - color)
    :precondition (and (robot-has ?r ?color) (robot-at ?r ?tile_down) (up ?tile_up ?tile_down) (clear ?tile_up))
    :effect (and (painted ?tile_up ?color) (not (clear ?tile_up)))
  )

  (:action paint_tile_down
    :parameters (?r - robot ?tile_down - tile ?tile_up - tile ?color - color)
    :precondition (and (robot-has ?r ?color) (robot-at ?r ?tile_up) (down ?tile_down ?tile_up) (clear ?tile_down))
    :effect (and (painted ?tile_down ?color) (not (clear ?tile_down)))
  )

  (:action move_robot_up
    :parameters (?r - robot ?tile_from - tile ?tile_to - tile)
    :precondition (and (robot-at ?r ?tile_from) (up ?tile_to ?tile_from) (clear ?tile_to))
    :effect (and (robot-at ?r ?tile_to) (not (robot-at ?r ?tile_from)) (not (clear ?tile_to)))
  )

  (:action move_robot_down
    :parameters (?r - robot ?tile_from - tile ?tile_to - tile)
    :precondition (and (robot-at ?r ?tile_from) (down ?tile_to ?tile_from) (clear ?tile_to))
    :effect (and (robot-at ?r ?tile_to) (not (robot-at ?r ?tile_from)) (not (clear ?tile_to)))
  )

  (:action move_robot_right
    :parameters (?r - robot ?tile_from - tile ?tile_to - tile)
    :precondition (and (robot-at ?r ?tile_from) (right ?tile_to ?tile_from) (clear ?tile_to))
    :effect (and (robot-at ?r ?tile_to) (not (robot-at ?r ?tile_from)) (not (clear ?tile_to)))
  )

  (:action move_robot_left
    :parameters (?r - robot ?tile_from - tile ?tile_to - tile)
    :precondition (and (robot-at ?r ?tile_from) (left ?tile_to ?tile_from) (clear ?tile_to))
    :effect (and (robot-at ?r ?tile_to) (not (robot-at ?r ?tile_from)) (not (clear ?tile_to)))
  )

)