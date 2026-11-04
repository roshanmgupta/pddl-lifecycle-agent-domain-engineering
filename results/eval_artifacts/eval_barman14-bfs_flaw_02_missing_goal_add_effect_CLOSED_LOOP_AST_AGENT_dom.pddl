(define (domain barman)
  (:requirements :strips :typing)

  (:types
    beverage container dispenser hand level - object
    cocktail ingredient - beverage
    shaker shot - container
  )

  (:predicates
    (ontable ?c - object)
    (holding ?h - object ?c - object)
    (handempty ?h - object)
    (empty ?c - object)
    (contains ?c - object ?b - object)
    (clean ?c - object)
    (used ?c - object ?b - object)
    (dispenses ?d - object ?i - object)
    (shaker-empty-level ?s - object ?l - object)
    (shaker-level ?s - object ?l - object)
    (next ?l1 - object ?l2 - object)
    (unshaked ?s - object)
    (shaked ?s - object)
    (cocktail-part1 ?c - object ?i - object)
    (cocktail-part2 ?c - object ?i - object)
  )

  (:action grasp
    :parameters (?h - hand ?c - container)
    :precondition (and (ontable ?c) (handempty ?h))
    :effect (and (not (ontable ?c)) (not (handempty ?h)) (holding ?h ?c))
  )

  (:action leave
    :parameters (?h - hand ?c - container)
    :precondition (holding ?h ?c)
    :effect (and (not (holding ?h ?c)) (handempty ?h) (ontable ?c))
  )

  (:action fill-shot
    :parameters (?s - shot ?i - ingredient ?h1 - hand ?h2 - hand ?d - dispenser)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) (empty ?s) (clean ?s))
    :effect (and (not (empty ?s)) (not (clean ?s)) (used ?s ?i))
  )

  (:action refill-shot
    :parameters (?s - shot ?i - ingredient ?h1 - hand ?h2 - hand ?d - dispenser)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) (empty ?s) (used ?s ?i))
    :effect (and (not (empty ?s)) (contains ?s ?i))
  )

  (:action empty-shot
    :parameters (?h - hand ?p - shot ?b - beverage)
    :precondition (and (holding ?h ?p) (contains ?p ?b))
    :effect (and (not (contains ?p ?b)) (empty ?p))
  )

  (:action clean-shot
    :parameters (?s - shot ?b - beverage ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (empty ?s) (used ?s ?b))
    :effect (and (not (used ?s ?b)) (clean ?s))
  )

  (:action pour-shot-to-clean-shaker
    :parameters (?s - shot ?i - ingredient ?d - shaker ?h1 - hand ?l - level ?l1 - level)
    :precondition (and (holding ?h1 ?s) (contains ?s ?i) (empty ?d) (clean ?d) (shaker-level ?d ?l) (next ?l ?l1))
    :effect (and (not (contains ?s ?i)) (empty ?s) (contains ?d ?i) (not (empty ?d)) (not (clean ?d)) (unshaked ?d) (not (shaker-level ?d ?l)) (shaker-level ?d ?l1))
  )

  (:action pour-shot-to-used-shaker
    :parameters (?s - shot ?i - ingredient ?d - shaker ?h1 - hand ?l - level ?l1 - level)
    :precondition (and (holding ?h1 ?s) (contains ?s ?i) (shaker-level ?d ?l) (next ?l ?l1))
    :effect (and (not (contains ?s ?i)) (contains ?d ?i) (empty ?s) (not (shaker-level ?d ?l)) (shaker-level ?d ?l1))
  )

  (:action empty-shaker
    :parameters (?h - hand ?s - shaker ?b - cocktail ?l - level ?l1 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?b) (shaked ?s) (shaker-level ?s ?l) (shaker-empty-level ?s ?l1))
    :effect (and (not (shaked ?s)) (not (shaker-level ?s ?l)) (shaker-level ?s ?l1) (not (contains ?s ?b)) (empty ?s))
  )

  (:action clean-shaker
    :parameters (?h1 - hand ?h2 - hand ?s - shaker)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (empty ?s))
    :effect (clean ?s)
  )

  (:action shake
    :parameters (?b - cocktail ?d1 - ingredient ?d2 - ingredient ?s - shaker ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (contains ?s ?d1) (contains ?s ?d2) (cocktail-part1 ?b ?d1) (cocktail-part2 ?b ?d2) (unshaked ?s))
    :effect (and (not (unshaked ?s)) (not (contains ?s ?d1)) (not (contains ?s ?d2)) (shaked ?s) (contains ?s ?b))
  )

  (:action pour-shaker-to-shot
    :parameters (?b - beverage ?d - shot ?h - hand ?s - shaker ?l - level ?l1 - level)
    :precondition (and (holding ?h ?s) (shaked ?s) (empty ?d) (clean ?d) (contains ?s ?b) (shaker-level ?s ?l) (next ?l1 ?l))
    :effect (and (not (clean ?d)) (not (empty ?d)) (contains ?d ?b) (shaker-level ?s ?l1) (not (shaker-level ?s ?l)) (empty ?s))
  )

)