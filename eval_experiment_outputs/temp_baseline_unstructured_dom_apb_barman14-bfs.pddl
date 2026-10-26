(define (domain barman)
  (:requirements :strips :typing)
  (:types
    object - supertype
    hand level beverage dispenser container - object
    ingredient cocktail - beverage
    shot shaker - container
  )
  
  (:predicates
    (ontable ?x - container)
    (holding ?h - hand ?c - container)
    (handempty ?h - hand)
    (clean ?c - container)
    (empty ?c - container)
    (contains ?c - container ?b - beverage)
    (used ?c - container ?b - beverage)
    (dispenses ?d - dispenser ?i - ingredient)
    (shaker-empty-level ?s - shaker ?l - level)
    (shaker-level ?s - shaker ?l - level)
    (next ?l1 - level ?l2 - level)
    (unshaken ?s - shaker)
    (shaken ?s - shaker)
    (cocktail-part1 ?c - cocktail ?i - ingredient)
    (cocktail-part2 ?c - cocktail ?i - ingredient)
  )
  
  (:action grasp
    :parameters (?h - hand ?c - container)
    :precondition (and (ontable ?c) (handempty ?h))
    :effect (and (holding ?h ?c) (not (ontable ?c)) (not (handempty ?h)))
  )
  
  (:action leave
    :parameters (?h - hand ?c - container)
    :precondition (holding ?h ?c)
    :effect (and (handempty ?h) (ontable ?c) (not (holding ?h ?c)))
  )
  
  (:action fill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) 
                      (empty ?s) (clean ?s))
    :effect (and (contains ?s ?i) (used ?s ?i) (not (empty ?s)) (not (clean ?s)))
  )
  
  (:action refill
    :parameters (?s - shot ?i - ingredient ?d - dispenser ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) 
                      (empty ?s) (used ?s ?i))
    :effect (and (contains ?s ?i) (not (empty ?s)))
  )
  
  (:action empty-shot
    :parameters (?h - hand ?s - shot ?b - beverage)
    :precondition (and (holding ?h ?s) (contains ?s ?b))
    :effect (and (empty ?s) (not (contains ?s ?b)))
  )
  
  (:action clean-shot
    :parameters (?s - shot ?b - beverage ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (empty ?s) (used ?s ?b))
    :effect (and (clean ?s) (not (used ?s ?b)))
  )
  
  (:action pour-clean-shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (empty ?sh) (clean ?sh)
                      (shaker-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (empty ?s) (contains ?sh ?i) (unshaken ?sh) (shaker-level ?sh ?l2)
                (not (contains ?s ?i)) (not (empty ?sh)) (not (clean ?sh)) 
                (not (shaker-level ?sh ?l1)))
  )
  
  (:action pour-used-shaker
    :parameters (?s - shot ?i - ingredient ?sh - shaker ?h - hand ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?i) (unshaken ?sh)
                      (shaker-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?sh ?i) (empty ?s) (shaker-level ?sh ?l2)
                (not (contains ?s ?i)) (not (shaker-level ?sh ?l1)))
  )
  
  (:action empty-shaker
    :parameters (?h - hand ?sh - shaker ?c - cocktail ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (contains ?sh ?c) (shaken ?sh)
                      (shaker-level ?sh ?l1) (shaker-empty-level ?sh ?l2))
    :effect (and (shaker-level ?sh ?l2) (empty ?sh)
                (not (shaken ?sh)) (not (shaker-level ?sh ?l1)) (not (contains ?sh ?c)))
  )
  
  (:action clean-shaker
    :parameters (?sh - shaker ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?sh) (handempty ?h2) (empty ?sh))
    :effect (clean ?sh)
  )
  
  (:action shake
    :parameters (?c - cocktail ?sh - shaker ?h1 - hand ?h2 - hand ?i1 - ingredient ?i2 - ingredient)
    :precondition (and (holding ?h1 ?sh) (handempty ?h2) (contains ?sh ?i1) (contains ?sh ?i2)
                      (cocktail-part1 ?c ?i1) (cocktail-part2 ?c ?i2) (unshaken ?sh))
    :effect (and (shaken ?sh) (contains ?sh ?c) 
                (not (unshaken ?sh)) (not (contains ?sh ?i1)) (not (contains ?sh ?i2)))
  )
  
  (:action pour-shaker-to-shot
    :parameters (?b - beverage ?sh - shaker ?h - hand ?s - shot ?l1 - level ?l2 - level)
    :precondition (and (holding ?h ?sh) (shaken ?sh) (empty ?s) (clean ?s)
                      (contains ?sh ?b) (shaker-level ?sh ?l1) (next ?l1 ?l2))
    :effect (and (contains ?s ?b) (shaker-level ?sh ?l2)
                (not (clean ?s)) (not (empty ?s)) (not (shaker-level ?sh ?l1)))
  )
)