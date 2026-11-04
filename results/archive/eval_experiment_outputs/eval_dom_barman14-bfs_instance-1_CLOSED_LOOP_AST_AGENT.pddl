(define (domain barman)
  (:requirements :strips :typing)

  (:types
    beverage container dispenser hand level - object
    cocktail ingredient - beverage
    shaker shot - container
  )

  (:predicates
    (ontable ?b - container)
    (holding ?a - hand ?b - container)
    (handempty ?a - hand)
    (dispenses ?e - dispenser ?b - beverage)
    (contains ?c - container ?b - beverage)
    (empty ?c - container)
    (clean ?c - container)
    (used-by ?c - container ?b - beverage)
    (unshaken ?c - container)
    (shaken ?c - container)
    (shaker-level ?c - shaker ?l - level)
    (next ?l1 - level ?l2 - level)
    (shaker-empty-level ?x1 - shaker ?x2 - level)
    (cocktail-part1 ?x1 - cocktail ?x2 - ingredient)
    (cocktail-part2 ?x1 - cocktail ?x2 - ingredient)
  )

  (:action grasp
    :parameters (?a - hand ?b - container)
    :precondition (and (ontable ?b) (handempty ?a))
    :effect (and (holding ?a ?b) (not (ontable ?b)) (not (handempty ?a)))
  )

  (:action leave
    :parameters (?a - hand ?b - container)
    :precondition (holding ?a ?b)
    :effect (and (handempty ?a) (ontable ?b) (not (holding ?a ?b)))
  )

  (:action fill
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (handempty ?d) (dispenses ?e ?b) (empty ?a) (clean ?a))
    :effect (and (contains ?a ?b) (used-by ?a ?b) (not (empty ?a)) (not (clean ?a)))
  )

  (:action refill
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (handempty ?d) (dispenses ?e ?b) (empty ?a) (contains ?a ?b))
    :effect (and (contains ?a ?b) (not (empty ?a)))
  )

  (:action empty_shot
    :parameters (?a - hand ?b - shot ?c - beverage)
    :precondition (and (holding ?a ?b) (contains ?b ?c))
    :effect (and (empty ?b) (not (contains ?b ?c)))
  )

  (:action clean_shot
    :parameters (?a - shot ?b - beverage ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (handempty ?d) (empty ?a) (contains ?a ?b))
    :effect (and (clean ?a) (not (contains ?a ?b)))
  )

  (:action pour_into_clean_shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (contains ?a ?b) (empty ?c) (clean ?c) (shaker-level ?c ?e) (next ?e ?f))
    :effect (and (empty ?a) (contains ?c ?b) (unshaken ?c) (shaker-level ?c ?f) (not (contains ?a ?b)) (not (empty ?c)) (not (clean ?c)) (not (shaker-level ?c ?e)))
  )

  (:action pour_into_used_shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (contains ?a ?b) (shaken ?c) (shaker-level ?c ?e) (next ?e ?f))
    :effect (and (contains ?c ?b) (empty ?a) (shaker-level ?c ?f) (not (contains ?a ?b)) (not (shaker-level ?c ?e)))
  )

  (:action empty_shaker
    :parameters (?a - hand ?b - shaker ?c - cocktail ?d - level ?e - level)
    :precondition (and (holding ?a ?b) (contains ?b ?c) (shaken ?b) (shaker-level ?b ?d) (shaker-level ?b ?e))
    :effect (and (shaker-level ?b ?e) (empty ?b) (not (shaken ?b)) (not (shaker-level ?b ?d)) (not (contains ?b ?c)))
  )

  (:action clean_shaker
    :parameters (?a - hand ?b - hand ?c - shaker)
    :precondition (and (holding ?a ?c) (handempty ?b) (empty ?c))
    :effect (clean ?c)
  )

  (:action shake
    :parameters (?a - cocktail ?b - ingredient ?c - ingredient ?d - shaker ?e - hand ?f - hand)
    :precondition (and (holding ?e ?d) (handempty ?f) (contains ?d ?b) (contains ?d ?c) (unshaken ?d))
    :effect (and (shaken ?d) (contains ?d ?a) (not (unshaken ?d)) (not (contains ?d ?b)) (not (contains ?d ?c)))
  )

  (:action pour_from_shaker
    :parameters (?a - beverage ?b - shot ?c - hand ?d - shaker ?e - level ?f - level)
    :precondition (and (holding ?c ?d) (shaken ?d) (empty ?b) (clean ?b) (contains ?d ?a) (shaker-level ?d ?e) (next ?e ?f))
    :effect (and (contains ?b ?a) (shaker-level ?d ?f) (not (clean ?b)) (not (empty ?b)) (not (shaker-level ?d ?e)))
  )

)