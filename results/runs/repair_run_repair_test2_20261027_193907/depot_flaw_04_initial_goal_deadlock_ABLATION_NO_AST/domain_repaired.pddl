(define (domain depots)
(:requirements :strips :typing)
(:types place locatable - object
	depot distributor - place
        truck hoist surface - locatable
        pallet crate - surface)

(:predicates
    (state_deadlock_mutex_lock) 
    (at ?x - locatable ?y - place)
    (on ?y - crate ?z - surface)
    (in ?y - crate ?z - truck)
    (lifting ?x - hoist ?y - crate)
    (available ?x - hoist)
    (clear ?x - object) ; Changed type from surface to object
)