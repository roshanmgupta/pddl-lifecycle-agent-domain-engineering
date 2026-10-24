(define (domain barman)
 (:requirements :strips :typing)
 (:types 
     shaker shot ingredient cocktail dispenser hand level - object
 )
 (:predicates 
     (ontable ?c - container)
     (holding ?h - hand ?c - container)
     (clean ?c - container)
     (empty ?c - container)
     (contains ?c - container ?b - beverage)
     (dispenses ?d - dispenser ?i - ingredient)
     (shaker-empty-level ?s - shaker ?l - level)
     (shaker-level ?s - shaker ?l - level)
     (handempty ?h - hand)
     (next ?l1 - level ?l2 - level)
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
     :effect (and (ontable ?c) (not (holding ?h ?c)) (handempty ?h))
 )

 (:action fill
     :parameters (?hC - hand ?s - shot ?d - dispenser ?i - ingredient)
     :precondition (and (holding ?hC ?s) (handempty ?hD) (dispenses ?d ?i) (empty ?s) (clean ?s))
     :effect (and (contains ?s ?i) (not (empty ?s)) (not (clean ?s)))
 )

 (:action refill
     :parameters (?hC - hand ?s - shot ?d - dispenser ?i - ingredient)
     :precondition (and (holding ?hC ?s) (handempty ?hD) (dispenses ?d ?i) (not (empty ?s)) (not (clean ?s)))
     :effect (and (contains ?s ?i) (not (empty ?s)))
 )

 (:action empty-shot
     :parameters (?h - hand ?s - shot ?b - beverage)
     :precondition (and (holding ?h ?s) (contains ?s ?b))
     :effect (and (empty ?s) (not (contains ?s ?b)))
 )

 (:action clean-shot
     :parameters (?hC - hand ?s - shot ?b - beverage)
     :precondition (and (holding ?hC ?s) (handempty ?hD) (not (empty ?s)) (not (clean ?s)))
     :effect (and (clean ?s) (not (not (clean ?s))) (not (contains ?s ?b)))
 )

 (:action pour-to-clean-shaker
     :parameters (?hD - hand ?s - shot ?c - shaker ?i - ingredient ?lE - level ?lF - level)
     :precondition (and (holding ?hD ?s) (contains ?s ?i) (empty ?c) (clean ?c) (shaker-level ?c ?lE) (next ?lE ?lF))
     :effect (and (empty ?s) (contains ?c ?i) (not (empty ?c)) (not (clean ?c)) (shaker-level ?c ?lF))
 )

 (:action pour-to-used-shaker
     :parameters (?hD - hand ?s - shot ?c - shaker ?i - ingredient ?lE - level ?lF - level)
     :precondition (and (holding ?hD ?s) (contains ?s ?i) (not (empty ?c)) (shaker-level ?c ?lE) (next ?lE ?lF))
     :effect (and (empty ?s) (contains ?c ?i) (shaker-level ?c ?lF))
 )

 (:action empty-shaker
     :parameters (?h - hand ?c - shaker ?b - cocktail ?lD - level ?lE - level)
     :precondition (and (holding ?h ?c) (contains ?c ?b) (shaken ?c) (shaker-level ?c ?lD) (shaker-empty-level ?c ?lE))
     :effect (and (shaker-level ?c ?lE) (empty ?c) (not (contains ?c ?b)))
 )

 (:action clean-shaker
     :parameters (?hA - hand ?c - shaker)
     :precondition (and (holding ?hA ?c) (handempty ?hB) (empty ?c))
     :effect (clean ?c)
 )

 (:action shake
     :parameters (?hE - hand ?c - shaker ?b - ingredient ?c2 - ingredient)
     :precondition (and (holding ?hE ?c) (handempty ?hF) (not (shaken ?c)) (contains ?c ?b) (contains ?c ?c2))
     :effect (and (shaken ?c) (not (not (shaken ?c))) (not (contains ?c ?b)) (not (contains ?c ?c2)))
 )

 (:action pour-beverage
     :parameters (?hC - hand ?c - shaker ?s - shot ?b - beverage ?lE - level ?lF - level)
     :precondition (and (holding ?hC ?c) (shaken ?c) (empty ?s) (clean ?s) (contains ?c ?b) (shaker-level ?c ?lE) (next ?lE ?lF))
     :effect (and (contains ?s ?b) (shaker-level ?c ?lF) (not (empty ?s)) (not (clean ?s)))
 )
)