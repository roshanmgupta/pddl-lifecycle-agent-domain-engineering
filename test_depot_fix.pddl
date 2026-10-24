(define (domain depots)
  (:requirements :strips :typing)

  (:types
    location physical_entity - object
    depot distributor - location
    hoist surface truck - physical_entity
    crate pallet - surface
  )

  (:predicates
    (at ?x - physical_entity ?y - location)
    (available ?h - hoist)
    (lifting ?h - hoist ?c - crate)
    (on ?c - crate ?s - surface)
    (clear ?c - physical_entity)
    (in ?c - crate ?t - truck)
  )

  (:action drive_truck
    :parameters (?t - truck ?from - location ?to - location)
    :precondition (at ?t ?from)
    :effect (and (at ?t ?to) (not (at ?t ?from)))
  )

  (:action lift_crate
    :parameters (?h - hoist ?c - crate ?s - surface ?loc - location)
    :precondition (and (at ?h ?loc) (available ?h) (at ?c ?loc) (on ?c ?s) (clear ?c))
    :effect (and (lifting ?h ?c) (not (at ?c ?loc)) (not (available ?h)) (not (on ?c ?s)) (clear ?s)))
  )

  (:action drop_crate
    :parameters (?h - hoist ?c - crate ?s - surface ?loc - location)
    :precondition (and (at ?h ?loc) (at ?s ?loc) (lifting ?h ?c))
    :effect (and (available ?h) (at ?c ?loc) (clear ?c) (on ?c ?s) (not (lifting ?h ?c)) (clear ?s)))
  )

  (:action load_crate
    :parameters (?h - hoist ?c - crate ?t - truck ?loc - location)
    :precondition (and (at ?h ?loc) (at ?t ?loc) (lifting ?h ?c))
    :effect (and (in ?c ?t) (available ?h) (not (lifting ?h ?c)) (clear ?t))
  )

  (:action unload_crate
    :parameters (?h - hoist ?c - crate ?t - truck ?loc - location)
    :precondition (and (at ?h ?loc) (at ?t ?loc) (available ?h) (in ?c ?t))
    :effect (and (lifting ?h ?c) (not (in ?c ?t)) (not (available ?h)))
  )

)