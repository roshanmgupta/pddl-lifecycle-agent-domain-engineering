(define (domain floortile)
  (:requirements :strips :typing)

  (:types
    color robot tile - object
  )

  (:predicates
    (at ?r - robot ?t - tile)
    (has-color ?r - robot ?c - color)
    (available-color ?c - color)
    (clear ?t - tile)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (to-the-right ?t1 - tile ?t2 - tile)
    (to-the-left ?t1 - tile ?t2 - tile)
    (painted ?t - tile ?c - color)
  )

  (:action paint_tile
    :parameters (?r - robot ?t1 - tile ?t2 - tile ?c - color)
    :precondition (and (at ?r ?t1) (has-color ?r ?c) (clear ?t2))
    :effect (and (painted ?t2 ?c) (not (clear ?t2)))
  )

)