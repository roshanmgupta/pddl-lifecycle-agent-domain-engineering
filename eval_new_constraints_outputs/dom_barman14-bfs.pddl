(define (domain barman14-bfs)
  (:requirements :strips :typing)

  (:types
    cocktail container device location manipulator material surface - object
    shaker shot - container
    hand - manipulator
    ingredient - material
    dispenser - device
    level - location
    table - surface
  )

  (:predicates
    (on ?x - container ?y - surface)
    (clean ?x - container)
    (empty ?x - container)
    (dispenses ?d - object ?i - object)
    (next-to ?l1 - location ?l2 - location)
    (part-of ?c - cocktail ?i - object)
    (contains ?s - container ?c - cocktail)
    (has-empty-hand ?h - manipulator)
  )

  (:action fill-shot
    :parameters (?s - container ?c - cocktail ?d - object ?i - object)
    :precondition (and (empty ?s) (part-of ?c ?i) (dispenses ?d ?i))
    :effect (and (not (empty ?s)) (contains ?s ?c))
  )

)