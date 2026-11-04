# Canonical Domain Modelling and Planning Vocabulary Lexicon

This reference document establishes the formal, literature-grounded vocabulary for the Master's Thesis *"Towards an Autonomous Lifecycle Agent for PDDL Domain Modelling"*. All thesis chapters, agent prompts, code documentation, and explanations must strictly adhere to these definitions and prohibited synonym rules.

---

## 1. Lifecycle Activities & Methodological Phases

| Standard Domain Modelling Term | Prohibited Synonyms / Jargon to Avoid | Formal Literature Definition & Source | Contextual Usage in Thesis |
| :--- | :--- | :--- | :--- |
| **Domain Model Formulation** (or **Domain Generation**) | *Relational semantic induction*, *domain synthesis*, *domain writing*, *model creation* | The process of conceptualizing, formulating, and deriving declarative planning operators (preconditions and effects) from natural-language requirements (Georgievski 2023; Oswald et al. 2024). | "The agent automates domain model formulation over fixed ground-truth signatures." |
| **PDDL Domain Encoding** (or **Deterministic Compilation**) | *Concrete syntax serialization*, *PDDL dumping*, *code stringifying*, *text emitting* | The translation of structured relational schemas or AST representations into standardized concrete PDDL text conforming to formal BNF grammar (McDermott et al. 1998; Fox & Long 2003). | "Decoupling action model formulation from deterministic PDDL domain encoding." |
| **Requirements Elicitation** | *Requirement extraction*, *prompt scraping*, *spec harvesting* | The disciplined extraction of operational concepts, constraints, entities, and behaviors from informal text or stakeholder descriptions (Silva et al. 2020; Georgievski 2023). | "Phase 1 performs requirements elicitation to establish formal domain boundaries." |
| **Plan Validation** | *Plan checking*, *plan testing*, *execution verification* | Independent simulation of an action sequence against initial states and formal domain transition semantics using a certified tool such as VAL (Howey, Long & Fox 2004). | "Plan validation under VAL certifies that state transitions satisfy all action preconditions." |
| **Fault Localization** | *Flaw finding*, *bug hunting*, *defect searching*, *error parsing* | The identification and isolation of the specific action schema, precondition, or effect causing a domain failure (IEEE 610.12; Georgievski 2023). | "Spectrum-based fault localization maps planner counterexamples to defective AST elements." |
| **Multi-Tier Diagnostic Triage** | *Log scraping*, *error debugging*, *trace parsing* | The structured classification of compiler, planner, and validator error signals across hierarchical semantic tiers (Syntax, Typing, Reachability, Trace) (Patil et al. 2024). | "Multi-tier diagnostic triage produces structured diagnostic records without prompt context bloat." |
| **Action Repair** (or **Fault Repair**) | *Model patching*, *bug fixing*, *error tweaking*, *heuristic correction* | Modifying an existing, defective domain model to restore syntactic validity, planner solvability, and physical consistency while avoiding regressions (Silva et al. 2020; Bavandpour & Bercher 2026). | "The repair node executes localized action repair on the isolated AST schema." |
| **Continuous Domain Evolution** | *Domain updating*, *model feature addition*, *code extending* | Extending a previously valid domain model with new capability schemas while preserving backwards compatibility across baseline benchmark instances (Georgievski 2023, 2025). | "Continuous domain evolution introduces target capabilities without causing reachability collapse." |

---

## 2. PDDL Structural & Semantic Elements

| Formal PDDL Term | Formal Notation | Prohibited Synonyms to Avoid | Literature Definition (McDermott 1998; Fox & Long 2003) |
| :--- | :--- | :--- | :--- |
| **Domain Model** | $D$ | *Environment code*, *rule file*, *world model* | The generalized specification of an environment comprising object types, relational predicates, and parameterized action schemas. |
| **Problem Instance** | $P = (O, I, G)$ | *Task file*, *scenario file*, *question instance* | A specific planning problem specifying a set of typed objects $O$, an initial state fact set $I$, and a goal condition formula $G$. |
| **Action Schema** | $a = (\text{params}, \text{pre}, \text{eff})$ | *Operator template*, *action definition*, *command* | A parameterized state-transition rule specifying parameter bindings, applicability preconditions, and state transformation effects. |
| **Precondition** | $\text{Pre}(a)$ | *Prerequisite*, *requirement*, *guard condition* | A first-order logical formula that must evaluate to true in the current state for an action to be applicable. |
| **Add Effect** | $\text{Eff}^+(a)$ | *Positive effect*, *asserted fact*, *add list* | Atomic relational state facts that become true immediately following action execution. |
| **Delete Effect** | $\text{Eff}^-(a)$ | *Negative effect*, *retracted fact*, *delete list* | Atomic relational state facts that cease to be true immediately following action execution. |
| **Relational Predicate** | $p(x_1, \dots, x_k)$ | *Property*, *attribute*, *state label* | A typed relation over domain objects expressing state conditions; partitioned into mutable fluents and static relations. |
| **Type Hierarchy** | $\mathcal{T}$ | *Class inheritance*, *category tree*, *taxonomy* | A partially ordered, acyclic specialization graph of object classes descending from the root type `object`. |

---

## 3. Execution, Oracles & Semantic Verification

