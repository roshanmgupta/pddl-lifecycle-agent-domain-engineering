; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_01_unsatisfiable_precondition_1
; DOMAIN: gripper
; MUTATION OPERATOR: OPERATOR_1_UNSATISFIABLE_PRECONDITION
; TARGET ACTION SCHEMA: pick
; INJECTED FLAW: Added unsatisfiable precondition '(unreachable_precondition)' to action 'pick'
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: Remove '(unreachable_precondition)' from action 'pick' preconditions.
; ==============================================================================

(define (domain gripper-strips)
 (:requirements :strips :typing) 
 (:types room object robot gripper)
 (:predicates (unreachable_precondition)
  (at-robby ?r - robot ?x - room)
 	      (at ?o - object ?x - room)
	      (free ?r - robot ?g - gripper)
	      (carry ?r - robot ?o - object ?g - gripper))

   (:action move
       :parameters  (?r - robot ?from ?to - room)
       :precondition (and  (at-robby ?r ?from))
       :effect (and  (at-robby ?r ?to)
		     (not (at-robby ?r ?from))))

   (:action pick
       :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
       :precondition  (and  (unreachable_precondition) (at ?obj ?room) (at-robby ?r ?room) (free ?r ?g))
       :effect (and (carry ?r ?obj ?g)
		    (not (at ?obj ?room)) 
		    (not (free ?r ?g))))

   (:action drop
       :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
       :precondition  (and  (carry ?r ?obj ?g) (at-robby ?r ?room))
       :effect (and (at ?obj ?room)
		    (free ?r ?g)
		    (not (carry ?r ?obj ?g)))))
