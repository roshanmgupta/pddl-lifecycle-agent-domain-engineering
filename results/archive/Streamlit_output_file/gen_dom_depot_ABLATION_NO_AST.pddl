(define (domain depots)
  (:requirements :strips :typing)
  (:types
    place locatable - object
    depot distributor - place
    truck hoist surface - locatable
    pallet crate - surface
  )
  (:predicates
    (at ?locatable - locatable ?place - place)
    (available ?hoist - hoist)
    (on ?crate - crate ?surface - surface)
    (clear ?surface - surface)
    (lifting ?hoist - hoist ?crate - crate)
    (in ?crate - crate ?truck - truck)
  )
  (:action drive
    :parameters (?truck - truck ?from - place ?to - place)
    :precondition (and (at ?truck ?from))
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )
  (:action lift
    :parameters (?hoist - hoist ?crate - crate ?surface - surface ?place - place)
    :precondition (and (at ?hoist ?place) (available ?hoist) (at ?crate ?place) (on ?crate ?surface) (clear ?crate))
    :effect (and (lifting ?hoist ?crate) (clear ?surface) (not (at ?crate ?place)) (not (clear ?crate)) (not (available ?hoist)) (not (on ?crate ?surface)))
  )
  (:action drop
    :parameters (?hoist - hoist ?crate - crate ?surface - surface ?place - place)
    :precondition (and (at ?hoist ?place) (at ?surface ?place) (clear ?surface) (lifting ?hoist ?crate))
    :effect (and (available ?hoist) (at ?crate ?place) (clear ?crate) (on ?crate ?surface) (not (lifting ?hoist ?crate)) (not (clear ?surface)))
  )
  (:action load
    :parameters (?hoist - hoist ?crate - crate ?truck - truck ?place - place)
    :precondition (and (at ?hoist ?place) (at ?truck ?place) (lifting ?hoist ?crate))
    :effect (and (in ?crate ?truck) (available ?hoist) (not (lifting ?hoist ?crate)))
  )
  (:action unload
    :parameters (?hoist - hoist ?crate - crate ?truck - truck ?place - place)
    :precondition (and (at ?hoist ?place) (at ?truck ?place) (available ?hoist) (in ?crate ?truck))
    :effect (and (lifting ?hoist ?crate) (not (in ?crate ?truck)) (not (available ?hoist)))
  )
)