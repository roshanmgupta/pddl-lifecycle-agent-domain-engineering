; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_unsatisfiable_precondition_2
; DOMAIN: blocksworld
; MUTATION OPERATOR: OPERATOR_1_UNSATISFIABLE_PRECONDITION
; TARGET ACTION SCHEMA: unstack
; INJECTED FLAW: Added unsatisfiable precondition '(unreachable_precondition)' to action 'unstack'
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: Remove '(unreachable_precondition)' from action 'unstack' preconditions.
; ==============================================================================

(define (domain blocksworld-4ops)
  (:requirements :strips)
(:predicates (unreachable_precondition)
  (clear ?x)
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
  :effect (and (handempty) (clear ?ob) (on ?ob ?underob)
               (not (clear ?underob)) (not (holding ?ob))))

(:action unstack
  :parameters  (?ob ?underob)
  :precondition (and (unreachable_precondition) (on ?ob ?underob) (clear ?ob) (handempty))
  :effect (and (holding ?ob) (clear ?underob)
               (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))))
