; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_missing_goal_add_effect
; DOMAIN: driverlog02-bfs
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: unload-truck
; INJECTED FLAW: Removed vital add effect '(at ?obj ?loc)' from action 'unload-truck'
; RATIONALE: Prevents action 'unload-truck' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '(at ?obj ?loc)' in action 'unload-truck' effects.
; ==============================================================================

(define (domain driverlog)
  (:requirements :strips) 
  (:predicates 	(OBJ ?obj)
	       	(TRUCK ?truck)
               	(LOCATION ?loc)
		(driver ?d)
		(at ?obj ?loc)
		(in ?obj1 ?obj)
		(driving ?d ?v)
		(link ?x ?y) (path ?x ?y)
		(empty ?v)
)


(:action LOAD-TRUCK
  :parameters
   (?obj
    ?truck
    ?loc)
  :precondition
   (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc)
   (at ?truck ?loc) (at ?obj ?loc))
  :effect
   (and (not (at ?obj ?loc)) (in ?obj ?truck)))

(:action UNLOAD-TRUCK
  :parameters
   (?obj
    ?truck
    ?loc)
  :precondition
   (and (OBJ ?obj) (TRUCK ?truck) (LOCATION ?loc)
        (at ?truck ?loc) (in ?obj ?truck))
  :effect
   (and (not (in ?obj ?truck)) ))

(:action BOARD-TRUCK
  :parameters
   (?driver
    ?truck
    ?loc)
  :precondition
   (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc)
   (at ?truck ?loc) (at ?driver ?loc) (empty ?truck))
  :effect
   (and (not (at ?driver ?loc)) (driving ?driver ?truck) (not (empty ?truck))))

(:action DISEMBARK-TRUCK
  :parameters
   (?driver
    ?truck
    ?loc)
  :precondition
   (and (DRIVER ?driver) (TRUCK ?truck) (LOCATION ?loc)
        (at ?truck ?loc) (driving ?driver ?truck))
  :effect
   (and (not (driving ?driver ?truck)) (at ?driver ?loc) (empty ?truck)))

(:action DRIVE-TRUCK
  :parameters
   (?truck
    ?loc-from
    ?loc-to
    ?driver)
  :precondition
   (and (TRUCK ?truck) (LOCATION ?loc-from) (LOCATION ?loc-to) (DRIVER ?driver) 
   (at ?truck ?loc-from)
   (driving ?driver ?truck) (link ?loc-from ?loc-to))
  :effect
   (and (not (at ?truck ?loc-from)) (at ?truck ?loc-to)))

(:action WALK
  :parameters
   (?driver
    ?loc-from
    ?loc-to)
  :precondition
   (and (DRIVER ?driver) (LOCATION ?loc-from) (LOCATION ?loc-to)
	(at ?driver ?loc-from) (path ?loc-from ?loc-to))
  :effect
   (and (not (at ?driver ?loc-from)) (at ?driver ?loc-to)))

 
)
