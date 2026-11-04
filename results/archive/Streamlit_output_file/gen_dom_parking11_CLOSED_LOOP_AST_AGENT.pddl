(define (domain parking)
  (:requirements :strips :typing)

  (:types
    car curb physical_entity - object
  )

  (:predicates
    (car-clear ?a - car)
    (curb-clear ?c - curb)
    (at-curb-num ?a - car ?c - object)
    (behind-car ?a - car ?b - object)
    (clear ?b - object)
    (at-curb ?x1 - car)
  )

  (:action move-car-to-curb
    :parameters (?a - car ?b - curb ?c - curb)
    :precondition (and (car-clear ?a) (curb-clear ?c) (at-curb-num ?a ?b))
    :effect (and (not (at-curb-num ?a ?b)) (at-curb-num ?a ?c) (not (curb-clear ?c)) (clear ?b))
  )

  (:action move-car-behind-car
    :parameters (?a - car ?b - curb ?c - car)
    :precondition (and (car-clear ?a) (car-clear ?c) (at-curb-num ?a ?b) (at-curb-num ?c ?b))
    :effect (and (not (at-curb-num ?a ?b)) (behind-car ?a ?c) (not (car-clear ?c)))
  )

  (:action move-car-to-curb-from-behind
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and (car-clear ?a) (curb-clear ?c) (behind-car ?a ?b))
    :effect (and (not (behind-car ?a ?b)) (at-curb-num ?a ?c) (not (curb-clear ?c)) (clear ?b))
  )

  (:action move-car-behind-car-from-behind
    :parameters (?a - car ?b - car ?c - curb)
    :precondition (and (car-clear ?a) (curb-clear ?c) (behind-car ?a ?b) (at-curb-num ?b ?c))
    :effect (and (not (behind-car ?a ?b)) (behind-car ?a ?c) (not (curb-clear ?c)) (not (at-curb-num ?a ?b)))
  )

)