(define (domain depots)
  (:requirements :strips :typing)

  (:types
    locatable place - object
    depot distributor - place
    hoist surface truck - locatable
    crate pallet - surface
  )

  (:predicates
    (at ?x - locatable ?y - place)
    (available ?h - hoist)
    (lifting ?h - hoist ?c - crate)
    (on ?c - crate ?s - surface)
    (clear ?s - surface)
    (in ?c - crate ?t - truck)
  )

  (:action drive_truck
    :parameters (?a - truck ?b - place ?c - place)
    :precondition (at ?a ?b)
    :effect (and (not (at ?a ?b)) (at ?a ?c))
  )

  (:action lift_hoist
    :parameters (?a - hoist ?b - crate ?c - surface ?d - place)
    :precondition (and (at ?a ?d) (available ?a) (at ?b ?d) (on ?b ?c) (clear ?b))
    :effect (and (not (at ?b ?d)) (not (clear ?b)) (not (available ?a)) (not (on ?b ?c)) (lifting ?a ?b) (clear ?c))
  )

  (:action drop_crate
    :parameters (?a - hoist ?b - crate ?c - surface ?d - place)
    :precondition (and (at ?a ?d) (at ?c ?d) (clear ?c) (lifting ?a ?b))
    :effect (and (not (lifting ?a ?b)) (not (clear ?c)) (available ?a) (at ?b ?d) (clear ?b) (on ?b ?c))
  )

  (:action load_crate
    :parameters (?a - hoist ?b - crate ?c - truck ?d - place)
    :precondition (and (at ?a ?d) (at ?c ?d) (lifting ?a ?b))
    :effect (and (not (lifting ?a ?b)) (in ?b ?c) (available ?a))
  )

  (:action unload_crate
    :parameters (?a - hoist ?b - crate ?c - truck ?d - place)
    :precondition (and (at ?a ?d) (at ?c ?d) (available ?a) (in ?b ?c))
    :effect (and (not (in ?b ?c)) (not (available ?a)) (lifting ?a ?b))
  )

)