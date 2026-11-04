; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_03_missing_goal_add_effect_1
; DOMAIN: gripper
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: pick
; INJECTED FLAW: Removed required add effect '(carry ?r ?obj ?g)' from action 'pick'
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: Restore add effect '(carry ?r ?obj ?g)' in action 'pick' effects.
; ==============================================================================

(define (domain gripper-strips)
 (:requirements :strips :typing) 
 (:types room object robot gripper)
 (:predicates (at-robby ?r - robot ?x - room)
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
       :precondition  (and  (at ?obj ?room) (at-robby ?r ?room) (free ?r ?g))
       :effect (and (not (at ?obj ?room)) 
		    (not (free ?r ?g))))

   (:action drop
       :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
       :precondition  (and  (carry ?r ?obj ?g) (at-robby ?r ?room))
       :effect (and (at ?obj ?room)
		    (free ?r ?g)
		    (not (carry ?r ?obj ?g)))))
