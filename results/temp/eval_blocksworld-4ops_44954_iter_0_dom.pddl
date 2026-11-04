; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_01_unsatisfiable_precondition
; DOMAIN: blocksworld
; MUTATION OPERATOR: OPERATOR_1_UNSATISFIABLE_PRECONDITION
; TARGET ACTION SCHEMA: pick-up
; INJECTED FLAW: Added unsatisfiable precondition '(unreachable_precondition_predicate)' to action 'pick-up'
; RATIONALE: Action can never be grounded or executed because predicate is absent from :init
; GROUND TRUTH FIX: Remove '(unreachable_precondition_predicate)' from action 'pick-up' preconditions.
; ==============================================================================

(define (domain blocksworld-4ops)
  (:requirements :strips)
(:predicates (clear ?x)
             (ontable ?x)
             (handempty)
             (holding ?x)
             (on ?x ?y)
    (unreachable_precondition_predicate)
  )

(:action pick-up
  :parameters (?ob)
  :precondition (and (unreachable_precondition_predicate) (clear ?ob) (ontable ?ob) (handempty))
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
  :precondition (and (on ?ob ?underob) (clear ?ob) (handempty))
  :effect (and (holding ?ob) (clear ?underob)
               (not (on ?ob ?underob)) (not (clear ?ob)) (not (handempty)))))
