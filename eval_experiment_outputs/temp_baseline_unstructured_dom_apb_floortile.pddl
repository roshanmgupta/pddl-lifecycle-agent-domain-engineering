(define (domain floor-tile)
  (:requirements :strips :typing)
  (:types
    robot tile color - object
  )
  (:predicates
    (robot-at ?r - robot ?t - tile)
    (robot-has ?r - robot ?c - color)
    (available-color ?c - color)
    (clear ?t - tile)
    (painted ?t - tile ?c - color)
    (up ?t1 - tile ?t2 - tile)
    (down ?t1 - tile ?t2 - tile)
    (right ?t1 - tile ?t2 - tile)
    (left ?t1 - tile ?t2 - tile)
  )
  (:action change-color
    :parameters (?r - robot ?from - color ?to - color)
    :precondition (and
      (robot-has ?r ?from)
      (available-color ?to)
    )
    :effect (and
      (not (robot-has ?r ?from))
      (robot-has ?r ?to)
    )
  )
  (:action paint-up
    :parameters (?r - robot ?t - tile ?c - tile ?col - color)
    :precondition (and
      (robot-has ?r ?col)
      (robot-at ?r ?c)
      (up ?t ?c)
      (clear ?t)
    )
    :effect (and
      (painted ?t ?col)
      (not (clear ?t))
    )
  )
  (:action paint-down
    :parameters (?r - robot ?t - tile ?c - tile ?col - color)
    :precondition (and
      (robot-has ?r ?col)
      (robot-at ?r ?c)
      (down ?t ?c)
      (clear ?t)
    )
    :effect (and
      (painted ?t ?col)
      (not (clear ?t))
    )
  )
  (:action move-up
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and
      (robot-at ?r ?from)
      (up ?to ?from)
      (clear ?to)
    )
    :effect (and
      (robot-at ?r ?to)
      (clear ?from)
      (not (robot-at ?r ?from))
      (not (clear ?to))
    )
  )
  (:action move-down
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and
      (robot-at ?r ?from)
      (down ?to ?from)
      (clear ?to)
    )
    :effect (and
      (robot-at ?r ?to)
      (clear ?from)
      (not (robot-at ?r ?from))
      (not (clear ?to))
    )
  )
  (:action move-right
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and
      (robot-at ?r ?from)
      (right ?to ?from)
      (clear ?to)
    )
    :effect (and
      (robot-at ?r ?to)
      (clear ?from)
      (not (robot-at ?r ?from))
      (not (clear ?to))
    )
  )
  (:action move-left
    :parameters (?r - robot ?from - tile ?to - tile)
    :precondition (and
      (robot-at ?r ?from)
      (left ?to ?from)
      (clear ?to)
    )
    :effect (and
      (robot-at ?r ?to)
      (clear ?from)
      (not (robot-at ?r ?from))
      (not (clear ?to))
    )
  )
)