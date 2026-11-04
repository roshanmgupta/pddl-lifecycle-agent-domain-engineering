(define (domain barman)
  (:requirements :strips :typing)

  (:types
    beverage container dispenser hand level - object
    cocktail ingredient - beverage
    shaker shot - container
  )

  (:predicates
    (ontable ?b - container)
    (handempty ?h - object)
    (holding ?h - hand ?b - container)
    (contains ?c - container ?b - beverage)
    (clean ?c - container)
    (used-by ?c - container ?b - object)
    (shaken ?c - shaker)
    (unshaken ?c - shaker)
    (shaker-level ?c - container ?l - level)
    (next ?l1 - level ?l2 - level)
    (empty ?c - object)
    (dispenses ?e - dispenser ?b - beverage)
    (on-table ?b - container)
    (shaker-empty-level ?x1 - shaker ?x2 - level)
    (cocktail-part1 ?x1 - cocktail ?x2 - ingredient)
    (cocktail-part2 ?x1 - cocktail ?x2 - ingredient)
  )

  (:action grasp-container
    :parameters (?a - hand ?b - container)
    :precondition (and (ontable ?b) (handempty ?a))
    :effect (and (holding ?a ?b) (not (ontable ?b)) (not (handempty ?a)))
  )

  (:action leave-container
    :parameters (?a - hand ?b - container)
    :precondition (holding ?a ?b)
    :effect (and (empty ?a) (on-table ?b) (not (holding ?a ?b)))
  )

  (:action fill-shot
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (empty ?d) (dispenses ?e ?b) (empty ?a) (clean ?a))
    :effect (and (contains ?a ?b) (used-by ?a ?b) (not (empty ?a)) (not (clean ?a)))
  )

  (:action refill-shot
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (empty ?d) (dispenses ?e ?b) (contains ?a ?b))
    :effect (and (contains ?a ?b) (not (empty ?a)))
  )

  (:action empty-shot
    :parameters (?a - shot ?c - hand ?b - object)
    :precondition (and (holding ?c ?a) (used-by ?a ?b))
    :effect (and (empty ?a) (not (used-by ?a ?b)))
  )

  (:action clean-shot
    :parameters (?a - shot ?b - beverage ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (empty ?d) (empty ?a) (used-by ?a ?b))
    :effect (and (clean ?a) (not (used-by ?a ?b)))
  )

  (:action pour-into-clean-shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (used-by ?a ?b) (empty ?c) (clean ?c) (shaker-level ?c ?e) (next ?e ?f))
    :effect (and (handempty ?a) (contains ?c ?b) (unshaken ?c) (shaker-level ?c ?f))
  )

  (:action pour-into-used-shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (contains ?a ?b) (unshaken ?c) (shaker-level ?c ?e) (next ?e ?f))
    :effect (and (contains ?c ?b) (empty ?a) (shaker-level ?c ?f))
  )

  (:action empty-shaker
    :parameters (?b - shaker ?c - cocktail ?a - hand ?d - level ?e - level)
    :precondition (and (holding ?a ?b) (contains ?b ?c) (unshaken ?b) (shaker-level ?b ?d) (next ?d ?e))
    :effect (and (shaker-level ?b ?e) (empty ?b) (not (unshaken ?b)) (not (contains ?b ?c)))
  )

  (:action clean-shaker
    :parameters (?c - shaker ?a - hand ?b - hand)
    :precondition (and (holding ?a ?c) (handempty ?b))
    :effect (clean ?c)
  )

  (:action shake-cocktail
    :parameters (?a - cocktail ?d - shaker ?e - hand ?f - hand ?b - ingredient ?c - ingredient)
    :precondition (and (holding ?e ?d) (handempty ?f) (contains ?d ?b) (contains ?d ?c) (unshaken ?d))
    :effect (and (shaken ?d) (contains ?d ?a) (not (unshaken ?d)) (not (contains ?d ?b)) (not (contains ?d ?c)))
  )

  (:action pour-beverage
    :parameters (?a - beverage ?b - shot ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?c) (unshaken ?c) (empty ?b) (clean ?b) (contains ?c ?a) (shaker-level ?c ?e) (next ?e ?f))
    :effect (and (contains ?b ?a) (shaker-level ?c ?f))
  )

)