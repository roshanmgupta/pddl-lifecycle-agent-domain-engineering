(define (domain parking)
  (:requirements :strips :typing)

  (:types
    car curb - object
  )

  (:predicates
    (at-curb ?c - car)
    (at-curb-num ?c - car ?curb - curb)
    (behind-car ?c1 - car ?c2 - car)
    (clear-car ?c - car)
    (clear-curb ?curb - curb)
    (car-clear ?x1 - car)
    (curb-clear ?x1 - curb)
  )

  (:action move_curb_to_curb
    :parameters (?a - car ?b - curb ?c - curb)
    :precondition (and (clear-car ?a) (clear-curb ?c) (at-curb-num ?a ?b))
    :effect (and (not (at-curb-num ?a ?b)) (at-curb-num ?a ?c) (clear-curb ?b) (not (clear-curb ?c)))
  )

  (:action move_curb_to_behind
    :parameters (?a - car ?b - curb ?c - car)
    :precondition (and (clear-car ?a) (clear-car ?c) (at-curb-num ?a ?b) (at-curb ?c))
    :effect (and (not (at-curb-num ?a ?b)) (behind-car ?a ?c) (clear-curb ?b) (not (clear-car ?c)))
  )

  (:action move_behind_to_curb
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and (clear-car ?a) (clear-curb ?c) (behind-car ?a ?b))
    :effect (and (not (behind-car ?a ?b)) (at-curb-num ?a ?c) (clear-car ?b) (not (clear-curb ?c)))
  )

  (:action move_behind_to_behind
    :parameters (?a - car ?b - car ?c - car)
    :precondition (and (clear-car ?a) (clear-car ?c) (behind-car ?a ?b) (at-curb ?c))
    :effect (and (not (behind-car ?a ?b)) (behind-car ?a ?c) (clear-car ?b) (not (clear-car ?c)))
  )

)