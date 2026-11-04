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
    :effect (and (holding ?h ?c) (not (ontable ?c)) (not (handempty ?h)))
  )

  (:action leave
    :parameters (?h - hand ?c - container)
    :precondition (holding ?h ?c)
    :effect (and (handempty ?h) (ontable ?c) (not (holding ?h ?c)))
  )

  (:action fill-shot
    :parameters (?s - shot ?i - ingredient ?h1 - hand ?h2 - hand ?d - dispenser)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) (empty ?s) (clean ?s))
    :effect (and (contains ?s ?i) (used ?s ?i) (not (empty ?s)) (not (clean ?s)))
  )

  (:action refill-shot
    :parameters (?s - shot ?i - ingredient ?h1 - hand ?h2 - hand ?d - dispenser)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (dispenses ?d ?i) (empty ?s) (used ?s ?i))
    :effect (and (contains ?s ?i) (not (empty ?s)))
  )

  (:action empty-shot
    :parameters (?h - hand ?p - shot ?b - beverage)
    :precondition (and (holding ?h ?p) (contains ?p ?b))
    :effect (and (empty ?p) (not (contains ?p ?b)))
  )

  (:action clean-shot
    :parameters (?s - shot ?b - beverage ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (empty ?s) (used ?s ?b))
    :effect (and (clean ?s) (not (used ?s ?b)))
  )

  (:action pour-shot-to-clean-shaker
    :parameters (?s - shot ?i - ingredient ?d - shaker ?h1 - hand ?l - level ?l1 - level)
    :precondition (and (holding ?h1 ?s) (contains ?s ?i) (empty ?d) (clean ?d) (shaker-level ?d ?l) (next ?l ?l1))
    :effect (and (empty ?s) (contains ?d ?i) (unshaked ?d) (shaker-level ?d ?l1) (not (contains ?s ?i)) (not (empty ?d)) (not (clean ?d)) (not (shaker-level ?d ?l)))
  )

  (:action pour-shot-to-used-shaker
    :parameters (?s - shot ?i - ingredient ?d - shaker ?h1 - hand ?l - level ?l1 - level)
    :precondition (and (holding ?h1 ?s) (contains ?s ?i) (unshaked ?d) (shaker-level ?d ?l) (next ?l ?l1))
    :effect (and (contains ?d ?i) (empty ?s) (shaker-level ?d ?l1) (not (contains ?s ?i)) (not (shaker-level ?d ?l)))
  )

  (:action empty-shaker
    :parameters (?h - hand ?s - shaker ?b - cocktail ?l - level ?l1 - level)
    :precondition (and (holding ?h ?s) (contains ?s ?b) (shaked ?s) (shaker-level ?s ?l) (shaker-empty-level ?s ?l1))
    :effect (and (shaker-level ?s ?l1) (empty ?s) (not (shaked ?s)) (not (shaker-level ?s ?l)) (not (contains ?s ?b)))
  )

  (:action clean-shaker
    :parameters (?h1 - hand ?h2 - hand ?s - shaker)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (empty ?s))
    :effect (clean ?s)
  )

  (:action shake
    :parameters (?b - cocktail ?d1 - ingredient ?d2 - ingredient ?s - shaker ?h1 - hand ?h2 - hand)
    :precondition (and (holding ?h1 ?s) (handempty ?h2) (contains ?s ?d1) (contains ?s ?d2) (cocktail-part1 ?b ?d1) (cocktail-part2 ?b ?d2))
    :effect (and (shaked ?s) (contains ?s ?b) (not (contains ?s ?d1)) (not (contains ?s ?d2)))
  )

  (:action pour-shaker-to-shot
    :parameters (?b - beverage ?d - shot ?h - hand ?s - shaker ?l - level ?l1 - level)
    :precondition (and (holding ?h ?s) (shaked ?s) (empty ?d) (clean ?d) (contains ?s ?b) (shaker-level ?s ?l) (next ?l ?l1))
    :effect (and (contains ?d ?b) (shaker-level ?s ?l1) (not (clean ?d)) (not (empty ?d)) (not (shaker-level ?s ?l)) (not (contains ?s ?b)))
  )

)