(define (domain barman)
  (:requirements :strips :typing)

  (:types
    beverage container dispenser hand level - object
    cocktail ingredient - beverage
    shaker shot - container
  )

  (:predicates
    (holding ?h - hand ?c - container)
    (ontable ?c - container)
    (empty ?c - object)
    (contains ?c - container ?b - beverage)
    (dispenses ?d - dispenser ?b - beverage)
    (clean ?c - container)
    (used-by ?c - container ?b - beverage)
    (unshaken ?c - container)
    (shaken ?c - container)
    (at-level ?c - container ?l - level)
    (next ?l1 - level ?l2 - level)
    (handempty ?h - hand)
    (shaker-empty-level ?sh - shaker ?l - level)
    (shaker-level ?sh - shaker ?l - level)
    (cocktail-part1 ?c - cocktail ?i - ingredient)
    (cocktail-part2 ?c - cocktail ?i - ingredient)
  )

  (:action grasp
    :parameters (?h - hand ?c - container)
    :precondition (and (ontable ?c) (empty ?h))
    :effect (and (holding ?h ?c) (not (ontable ?c)) (not (empty ?h)))
  )

  (:action leave
    :parameters (?h - hand ?c - container)
    :precondition (holding ?h ?c)
    :effect (and (empty ?h) (ontable ?c) (not (holding ?h ?c)))
  )

  (:action fill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (dispenses ?d ?i) (empty ?s) (clean ?s))
    :effect (and (contains ?s ?i) (used-by ?s ?i) (not (empty ?s)) (not (clean ?s)))
  )

  (:action refill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (dispenses ?d ?i) (empty ?s) (used-by ?s ?i))
    :effect (and (contains ?s ?i) (not (empty ?s)))
  )

  (:action empty_shot
    :parameters (?h - hand ?s - shot ?b - beverage)
    :precondition (and (holding ?h ?s) (contains ?s ?b))
    :effect (and (empty ?s) (not (contains ?s ?b)))
  )

  (:action clean_shot
    :parameters (?h1 - hand ?s - shot ?b - beverage ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (empty ?s) (used-by ?s ?b))
    :effect (and (clean ?s) (not (used-by ?s ?b)))
  )

  (:action pour_into_clean_shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (empty ?sh) (clean ?sh) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (empty ?s) (contains ?sh ?i) (unshaken ?sh) (at-level ?sh ?l2) (not (contains ?s ?i)) (not (empty ?sh)) (not (clean ?sh)) (not (at-level ?sh ?l1)))
  )

  (:action pour_into_used_shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (unshaken ?sh) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?sh ?i) (empty ?s) (at-level ?sh ?l2) (not (contains ?s ?i)) (not (at-level ?sh ?l1)))
  )

  (:action empty_shaker
    :parameters (?h - hand ?sh - shaker ?c - cocktail ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (contains ?sh ?c) (shaken ?sh) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (empty ?sh) (at-level ?sh ?l2) (not (shaken ?sh)) (not (at-level ?sh ?l1)) (not (contains ?sh ?c)))
  )

  (:action clean_shaker
    :parameters (?h1 - hand ?sh - shaker ?h2 - hand)
    :precondition (and (holding ?h1 ?sh) (empty ?h2) (empty ?sh))
    :effect (clean ?sh)
  )

  (:action shake
    :parameters (?c - cocktail ?sh - shaker ?h1 - hand ?h2 - hand ?i1 - ingredient ?i2 - ingredient)
    :precondition (and (holding ?h1 ?sh) (empty ?h2) (contains ?sh ?i1) (contains ?sh ?i2) (unshaken ?sh) (cocktail-part1 ?c ?i1) (cocktail-part2 ?c ?i2))
    :effect (and (shaken ?sh) (contains ?sh ?c) (not (unshaken ?sh)) (not (contains ?sh ?i1)) (not (contains ?sh ?i2)))
  )

  (:action pour_from_shaker
    :parameters (?b - beverage ?sh - shaker ?h - hand ?s - shot ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (shaken ?sh) (empty ?s) (clean ?s) (contains ?sh ?b) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?s ?b) (at-level ?sh ?l2) (not (clean ?s)) (not (empty ?s)) (not (at-level ?sh ?l1)))
  )

)