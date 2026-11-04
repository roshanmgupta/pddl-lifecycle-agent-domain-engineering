(define (problem roverprob66-discriminative) (:domain Rover)
(:objects
	general - Lander
	rover0 - Rover
	rover0store - Store
	waypoint0 waypoint1 waypoint2 - Waypoint
)
(:init
	(visible waypoint0 waypoint2)
	(visible waypoint2 waypoint0)
	(visible waypoint1 waypoint0)
	(visible waypoint0 waypoint1)
	(visible waypoint2 waypoint1)
	(visible waypoint1 waypoint2)
	(at_rock_sample waypoint1)
	(at rover0 waypoint1)
	(available rover0)
	(store_of rover0store rover0)
	(empty rover0store)
	(equipped_for_rock_analysis rover0)
	(can_traverse rover0 waypoint1 waypoint0)
	(can_traverse rover0 waypoint0 waypoint1)
)
(:goal (and
	(communicated_rock_data waypoint1)
))
)
