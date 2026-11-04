(define (domain parking)
  (:requirements :strips :typing)

  (:types
    car curb physical_entity - object
  )

  (:predicates
    (at-curb ?c - car)
    (at-curb-num ?c - car ?curb - curb)
    (behind-car ?c1 - car ?c2 - car)
    (car-clear ?c - car)
    (curb-clear ?curb - object)
  )

  (:action move_car_to_curb
    :parameters (?car - car ?from-curb - curb ?to-curb - curb)
    :precondition (and (car-clear ?car) (curb-clear ?to-curb) (curb-clear ?from-curb))
    :effect (and (not (curb-clear ?to-curb)) (not (at-curb-num ?car ?from-curb)) (at-curb ?car) (at-curb-num ?car ?to-curb) (curb-clear ?from-curb))
  )

  (:action move_car_behind_car
    :parameters (?car - car ?from-curb - curb ?to-car - car ?clear-car - car)
    :precondition (and (car-clear ?car) (car-clear ?to-car) (at-curb-num ?car ?from-curb) (at-curb ?to-car))
    :effect (and (not (car-clear ?to-car)) (not (at-curb-num ?car ?from-curb)) (behind-car ?car ?to-car) (curb-clear ?from-curb))
  )

  (:action move_car_to_curb_from_behind
    :parameters (?car - car ?from-car - car ?to-curb - curb ?clear-car - car)
    :precondition (and (car-clear ?car) (curb-clear ?to-curb) (behind-car ?car ?from-car))
    :effect (and (not (curb-clear ?to-curb)) (not (behind-car ?car ?from-car)) (at-curb ?car) (at-curb-num ?car ?to-curb) (curb-clear ?from-car))
  )

  (:action move_car_behind_car_from_behind
    :parameters (?car - car ?from-car - car ?to-car - car ?clear-car - car)
    :precondition (and (car-clear ?car) (car-clear ?to-car) (behind-car ?car ?from-car) (at-curb ?to-car))
    :effect (and (not (car-clear ?to-car)) (not (behind-car ?car ?from-car)) (behind-car ?car ?to-car) (curb-clear ?from-car))
  )

)