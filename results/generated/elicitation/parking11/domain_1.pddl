(define (domain parking11)
  (:requirements :strips :typing)

  (:types
    car curb - object
  )

  (:predicates
    (at ?c - car ?curb - object)
    (behind ?c1 - car ?c2 - car)
    (clear ?curb - object)
  )

  (:action move_to_curb
    :parameters (?car - car ?from - curb ?to - curb)
    :precondition (and (clear ?car) (clear ?to) (at ?car ?from))
    :effect (and (clear ?from) (at ?car ?to) (not (at ?car ?from)) (not (clear ?to)))
  )

  (:action move_behind_car
    :parameters (?car - car ?from - curb ?to - car ?curb - object)
    :precondition (and (clear ?car) (clear ?to) (at ?car ?from) (at ?to ?curb))
    :effect (and (clear ?from) (behind ?car ?to) (not (at ?car ?from)) (not (clear ?to)))
  )

  (:action move_to_curb_from_behind
    :parameters (?car - car ?from - car ?to - curb)
    :precondition (and (clear ?car) (clear ?to) (behind ?car ?from))
    :effect (and (clear ?from) (at ?car ?to) (not (behind ?car ?from)) (not (clear ?to)))
  )

  (:action move_behind_car_from_behind
    :parameters (?car - car ?from - car ?to - car ?curb - object)
    :precondition (and (clear ?car) (clear ?to) (behind ?car ?from) (at ?to ?curb))
    :effect (and (clear ?from) (behind ?car ?to) (not (behind ?car ?from)) (not (clear ?to)))
  )

)