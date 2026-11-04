; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_missing_goal_add_effect
; DOMAIN: blocksworld
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: stack
; INJECTED FLAW: Removed vital add effect '(on ?ob ?underob)' from action 'stack'
; RATIONALE: Prevents action 'stack' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '(on ?ob ?underob)' in action 'stack' effects.
; ==============================================================================

(define (domain blocksworld-4ops)
  (:requirements :strips)
(:predicates (clear ?x)
             (ontable ?x)
             (handempty)
             (holding ?x)
             (on ?x ?y))

(:action pick-up
  :parameters (?ob)
  :precondition (and (clear ?ob) (ontable ?ob) (handempty))
  :effect (and (holding ?ob) (not (clear ?ob)) (not (ontable ?ob))
               (not (handempty))))

(:action put-down
  :parameters  (?ob)
  :precondition (holding ?ob)
  :effect (and (clear ?ob) (handempty) (ontable ?ob)
               (not (holding ?ob))))

(:action stack
  :parameters  (?ob ?underob)
  :precondition (and (clear ?underob) (holding ?ob))
  :effect (and (handempty) (clear ?ob) 
               (not (clear ?underob)) (not (holding ?ob))))

(:action unstack
  :parameters  (?ob ?underob)
  :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
  :effect (and (holding ?ob) (clear ?underob)
               (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))))
