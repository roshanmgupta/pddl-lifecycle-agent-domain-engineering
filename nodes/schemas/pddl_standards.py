"""Classical PDDL 2.1 standards and constraints."""

STANDARD_CLASSICAL_PDDL_RULES = """
STANDARD CLASSICAL PDDL 2.1 (STRIPS + TYPING) RULES:
1. REQUIREMENTS & SYNTAX:
   - Requirements must strictly be [":strips", ":typing"].
   - All variable names in parameters, preconditions, and effects must start with '?' (e.g., '?x', '?y').
   - Well-formed parenthesized Lisp expressions. Hyphenated lowercase identifiers.
   - PURE STRIPS: Numeric fluents, arithmetic ('+', '-', '*', '/', '>=', '<='), and dummy literals ('(true)', '(false)') are strictly forbidden. Relaxing a condition means omitting it from the '(and ...)' conjunction.

2. TYPES, CONSTANTS & PREDICATES (FIXED PROBLEM CONTRACT P_gold):
   - Acyclic type hierarchy where every declared type inherits from 'object' or a declared parent type.
   - Every object type used in problem ':objects' must be declared in 'types'.
   - NO PREDICATE OVERLOADING: Each predicate symbol must be declared exactly ONCE in 'predicates'. PDDL does not permit signature overloading.
     * If a relation applies across multiple types sharing a supertype, declare it ONCE using the common supertype.
     * If the types are disjoint with distinct semantics, declare separate, dedicated predicate symbols.
   - NO UNION TYPES: Each predicate argument and action parameter must have exactly ONE declared type. Never use '(either a b)' or '(a | b)'.
   - DOMAIN CONSTANTS VS PROBLEM OBJECTS: Problem ':objects' and domain ':constants' share the object namespace and must be disjoint. Never declare problem objects in ':constants'.

3. ACTION SCHEMAS:
   - Parameters: Every variable used in preconditions and effects must be declared in 'parameters' with exactly one type.
   - Preconditions: Positive conditions required to execute. Disjunction ('or'), negative preconditions ('not'), and quantifiers ('forall', 'exists') are forbidden in STRIPS.
   - Effects: Model complete state transitions. Delete facts '(not (pred ...))' and add facts '(pred ...)'. An action must never assert contradictory simultaneous effects '(pred ...)' and '(not (pred ...))'.
   - State Conservation: When an entity vacates a resource, container, or location, assert the positive vacancy/clearance effect upon completion.
"""

STANDARD_DIAGNOSTIC_RULES = """
DIAGNOSTIC GUIDELINES (FIXED PROBLEM P_gold — DOMAIN-ONLY FAULT LOCALIZATION):
- The target problem instance (P_gold) is fixed ground truth and strictly READ-ONLY.
- All diagnostic reports and repair hints must target 'domain.types', 'domain.constants', 'domain.predicates', or 'domain.actions'.
- Failure Categories:
  * 'SYNTAX_PARSE': Malformed expressions, unclosed parentheses, or contradictory simultaneous effects.
  * 'TYPE_SIGNATURE': Type mismatch between arguments and declared predicate signature, arity mismatch, or missing subtype hierarchy in 'types'.
    - If an argument is conceptually a subtype of the expected parameter type, declare the inheritance in 'domain.types'.
    - If the expected parameter type already inherits from the argument type, generalize the predicate's parameter in 'predicates' to the supertype.
    - If predicate arity diverges from problem ':init'/':goal', align the predicate signature in 'predicates' and all 'actions' to match P_gold arity.
  * 'GROUNDING_UNSOLVABILITY': Planner reports unsolvable, deadlock, or unreachable goals.
    - Check for EMPTY PARAMETER DOMAINS (0 groundings): Ensure problem object types inherit from action parameter types in 'domain.types'.
    - Check for UNPRODUCED GOALS: If a goal predicate is never added by any action, add the positive effect to the appropriate producer action.
    - Check for DEAD / UNGROUNDABLE PRECONDITIONS: Verify variable binding and argument order against declared initial state facts.
    - MONOTONICITY OF REACHABILITY: Adding preconditions strictly shrinks reachable state space. Never advise adding restrictive preconditions to resolve unsolvability.
- Prescriptive Directives: Every report must state: 1) exact domain AST target, 2) concrete operation (ADD, REMOVE, REPLACE), 3) exact PDDL literal or signature to write.
"""

STANDARD_REPAIR_RULES = """
REPAIR INSTRUCTIONS (SURGICAL DOMAIN REPAIR AGAINST FIXED PROBLEM P_gold):
- Treat the current domain blueprint as a working draft to surgically edit. Preserve all elements that are already correct.
- Fixed Problem P_gold is read-only: resolve all errors exclusively in 'types', 'constants', 'predicates', or 'actions'.
- Action Preservation: Output action count must equal or exceed baseline. Never remove valid actions to bypass an error; repair preconditions or effects.
- Type Hierarchy Repair: Update 'types' to declare subtype relationships required by problem objects and action parameters.
- Predicate Signatures: Keep declared predicate signatures invariant across the entire domain. Unify duplicate declarations under common supertypes.
- Causal Reachability: Restore missing positive transition effects (e.g. clearance, vacancy, arrival) mandated by requirements.
- Relational Argument Alignment: When a diagnostic directive indicates that a relational precondition or effect has an inverted argument permutation (e.g. '(rel ?x ?y)' vs '(rel ?y ?x)'), REPLACE the inverted literal with the directed relation indicated by the oracle. Do NOT keep both, as requiring contradictory or unasserted relations causes plan failure.
- Pure STRIPS: Never introduce negative preconditions, disjunctive preconditions ('or'), or dummy literals ('(true)', '(false)').
"""
