(define (domain cocktail_making)
  (:requirements :strips :typing)
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
    (holding ?h - hand ?c - container)
    (on_table ?c - container)
    (hand_empty ?h - hand)
    (dispenses ?d - dispenser ?i - ingredient)
    (contains ?c - container ?b - beverage)
    (empty ?c - container)
    (clean ?c - container)
    (used_by ?c - container ?b - beverage)
    (unshaken ?s - shaker)
    (shaken ?s - shaker)
    (at_level ?s - shaker ?l - level)
    (next ?l1 - level ?l2 - level)
    (part_of ?i - ingredient ?c - cocktail)
  )

  (:action grasp
    :parameters (?b - container ?a - hand)
    :precondition (and (on_table ?b) (hand_empty ?a))
    :effect (and (holding ?a ?b) (not (on_table ?b)) (not (hand_empty ?a)))
  )

  (:action leave
    :parameters (?b - container ?a - hand)
    :precondition (holding ?a ?b)
    :effect (and (hand_empty ?a) (on_table ?b) (not (holding ?a ?b)))
  )

  (:action fill
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (hand_empty ?d) (dispenses ?e ?b) (empty ?a) (clean ?a))
    :effect (and (contains ?a ?b) (used_by ?a ?b) (not (empty ?a)) (not (clean ?a)))
  )

  (:action refill
    :parameters (?a - shot ?b - ingredient ?e - dispenser ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (hand_empty ?d) (dispenses ?e ?b) (empty ?a) (used_by ?a ?b))
    :effect (and (contains ?a ?b) (not (empty ?a)))
  )

  (:action empty_shot
    :parameters (?b - shot ?c - beverage ?a - hand)
    :precondition (and (holding ?a ?b) (contains ?b ?c))
    :effect (and (empty ?b) (not (contains ?b ?c)))
  )

  (:action clean_shot
    :parameters (?a - shot ?b - beverage ?c - hand ?d - hand)
    :precondition (and (holding ?c ?a) (hand_empty ?d) (empty ?a) (used_by ?a ?b))
    :effect (and (clean ?a) (not (used_by ?a ?b)))
  )

  (:action pour_into_clean_shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (contains ?a ?b) (empty ?c) (clean ?c) (at_level ?c ?e) (next ?e ?f))
    :effect (and (empty ?a) (contains ?c ?b) (unshaken ?c) (at_level ?c ?f) 
                 (not (contains ?a ?b)) (not (empty ?c)) (not (clean ?c)) (not (at_level ?c ?e)))
  )

  (:action pour_into_used_shaker
    :parameters (?a - shot ?b - ingredient ?c - shaker ?d - hand ?e - level ?f - level)
    :precondition (and (holding ?d ?a) (contains ?a ?b) (unshaken ?c) (at_level ?c ?e) (next ?e ?f))
    :effect (and (contains ?c ?b) (empty ?a) (at_level ?c ?f) 
                 (not (contains ?a ?b)) (not (at_level ?c ?e)))
  )

  (:action empty_shaker
    :parameters (?b - shaker ?c - cocktail ?a - hand ?d - level ?e - level)
    :precondition (and (holding ?a ?b) (contains ?b ?c) (shaken ?b) (at_level ?b ?d) (next ?d ?e))
    :effect (and (at_level ?b ?e) (empty ?b) 
                 (not (shaken ?b)) (not (at_level ?b ?d)) (not (contains ?b ?c)))
  )

  (:action clean_shaker
    :parameters (?c - shaker ?a - hand ?b - hand)
    :precondition (and (holding ?a ?c) (hand_empty ?b) (empty ?c))
    :effect (and (clean ?c))
  )

  (:action shake
    :parameters (?a - cocktail ?d - shaker ?e - hand ?f - hand ?b - ingredient ?c - ingredient)
    :precondition (and (holding ?e ?d) (hand_empty ?f) (contains ?d ?b) (contains ?d ?c) 
                       (part_of ?b ?a) (part_of ?c ?a) (unshaken ?d))
    :effect (and (shaken ?d) (contains ?d ?a) 
                 (not (unshaken ?d)) (not (contains ?d ?b)) (not (contains ?d ?c)))
  )

  (:action pour_from_shaker
    :parameters (?a - beverage ?d - shaker ?c - hand ?b - shot ?e - level ?f - level)
    :precondition (and (holding ?c ?d) (shaken ?d) (empty ?b) (clean ?b) (contains ?d ?a) (at_level ?d ?e) (next ?e ?f))
    :effect (and (contains ?b ?a) (at_level ?d ?f) 
                 (not (clean ?b)) (not (empty ?b)) (not (at_level ?d ?e)))
  )
)