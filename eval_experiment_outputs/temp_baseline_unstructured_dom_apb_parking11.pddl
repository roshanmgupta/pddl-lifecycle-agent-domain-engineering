(define (domain parking)
  (:requirements :strips :typing)
  (:types car curb - object)
  
  (:predicates
    (at-curb ?c - car)
    (at-curb-num ?c - car ?curb - curb)
    (behind-car ?c1 - car ?c2 - car)
    (car-clear ?c - car)
    (curb-clear ?curb - curb)
  )

  (:action move-to-curb
    :parameters (?a - car ?b - curb ?c - curb)
    :precondition (and
      (car-clear ?a)
      (curb-clear ?c)
      (at-curb ?a)
      (at-curb-num ?a ?b)
    )
    :effect (and
      (not (at-curb ?a))
      (not (at-curb-num ?a ?b))
      (at-curb ?a)
      (at-curb-num ?a ?c)
      (curb-clear ?b)
    )
  )

  (:action move-behind-car
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and
      (car-clear ?a)
      (car-clear ?b)
      (at-curb ?a)
      (at-curb-num ?b ?c)
      (behind-car ?b ?a)
    )
    :effect (and
      (not (at-curb ?a))
      (not (at-curb-num ?a ?b))
      (behind-car ?a ?b)
      (not (car-clear ?b))
    )
  )

  (:action move-from-behind-to-curb
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and
      (car-clear ?a)
      (curb-clear ?c)
      (behind-car ?a ?b)
    )
    :effect (and
      (not (behind-car ?a ?b))
      (at-curb ?a)
      (at-curb-num ?a ?c)
      (not (curb-clear ?c))
      (car-clear ?b)
    )
  )

  (:action move-from-behind-to-behind
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and
      (car-clear ?a)
      (car-clear ?b)
      (behind-car ?a ?b)
      (at-curb ?b)
      (curb-clear ?c)
    )
    :effect (and
      (not (behind-car ?a ?b))
      (behind-car ?a ?b)
      (not (car-clear ?b))
      (not (curb-clear ?c))
    )
  )
)