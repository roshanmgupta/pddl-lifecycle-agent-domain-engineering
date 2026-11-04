; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: flaw_02_missing_goal_add_effect
; DOMAIN: pegsol08
; MUTATION OPERATOR: OPERATOR_2_REMOVE_GOAL_ADD_EFFECT
; TARGET ACTION SCHEMA: end-move
; INJECTED FLAW: Removed vital add effect '(move-ended)' from action 'end-move'
; RATIONALE: Prevents action 'end-move' from producing necessary goal/causal atom
; GROUND TRUTH FIX: Restore add effect '(move-ended)' in action 'end-move' effects.
; ==============================================================================

;; Peg Solitaire sequential domain

(define (domain pegsolitaire-sequential)
    (:requirements :typing)
    (:types location - object)
    (:predicates
        (IN-LINE ?x ?y ?z - location)
        (occupied ?l - location)
        (free ?l - location)
        (move-ended)
        (last-visited ?l - location)
    )

    (:action jump-new-move
     :parameters (?from - location ?over - location ?to - location)
     :precondition (and 
                       (move-ended)
                       (IN-LINE ?from ?over ?to)
                       (occupied ?from)
                       (occupied ?over)
                       (free ?to)
                   )
     :effect (and
                 (not (move-ended))
                 (not (occupied ?from))
                 (not (occupied ?over))
                 (not (free ?to))
                 (free ?from)
                 (free ?over)
                 (occupied ?to)
                 (last-visited ?to)
             )
    )

    (:action jump-continue-move
     :parameters (?from - location ?over - location ?to - location)
     :precondition (and 
                       (last-visited ?from)
                       (IN-LINE ?from ?over ?to)
                       (occupied ?from)
                       (occupied ?over)
                       (free ?to)
                   )
     :effect (and
                 (not (occupied ?from))
                 (not (occupied ?over))
                 (not (free ?to))
                 (free ?from)
                 (free ?over)
                 (occupied ?to)
                 (not (last-visited ?from))
                 (last-visited ?to)
             )
    )

    (:action end-move
     :parameters (?loc - location)
     :precondition (last-visited ?loc)
     :effect (and
                 
                 (not (last-visited ?loc))
             )
    )
)
