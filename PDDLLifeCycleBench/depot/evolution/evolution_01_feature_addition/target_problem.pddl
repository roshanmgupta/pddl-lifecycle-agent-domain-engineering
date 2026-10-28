(define (problem depot-crossdock-disc) (:domain depots)
(:objects
	depot0 - Depot
	truck0 truck1 - Truck
	pallet0 - Pallet
	crate0 - Crate
	hoist0 - Hoist)
(:init
	(at pallet0 depot0)
	(clear pallet0)
	(at truck0 depot0)
	(at truck1 depot0)
	(at hoist0 depot0)
	(available hoist0)
	(in crate0 truck0)
)
(:goal (and
	(in crate0 truck1)
))
)
