; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_unsatisfiable_precondition_2
; DOMAIN: parking11
; MUTATION OPERATOR: OPERATOR_1_UNSATISFIABLE_PRECONDITION
; TARGET ACTION SCHEMA: move-car-to-car
; INJECTED FLAW: Added unsatisfiable precondition '(unreachable_precondition_predicate)' to action 'move-car-to-car'
; GROUND TRUTH FIX: Remove '(unreachable_precondition_predicate)' from action 'move-car-to-car' preconditions.
; ==============================================================================

(define (domain parking)
 (:requirements :strips :typing)
 (:types car curb)
 (:predicates
    (unreachable_precondition_predicate) 
    (at-curb ?car - car) 
    (at-curb-num ?car - car ?curb - curb)
    (behind-car ?car ?front-car - car)
    (car-clear ?car - car) 
    (curb-clear ?curb - curb)
 )


	(:action move-curb-to-curb
		:parameters (?car - car ?curbsrc ?curbdest - curb)
		:precondition (and 
			(car-clear ?car)
			(curb-clear ?curbdest)
			(at-curb-num ?car ?curbsrc)
		)
		:effect (and 
			(not (curb-clear ?curbdest))
			(curb-clear ?curbsrc)
			(at-curb-num ?car ?curbdest)
			(not (at-curb-num ?car ?curbsrc))

		)
	)

	(:action move-curb-to-car
		:parameters (?car - car ?curbsrc - curb ?cardest - car)
		:precondition (and 
			(car-clear ?car)
			(car-clear ?cardest)
			(at-curb-num ?car ?curbsrc)
			(at-curb ?cardest) 
		)
		:effect (and 
			(not (car-clear ?cardest))
			(curb-clear ?curbsrc)
			(behind-car ?car ?cardest)
			(not (at-curb-num ?car ?curbsrc))
			(not (at-curb ?car))

		)
	)

	(:action move-car-to-curb
		:parameters (?car - car ?carsrc - car ?curbdest - curb)
		:precondition (and 
			(car-clear ?car)
			(curb-clear ?curbdest)
			(behind-car ?car ?carsrc)
		)
		:effect (and 
			(not (curb-clear ?curbdest))
			(car-clear ?carsrc)
			(at-curb-num ?car ?curbdest)
			(not (behind-car ?car ?carsrc))
			(at-curb ?car)

		)
	)

	(:action move-car-to-car
		:parameters (?car - car ?carsrc - car ?cardest - car)
		:precondition (and (unreachable_precondition_predicate) 
			(car-clear ?car)
			(car-clear ?cardest)
			(behind-car ?car ?carsrc)
			(at-curb ?cardest) 
		)
		:effect (and 
			(not (car-clear ?cardest))
			(car-clear ?carsrc)
			(behind-car ?car ?cardest)
			(not (behind-car ?car ?carsrc))

		)
	)
)
