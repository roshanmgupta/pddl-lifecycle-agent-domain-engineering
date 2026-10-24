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

  (:action park_car
    :parameters (?car - car ?curb - curb)
    :precondition (and (clear ?curb) (clear ?car))
    :effect (and (at ?car ?curb) (not (clear ?curb)) (not (clear ?car)))
  )

  (:action move_behind
    :parameters (?car1 - car ?car2 - car ?curb - object)
    :precondition (and (at ?car1 ?curb) (at ?car2 ?curb))
    :effect (and (behind ?car1 ?car2) (not (clear ?car1)))
  )

)