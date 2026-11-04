(define (domain floortile)
  (:requirements :strips :typing)

  (:types
    color robot tile - object
  )

  (:predicates
    (at ?r - robot ?t - tile)
    (has ?r - robot ?c - color)
    (available-color ?c - color)
    (clear ?t - tile)
    (painted ?t - tile ?c - color)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (to-right ?t1 - tile ?t2 - tile)
    (to-left ?t1 - tile ?t2 - tile)
  )

  (:action change_color
    :parameters (?r - robot ?c1 - color ?c2 - color)
    :precondition (and (has ?r ?c1) (available-color ?c2))
    :effect (and (has ?r ?c2) (not (has ?r ?c1)))
  )

  (:action paint_tile_up
    :parameters (?r - robot ?t - tile ?c - color ?t2 - tile)
    :precondition (and (has ?r ?c) (at ?r ?t2) (clear ?t) (up ?t ?t2))
    :effect (and (painted ?t ?c) (not (clear ?t)))
  )

  (:action paint_tile_down
    :parameters (?r - robot ?t - tile ?c - color ?t2 - tile)
    :precondition (and (has ?r ?c) (at ?r ?t2) (clear ?t) (down ?t ?t2))
    :effect (and (painted ?t ?c) (not (clear ?t)))
  )

  (:action move_robot
    :parameters (?r - robot ?t1 - tile ?t2 - tile)
    :precondition (and (at ?r ?t1) (clear ?t2) (up ?t2 ?t1))
    :effect (and (at ?r ?t2) (not (at ?r ?t1)) (not (clear ?t2)))
  )

  (:action move_robot_down
    :parameters (?r - robot ?t1 - tile ?t2 - tile)
    :precondition (and (at ?r ?t1) (clear ?t2) (down ?t2 ?t1))
    :effect (and (at ?r ?t2) (not (at ?r ?t1)) (not (clear ?t2)))
  )

  (:action move_robot_right
    :parameters (?r - robot ?t1 - tile ?t2 - tile)
    :precondition (and (at ?r ?t1) (clear ?t2) (to-right ?t1 ?t2))
    :effect (and (at ?r ?t2) (not (at ?r ?t1)) (not (clear ?t2)))
  )

  (:action move_robot_left
    :parameters (?r - robot ?t1 - tile ?t2 - tile)
    :precondition (and (at ?r ?t1) (clear ?t2) (to-left ?t1 ?t2))
    :effect (and (at ?r ?t2) (not (at ?r ?t1)) (not (clear ?t2)))
  )

)