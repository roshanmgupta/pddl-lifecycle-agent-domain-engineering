(define (domain bartending)
  (:requirements :strips :typing :negative-preconditions)
  (:types
    object
    hand - object
    level - object
    beverage - object
    dispenser - object
    container - object
    ingredient - beverage
    cocktail - beverage
    shot - container
    shaker - container
  )
  (:predicates
    (on-table ?x - container)
    (holding ?h - hand ?c - container)
    (empty ?h - hand)
    (dispenses ?d - dispenser ?i - ingredient)
    (contains ?c - container ?b - beverage)
    (empty-container ?c - container)
    (clean ?c - container)
    (used-by ?c - container ?b - beverage)
    (unshaken ?s - shaker)
    (shaken ?s - shaker)
    (at-level ?s - shaker ?l - level)
    (next ?l1 - level ?l2 - level)
    (part-of ?i - ingredient ?c - cocktail)
  )
  (:action grasp
    :parameters (?h - hand ?c - container)
    :precondition (and (on-table ?c) (empty ?h))
    :effect (and (holding ?h ?c) (not (on-table ?c)) (not (empty ?h)))
  )
  (:action leave
    :parameters (?h - hand ?c - container)
    :precondition (holding ?h ?c)
    :effect (and (empty ?h) (on-table ?c) (not (holding ?h ?c)))
  )
  (:action fill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (dispenses ?d ?i) (empty-container ?s) (clean ?s))
    :effect (and (contains ?s ?i) (used-by ?s ?i) (not (empty-container ?s)) (not (clean ?s)))
  )
  (:action refill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (dispenses ?d ?i) (empty-container ?s) (used-by ?s ?i))
    :effect (and (contains ?s ?i) (not (empty-container ?s)))
  )
  (:action empty-shot
    :parameters (?h - hand ?s - shot ?b - beverage)
    :precondition (and (holding ?h ?s) (contains ?s ?b))
    :effect (and (empty-container ?s) (not (contains ?s ?b)))
  )
  (:action clean-shot
    :parameters (?s - shot ?b - beverage ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (empty ?h2) (empty-container ?s) (used-by ?s ?b))
    :effect (and (clean ?s) (not (used-by ?s ?b)))
  )
  (:action pour-clean-shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (empty-container ?sh) (clean ?sh) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (empty-container ?s) (contains ?sh ?i) (unshaken ?sh) (at-level ?sh ?l2) (not (contains ?s ?i)) (not (empty-container ?sh)) (not (clean ?sh)) (not (at-level ?sh ?l1)))
  )
  (:action pour-used-shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (unshaken ?sh) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?sh ?i) (empty-container ?s) (at-level ?sh ?l2) (not (contains ?s ?i)) (not (at-level ?sh ?l1)))
  )
  (:action empty-shaker
    :parameters (?h - hand ?sh - shaker ?c - cocktail ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (contains ?sh ?c) (shaken ?sh) (at-level ?sh ?l1) (at-level ?sh ?l2))
    :effect (and (at-level ?sh ?l2) (empty-container ?sh) (not (shaken ?sh)) (not (at-level ?sh ?l1)) (not (contains ?sh ?c)))
  )
  (:action clean-shaker
    :parameters (?sh - shaker ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?sh) (empty ?h2) (empty-container ?sh))
    :effect (clean ?sh)
  )
  (:action shake
    :parameters (?c - cocktail ?sh - shaker ?h1 - hand ?h2 - hand ?i1 - ingredient ?i2 - ingredient)
    :precondition (and (holding ?h1 ?sh) (empty ?h2) (contains ?sh ?i1) (contains ?sh ?i2) (part-of ?i1 ?c) (part-of ?i2 ?c) (unshaken ?sh))
    :effect (and (shaken ?sh) (contains ?sh ?c) (not (unshaken ?sh)) (not (contains ?sh ?i1)) (not (contains ?sh ?i2)))
  )
  (:action pour-beverage
    :parameters (?b - beverage ?sh - shaker ?h - hand ?s - shot ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (shaken ?sh) (empty-container ?s) (clean ?s) (contains ?sh ?b) (at-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?s ?b) (at-level ?sh ?l2) (not (clean ?s)) (not (empty-container ?s)) (not (at-level ?sh ?l1)))
  )
)