; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_03_missing_goal_add_effect_1
; DOMAIN: blocksworld
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: pick-up
; INJECTED FLAW: Removed required add effect '(holding ?ob)' from action 'pick-up' and should add "and" to handempty
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: Restore add effect '(holding ?ob)' in action 'pick-up' effects.
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
  :effect (and (not (clear ?ob)) (not (ontable ?ob))
               ( (handempty))))

(:action put-down
  :parameters  (?ob)
  :precondition (holding ?ob)
  :effect (and (clear ?ob) (handempty) (ontable ?ob)
               (not (holding ?ob))))

(:action stack
  :parameters  (?ob ?underob)
  :precondition (and (clear ?underob) (holding ?ob))
  :effect (and (handempty) (clear ?ob) (on ?ob ?underob)
               (not (clear ?underob)) (not (holding ?ob))))

(:action unstack
  :parameters  (?ob ?underob)
  :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
  :effect (and (holding ?ob) (clear ?underob)
               (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))))
