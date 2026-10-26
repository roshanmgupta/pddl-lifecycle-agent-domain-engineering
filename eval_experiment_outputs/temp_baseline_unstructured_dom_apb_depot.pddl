(define (domain depots)
  (:requirements :strips :typing)
  (:types
    place locatable - object
    depot distributor - place
    truck hoist surface - locatable
    pallet crate - surface
  )
  
  (:predicates
    (at ?x ?y - locatable ?p - place)
    (on ?x ?y - surface)
    (clear ?x - surface)
    (available ?h - hoist)
    (lifting ?h - hoist ?c - crate)
    (in ?c - crate ?t - truck)
  )
  
  (:action drive
    :parameters (?t - truck ?from - place ?to - place)
    :precondition (and (at ?t ?from) (not (= ?from ?to)))
    :effect (and (not (at ?t ?from)) (at ?t ?to))
  )
  
  (:action lift
    :parameters (?h - hoist ?c - crate ?s - surface ?p - place)
    :precondition (and (at ?h ?p) (available ?h) (at ?c ?p) (on ?c ?s) (clear ?c))
    :effect (and (not (at ?c ?p)) (not (clear ?c)) (not (available ?h)) (not (on ?c ?s)) 
                 (lifting ?h ?c) (clear ?s))
  )
  
  (:action drop
    :parameters (?h - hoist ?c - crate ?s - surface ?p - place)
    :precondition (and (at ?h ?p) (at ?s ?p) (clear ?s) (lifting ?h ?c))
    :effect (and (available ?h) (at ?c ?p) (clear ?c) (on ?c ?s) 
                 (not (lifting ?h ?c)) (not (clear ?s)))
  )
  
  (:action load
    :parameters (?h - hoist ?c - crate ?t - truck ?p - place)
    :precondition (and (at ?h ?p) (at ?t ?p) (lifting ?h ?c))
    :effect (and (in ?c ?t) (available ?h) (not (lifting ?h ?c)))
  )
  
  (:action unload
    :parameters (?h - hoist ?c - crate ?t - truck ?p - place)
    :precondition (and (at ?h ?p) (at ?t ?p) (available ?h) (in ?c ?t))
    :effect (and (lifting ?h ?c) (not (in ?c ?t)) (not (available ?h)))
  )
)