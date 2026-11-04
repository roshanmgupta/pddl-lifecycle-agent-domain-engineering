; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_missing_goal_add_effect
; DOMAIN: visitall
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: move
; INJECTED FLAW: Removed vital add effect '(visited ?nextpos)' from action 'move'
; RATIONALE: Prevents action 'move' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '(visited ?nextpos)' in action 'move' effects.
; ==============================================================================

(define (domain grid-visit-all)
(:requirements :typing)
(:types        place - object)
(:predicates (connected ?x ?y - place)
	     (at-robot ?x - place)
	     (visited ?x - place)
)
	
(:action move
:parameters (?curpos ?nextpos - place)
:precondition (and (at-robot ?curpos) (connected ?curpos ?nextpos))
:effect (and (at-robot ?nextpos) (not (at-robot ?curpos)) )
)

)
