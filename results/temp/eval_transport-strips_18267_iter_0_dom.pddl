; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_missing_goal_add_effect
; DOMAIN: nomystery11-bfs
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: UNLOAD
; INJECTED FLAW: Removed vital add effect '(at ?p ?l)' from action 'UNLOAD'
; RATIONALE: Prevents action 'UNLOAD' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '(at ?p ?l)' in action 'UNLOAD' effects.
; ==============================================================================

(define (domain transport-strips)
(:requirements :typing)

(:types location fuellevel locatable - object 
	package truck - locatable
)

(:predicates 
(connected ?l1 ?l2 - location)
(at ?o - locatable ?l - location)
(in ?p - package ?t - truck)
(fuel ?t - truck ?level - fuellevel)
(fuelcost ?level - fuellevel ?l1 ?l2 - location)
(sum ?a ?b ?c - fuellevel)
)


(:action LOAD
:parameters
(?p - package
?t - truck
?l - location)
:precondition
(and (at ?t ?l) (at ?p ?l))
:effect
(and (not (at ?p ?l)) (in ?p ?t))
)

(:action UNLOAD
:parameters
(?p - package
?t - truck
?l - location)
:precondition
(and (at ?t ?l) (in ?p ?t))
:effect
(and  (not (in ?p ?t)))
)

(:action DRIVE
:parameters
(?t - truck
?l1 - location
?l2 - location
?fuelpost - fuellevel
?fueldelta - fuellevel
?fuelpre - fuellevel)
:precondition
(and 
(connected ?l1 ?l2)
(fuelcost ?fueldelta ?l1 ?l2)
(fuel ?t ?fuelpre)
(sum ?fuelpost ?fueldelta ?fuelpre)
(at ?t ?l1)
)
:effect
(and (not (at ?t ?l1)) 
     (at ?t ?l2) 
     (not (fuel ?t ?fuelpre)) 
     (fuel ?t ?fuelpost)
    )
)

)
