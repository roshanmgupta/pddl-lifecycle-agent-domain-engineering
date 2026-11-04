(define (domain ferry)
  (:requirements :strips :typing)

  (:predicates
    (not-eq ?x - object ?y - object)
    (car ?c - object)
    (location ?l - object)
    (at-ferry ?l - object)
    (at ?c - object ?l - object)
    (empty-ferry)
    (on ?c - object)
    (-eq ?from - object ?to - object)
  )

  (:action sail
    :parameters (?from - object ?to - object)
    :precondition (and (location ?from) (location ?to) (at-ferry ?from))
    :effect (and (at ?to ?from) (not (at-ferry ?from)))
  )

  (:action board
    :parameters (?car - object ?loc - object)
    :precondition (and (car ?car) (location ?loc) (at ?car ?loc) (at-ferry ?loc))
    :effect (and (on ?car) (not (at ?car ?loc)) (not (empty-ferry)))
  )

  (:action debark
    :parameters (?car - object ?loc - object)
    :precondition (and (car ?car) (location ?loc) (on ?car) (at-ferry ?loc))
    :effect (and (at ?car ?loc) (not (empty-ferry)) (not (on ?car)))
  )

)