| Standard Planning Term | Mathematical Representation | Prohibited Synonyms to Avoid | Literature Definition & Verification Criteria |
| :--- | :--- | :--- | :--- |
| **Forward Soundness** (or **Plan Feasibility**) | $\text{VAL}(D_{\text{gold}}, P_{\text{gold}}, \pi_{\text{gen}}) = \text{SUCCESS}$ | *Physical validity*, *forward correctness*, *real-world fit* | Every plan synthesized on the generated domain executes successfully on the ground-truth physical environment without illegal transitions. |
| **Inverse Completeness** (or **Plan Interpretability**) | $\text{VAL}(D_{\text{gen}}, P_{\text{gold}}, \pi_{\text{gold}}) = \text{SUCCESS}$ | *Backward solvability*, *expressive fit*, *coverage* | Every reference plan synthesized on the ground-truth domain remains fully valid and executable on the generated domain without over-constraint. |
| **Bidirectional Semantic Correctness** | $\text{Soundness} \land \text{Completeness}$ | *Two-way success*, *dual correctness*, *mutual validity* | Strict conjunctive gate requiring both forward soundness and inverse completeness across all reference problems assigned to the task. |
| **Syntactic Validity Rate (SVR)** | $\text{SVR} = \frac{N_{\text{valid}}}{N_{\text{total}}}$ | *Parse rate*, *compilation accuracy*, *syntax score* | The percentage of generated domain files that parse without errors under a formal PDDL validator (`Validate -v`). |
| **Plan Trajectory** (or **Plan Sequence**) | $\pi = \langle a_1, a_2, \dots, a_k \rangle$ | *Action list*, *solution path*, *step trace* | A finite, linearly ordered sequence of grounded action instances that transforms the initial state $I$ into a state satisfying goal $G$. |
| **Ground-Truth Domain** | $D_{\text{gold}}$ | *Gold standard*, *canonical domain*, *correct file* | The authoritative, human-engineered reference domain model from the International Planning Competition (IPC). |
| **Reference Problems** | $\mathcal{P}_{\text{ref}}$ | *Benchmark problem suites*, *canonical problems* | Standardized, ground-truth problem instances used to evaluate domain solvability and plan execution. |

---

## 4. Agent Architecture & Computational Terms

| Architectural Term | Standard Definition | Prohibited Synonyms / Jargon to Avoid | Technical Justification |
| :--- | :--- | :--- | :--- |
| **Autonomous Lifecycle Agent** | The closed-loop neuro-symbolic system orchestrating formulation, compilation, validation, triage, and repair. | *Language model*, *LLM*, *GPT-4o*, *the model* (when referring to the system architecture) | The language model is merely the completion backbone; the *agent* is the autonomous graph system. |
| **Intermediate AST Blueprint** | Strongly typed, validated in-memory Pydantic data structure holding domain actions and invariants prior to compilation. | *JSON prompt*, *intermediate format*, *data dictionary* | Formal compiler terminology; enforces typing and parameter scope contracts. |
| **Deterministic Programmatic Compiler** | Algorithmic code serializer that parses the AST and emits canonical PDDL syntax without stochastic LLM variation. | *Code stringifier*, *syntax serializer*, *PDDL printer* | Emphasizes that compilation is algorithmic, guaranteeing 100% SVR by construction. |
| **Prompt Context Bloat** | Degradation of LLM reasoning performance caused by injecting raw, unparsed multi-kilobyte compiler and planner logs into prompts. | *Log bloat*, *prompt overload*, *token spam* | Academic standard term in LLM literature (Patil et al. 2024). |
| **Unstructured Re-prompting** | Re-prompting an LLM iteratively with raw compiler or planner stdout dumps without diagnostic triage (`ABLATION_NO_TRIAGE`). | *Naive retry*, *iterative retry*, *raw retry loop* | Formal baseline specification; avoids colloquial "retry". |
| **Zero-Shot Baseline** | Single-turn domain generation without closed-loop feedback or symbolic execution (`ZERO_SHOT`). | *Direct generation*, *one-pass model*, *vanilla prompt* | Literature-grounded baseline naming (Oswald et al. 2024). |

---

## 5. Prohibited Jargon & Replacement Quick-Lookup

| Prohibited Jargon / Hallucinated Term | Mandatory Canonical Replacement | Context / Rationale |
| :--- | :--- | :--- |
| *Relational semantic induction* | **Action model formulation** (or **Domain formulation**) | "Induction" is ML/ILP jargon; domain engineering uses formulation/acquisition. |
| *Concrete syntax serialization* | **PDDL domain encoding** (or **PDDL compilation**) | "Serialization" is generic CS jargon; PDDL domain encoding is the planning standard. |
| *Synthesis* (domain / plan) | **Generation** (*domain generation*, *plan generation*) | Standardized across the thesis and supervisor directives. |
| *Bug* / *Flaw* (in prose) | **Fault** (or **Defect**) | Aligns with IEEE standard fault/error/failure taxonomy. |
| *Fix* / *Fixing* / *Patching* | **Repair** (*action repair*, *fault repair*) | Standard PDDL lifecycle terminology; "fix" is colloquial. |
| *Two-way semantic success* | **Bidirectional semantic correctness** | Standardized formal terminology across all chapters. |
| *Log bloat* | **Prompt context bloat** | Academic terminology in LLM systems research. |
| *When a language model generates...* | **When an autonomous agent generates...** | Clarifies that the experimental condition tests the agent architecture, not the raw LLM. |
| *Canonical domain / problems* | **Ground-truth domain / Reference problems** | "Canonical" is reserved for algorithmic sorting; reference/ground-truth is planning standard. |
