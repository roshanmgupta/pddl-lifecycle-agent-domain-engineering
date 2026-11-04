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
    :parameters (?r - robot ?target - tile ?c - tile ?d - color)
    :precondition (and
                   (robot-has ?r ?d)
                   (robot-at ?r ?c)
                   (up ?target ?c)
                   (clear ?target)
                 )
    :effect (and
              (painted ?target ?d)
              (not (clear ?target))
            )
  )
  (:action paint-down
    :parameters (?r - robot ?target - tile ?c - tile ?d - color)
    :precondition (and
                   (robot-has ?r ?d)
                   (robot-at ?r ?c)
                   (down ?target ?c)
                   (clear ?target)
                 )
    :effect (and
              (painted ?target ?d)
              (not (clear ?target))
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
              (not (robot-at ?r ?from))
              (robot-at ?r ?to)
              (clear ?from)
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
              (not (robot-at ?r ?from))
              (robot-at ?r ?to)
              (clear ?from)
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
              (not (robot-at ?r ?from))
              (robot-at ?r ?to)
              (clear ?from)
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
              (not (robot-at ?r ?from))
              (robot-at ?r ?to)
              (clear ?from)
              (not (clear ?to))
            )
  )
)