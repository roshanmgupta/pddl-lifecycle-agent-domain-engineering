(define (domain floor-tile)
  (:requirements :strips :typing)
  (:types robot tile color)
  
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
    :parameters (?r - robot ?c1 - color ?c2 - color)
    :precondition (and 
      (robot-has ?r ?c1) 
      (available-color ?c2)
    )
    :effect (and 
      (not (robot-has ?r ?c1)) 
      (robot-has ?r ?c2)
    )
  )

  (:action paint
    :parameters (?r - robot ?t - tile ?c - color ?t2 - tile)
    :precondition (and 
      (robot-has ?r ?c) 
      (robot-at ?r ?t2) 
      (clear ?t) 
      (or (up ?t ?t2) (down ?t ?t2))
    )
    :effect (and 
      (painted ?t ?c) 
      (not (clear ?t))
    )
  )

  (:action move
    :parameters (?r - robot ?t1 - tile ?t2 - tile)
    :precondition (and 
      (robot-at ?r ?t1) 
      (clear ?t2) 
      (or (up ?t2 ?t1) (down ?t2 ?t1) (right ?t2 ?t1) (left ?t2 ?t1))
    )
    :effect (and 
      (not (robot-at ?r ?t1)) 
      (robot-at ?r ?t2) 
      (not (clear ?t2))
    )
  )
)