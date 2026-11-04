(define (domain floor-tile)
  (:requirements :strips :typing)

  (:types
    color robot tile - object
  )

  (:predicates
    (robot-has ?r - robot ?c - color)
    (available-color ?c - color)
    (robot-at ?r - robot ?t - tile)
    (clear ?t - tile)
    (painted ?t - tile ?c - color)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (right ?t1 - tile ?t2 - tile)
    (left ?t1 - tile ?t2 - tile)
  )

  (:action change_color
    :parameters (?a - robot ?b - color ?c - color)
    :precondition (and (robot-has ?a ?b) (available-color ?c))
    :effect (and (not (robot-has ?a ?b)) (robot-has ?a ?c))
  )

  (:action paint_up
    :parameters (?a - robot ?b - tile ?c - tile ?d - color)
    :precondition (and (robot-has ?a ?d) (robot-at ?a ?c) (up ?b ?c) (clear ?b))
    :effect (and (painted ?b ?d) (not (clear ?b)))
  )

  (:action paint_down
    :parameters (?a - robot ?b - tile ?c - tile ?d - color)
    :precondition (and (robot-has ?a ?d) (robot-at ?a ?c) (down ?b ?c) (clear ?b))
    :effect (and (painted ?b ?d) (not (clear ?b)))
  )

  (:action move_up
    :parameters (?a - robot ?b - tile ?c - tile)
    :precondition (and (robot-at ?a ?b) (up ?c ?b) (clear ?c))
    :effect (and (not (robot-at ?a ?b)) (robot-at ?a ?c) (clear ?b) (not (clear ?c)))
  )

  (:action move_down
    :parameters (?a - robot ?b - tile ?c - tile)
    :precondition (and (robot-at ?a ?b) (down ?c ?b) (clear ?c))
    :effect (and (not (robot-at ?a ?b)) (robot-at ?a ?c) (clear ?b) (not (clear ?c)))
  )

  (:action move_right
    :parameters (?a - robot ?b - tile ?c - tile)
    :precondition (and (robot-at ?a ?b) (right ?c ?b) (clear ?c))
    :effect (and (not (robot-at ?a ?b)) (robot-at ?a ?c) (clear ?b) (not (clear ?c)))
  )

  (:action move_left
    :parameters (?a - robot ?b - tile ?c - tile)
    :precondition (and (robot-at ?a ?b) (left ?c ?b) (clear ?c))
    :effect (and (not (robot-at ?a ?b)) (robot-at ?a ?c) (clear ?b) (not (clear ?c)))
  )

)