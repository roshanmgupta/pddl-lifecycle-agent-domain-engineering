# Research Brief & Architectural Deep Dive: SPAR (2025)
## Paper: "SPAR: Scalable LLM-based PDDL Domain Generation for Aerial Robotics"
**Authors**: Songhao Huang, Yuwei Wu, Guangyao Shi, Gaurav S. Sukhatme, Vijay Kumar  
**Affiliations**: GRASP Lab, University of Pennsylvania; Department of Computer Science, University of Southern California  
**Preprint / Publication**: arXiv:2509.13691v1 [cs.RO], 17 Sep 2025  
**Framework Name**: SPAR (Scalable PDDL Domain Generation for Aerial Robotics)  

---

## 1. Problem Statement

- **Domain**: Automated Planning and Robotics (Unmanned Aerial Vehicles / Multi-Robot Systems).
- **Research Area**: Large Language Model (LLM) based PDDL Domain Model Generation, Auto-Formalization, and Bidirectional Semantic Validation.
- **Core Challenge**: While LLMs show reasonable proficiency at generating PDDL problem instances for a fixed domain, generating reusable PDDL domain models (`D = (F, A)`) from ambiguous or incomplete natural language is fraught with syntactic failures (type mismatches, ill-formed expressions) and semantic invalidity (missing preconditions, inconsistent state transitions, unreachable actions). In real-world robotic environments (e.g., UAV operations in 3D spaces with battery/energy constraints and multi-agent coordination), domain authoring is labor-intensive, error-prone, and requires high formal modeling expertise.
- **Why Existing Approaches Fall Short**:
  1. *Assumption of Perfect Prior Knowledge*: Prior LLM-to-PDDL works (e.g., LLM+P, PROC2PDDL, Mahdavi et al.) assume access to complete action descriptions, pre-declared predicates, or ground-truth simulator environments. Non-expert users cannot provide formal predicate signatures.
  2. *Monolithic Generation Fragility*: Generating an entire domain in a single monolithic prompt leads to severe token-drift, hallucinated predicates, and undeclared types.
  3. *Inability to Handle Numeric Planning*: Standard PDDL parsers/validators (like Tarski) support classical STRIPS but break on numeric functions (e.g., battery levels, payload capacities, obstacle distances), which are essential for physical robots.
  4. *Lack of Open-Loop Semantic Verification*: Most LLM benchmarks only evaluate syntactic validity or planner executability (`can a plan be found?`). They fail to verify whether generated plans are executable in the true physical domain (feasibility) or whether ground-truth plans are admitted by the generated domain (interpretability).
- **Abstract Problem Formulation**:
  > Given an incomplete natural language domain description `Nd`, an incomplete set of natural language action specifications `NA = {Nai}`, and external type declarations `Extern`, how can an autonomous agent generate a syntactically correct and semantically sound PDDL domain `D_gen = (F_gen, A_gen)` capable of solving goal instances while remaining robust to lexical ambiguity, missing fluent declarations, and numeric constraint violations?

---

## 2. Data Assets

### Primary Dataset: SPAR UAV Planning Benchmark
- **Description**: 30 diverse UAV-related PDDL planning domains paired with ground-truth problem instances and natural language descriptions (`Nd`, `NA`). It models realistic robotic operations including 3D navigation, payload delivery, aerial manipulation, multi-robot coordination, and numerical resource consumption.
- **Location / Origin**: Curated by the authors from academic UAV literature, practical robotics studies, and modified International Planning Competition (IPC) domains, explicitly designed to be unseen in general LLM pre-training corpora.
- **Size**: 30 domains; each domain has 9 ground-truth problem instances stratified by difficulty:
  - 3 Simple problems (solvable in 1 to 2 actions).
  - 3 Medium problems (require nearly the full action set).
  - 3 Hard problems (require the complete action set and multi-agent coordination/constraints).
  - Total: 270 evaluation problem instances.
- **Domain Categories (7 Classes)**:
  1. *Navigation* (4 domains): 2DNavigation, HouseNavigation, MultiCamLand, SimpleNavigation.
  2. *Transportation* (9 domains): AirPassenger, CityCargo, Delivery, DeliveryCapacity, DeliveryDurative, DeliveryPriority, MedsDelivery, MedsDeliveryEnergy, MealDelivery.
  3. *Manipulation* (5 domains): BlockWorld, CeilingPaint, GraspDelivery, GraspFruit, Watering.
  4. *Monitoring* (4 domains): AirPollution, ForestFireCollaboration, MaintenanceComponent, MovableObs.
  5. *Exploration* (2 domains): GridExplore, MarsExploration.
  6. *Aerial Operations* (5 domains): Gate, Landing, Perching, Tracking, WindDisturbance.
  7. *Adaptation* (2 domains): TerrainAdapt, SpeedAdapt.
- **Key Columns / Elements**:
  - `Nd`: Natural language overview of the operational environment.
  - `Nai`: Natural language description of each individual action (often incomplete/abstracted).
  - `Extern`: Declared object types and PDDL requirements (e.g., `:strips`, `:typing`, `:numeric-fluents`).
  - `D_gt`: Handcrafted ground-truth PDDL domain file.
  - `P_gt`: Ground-truth PDDL problem files.

### Data Quirks and Known Issues
- Action descriptions are intentionally incomplete (they omit explicit precondition/effect lists).
- Numeric fluents are present in several domains (e.g., battery levels, water volumes), introducing operator complexity (`+`, `-`, `>`, `<=`).
- High variation in domain coupling: Simple navigation has low action coupling, whereas multi-robot manipulation (e.g., `MovableObs`, `Watering`) has high predicate interdependency.

### Infrastructure Code & Simulation Assets
- **Gazebo Simulation Suite**: 20 customized Gazebo simulation environments matching the domain categories, enabling full-stack physical plan execution of generated PDDL plans.
- **Embedding Model**: `sentence-transformers/all-mpnet-base-v2` for dense semantic vector retrieval of abstracted action templates.
- **Planners & Validators**: ENHSP-20 (Expressive Numeric Heuristic Search Planner) and VAL (Plan Validation Tool).

---

## 3. Domain Context

### Key Terminology
- **PDDL Domain (`D`)**: Defines types, predicates, numeric functions, and parameterized action schemas (`Pre(a)`, `Eff(a)`).
- **PDDL Problem (`P`)**: Grounded instance defining specific objects, initial world state facts (`:init`), and goal conditions (`:goal`).
- **Dynamic Fluent List**: An incrementally updated registry of state variables (`F`) maintained during action-by-action generation to ensure variable naming consistency across actions.
- **Action Abstraction**: Stripping domain-specific nouns, adjectives, and numbers from natural language descriptions into generalized tokens (`[object]`, `[state]`, `[value]`) while retaining verb semantics.
- **Bidirectional Domain Validation**: Evaluating semantic equivalence between generated and ground-truth domains via cross-execution of plans in VAL:
  - *Feasibility (Forward Validation)*: Executing the Generated Plan on the Ground-Truth Domain.
  - *Interpretability (Inverse Validation)*: Executing the Ground-Truth Plan on the Generated Domain.
- **Domain Complexity Score**: A composite structural metric (ranging from 2.79 to 15.23) based on 9 domain graph attributes.

### Domain Constraints
- **Syntactic Correctness**: Well-formed S-expressions, parameter variable prefixes (`?`), acyclic types under `object`, and valid numeric syntax.
- **Physical Executability**: Actions generated must adhere to real-world causality (e.g., a drone cannot pour water without first loading a pot and flying to a water source).

### Standards and Conventions
- Classical PDDL 2.1 (STRIPS + Typing + Numeric Fluents).
- VAL (Fox & Long 2003) validation standard.

### Practitioner Expectations
- Domain generation must not require non-expert users to write formal mathematical logic.
- Generated domains must compile directly in classical planners (ENHSP, Fast Downward) without manual human patching.

---

## 4. Target Venue & Publication Profile

- **Target Venue**: IEEE International Conference on Robotics and Automation (ICRA) / IEEE Transactions on Robotics (T-RO).
- **Audience**: Roboticists, Automated Planning researchers, Autonomous Systems engineers.
- **Quality Expectations**:
  - Formal experimental benchmarking on diverse, unseen domains.
  - Rigorous ablation of prompting strategies (Format vs. CoT vs. Retrieval vs. Combined).
  - Closed-loop physical simulation (Gazebo) proving practical robotic feasibility beyond toy benchmarks.

---

## 5. Success Criteria & Metrics

### Primary Metrics
1. **Executability (Problem-Solving Rate %)**:
   - Percentage of generated problems that the classical planner (ENHSP-20) can solve using the generated domain.
   - Result in SPAR: SPAR achieves 95.19% executability with GPT-4.1-mini (+14% over baseline Format prompting).
2. **Feasibility (Forward Validation %)**:
   - Percentage of generated plans (`Plan_gen`) that successfully validate against the Ground-Truth Domain (`D_gt`) using VAL.
   - Measures: *Are the plans produced by the LLM domain actually legal and viable in the real world?*
3. **Interpretability (Inverse Validation %)**:
   - Percentage of Ground-Truth Plans (`Plan_gt`) that successfully validate against the Generated Domain (`D_gen`) using VAL.
   - Measures: *Can the LLM domain accurately reproduce and permit real ground-truth behaviors?*

### Secondary Metrics
- **Syntax Error Frequency by Category**:
  - Object type mismatch.
  - Predicate / function naming conflicts.
  - Predicate / function formatting.
  - Predicate / function usage (arity, argument types).
  - Numeric usage (operator nesting, mixing fluents and predicates).
- **Domain Complexity Score (Composite 9-Factor Metric)**:
  - Factors: (1) action count, (2) object type count, (3) predicate count, (4) function count, (5) avg preconditions per action, (6) avg effects per action, (7) interdependency score (avg actions referencing a fluent), (8) action coupling score (effect conditions that serve as preconditions elsewhere).
  - Split threshold: 5.23 (Blocksworld complexity). Domains <= 5.23 are Simple (14 domains); > 5.23 are Complex (16 domains).

### Calibration, Uncertainty & Robustness
- **Interpretability vs. Feasibility Gap**: In all tested models, Interpretability is significantly higher than Feasibility. This proves that LLMs readily generate *permissive* action models that allow valid behavior, but frequently miss subtle negative preconditions or side-effects, generating invalid plans.
- **Complexity Sensitivity**: Errors grow rapidly in complex domains (> 5.23 complexity), demonstrating that reasoning degradation correlates directly with causal coupling.

### Deployability & Practical Feasibility
- Proved on 20 Gazebo robotic worlds including multi-UAV watering and heterogeneous UAV-UGV obstacle manipulation.

---

## 6. Comparator Methods

The paper systematically benchmarks four prompting configurations across two LLMs (GPT-4.1-mini and DeepSeek-Chat):

| # | Method Name | Architecture / Prompt Structure | Strengths | Weaknesses | Why Included |
|---|-------------|---------------------------------|-----------|------------|--------------|
| 1 | **Format** (Guan et al. 2023) | Prompted with 2 regular fixed in-context examples for syntactic format referencing. | Simple, minimal prompt overhead. | Highest syntax error count (41 errors on GPT, 62 on DeepSeek); low executability. | Standard baseline for few-shot PDDL generation. |
| 2 | **Format+CoT (FCoT)** | 2 regular fixed in-context examples, each containing 3-step Chain-of-Thought reasoning. | Drastically reduces object type errors; improves problem solving by ~16% on GPT. | CoT alone does not improve feasibility or interpretability; high predicate usage errors. | Evaluates isolated contribution of step-by-step reasoning. |
| 3 | **Format+Semantic (FS)** | 1 regular format example + 1 semantically relevant retrieved action example (no CoT). | Improves semantic relevance; lower syntax errors on GPT. | Unstable on DeepSeek (structural hallucination from retrieved action); lacks reasoning structure. | Isolates retrieval-augmented generation without CoT. |
| 4 | **SPAR (Ours: Retrieval+CoT)** | Action-by-action generation + abstracted semantic retrieval (all-mpnet-base-v2) + 3-step CoT + iterative syntax feedback loop. | Highest executability (95.19%), lowest overall syntax errors, superior feasibility and interpretability. | Requires embedding index and multi-turn syntax validation calls. | Proposed complete framework. |

---

## 7. Adjacent Fields & Cross-Disciplinary Analogies

- **Abstract Version of the Problem**:
  - Translating unconstrained natural language narratives into formal First-Order Logic transition systems under partial observability of invariants.
- **Analogous Concepts in Other Disciplines**:
  1. *Program Synthesis & Auto-formalization*: Synthesizing typed function contracts (pre/post-conditions) from docstrings (e.g., Dafny, Lean 4, Coq).
  2. *Software Fault Localization & Repair (APR)*: Spectrum-based fault localization and iterative test-suite driven patching.
  3. *Information Extraction / Relation Extraction*: Extracting typed entities and n-ary relations into ontology knowledge bases.

---

## 8. Evaluation Design

### Computational Setup & Tools
- **LLMs**: GPT-4.1-mini-2025-04-14, DeepSeek-Chat.
- **Embedding Model**: `all-mpnet-base-v2` for cosine-similarity dense retrieval over masked action signatures.
- **Search & Planning**: ENHSP-20 for numeric planning instances; Fast Downward / VAL for plan validation.
- **Re-ranking**: Top-K retrieved candidates re-ranked by LLM before in-context injection.

### Protocol Splits
- 30 Domains evaluated across 270 total problems (90 Simple, 90 Medium, 90 Hard).
- Cross-domain exclusion: When retrieving examples for domain `D`, all actions from `D` are strictly omitted from the vector index to prevent data leakage.

### Evaluation Loop
```
[Incomplete NL Action Nai]
       │
       ▼
[Action Abstraction: [object], [state], [value]]
       │
       ▼
[Dense Embedding (all-mpnet-base-v2) + Top-K Retrieval + LLM Re-Ranking]
       │
       ▼
[3-Step CoT Prompting: Objects -> Preconditions -> Effects]
       │
       ▼
[Action PDDL Candidate] ───► [Syntax Checker (STRIPS + Numeric)]
                                  │
                  ┌───────────────┴──────────────┐
                  ▼                              ▼
             [Errors Found]                 [Syntax Valid]
                  │                              │
         [Prompt Feedback Loop]         [Add Fluents to Dynamic Fluent List]
         (Max Iterations)                        │
                                                 ▼
                                        [Compile Domain D_gen]
                                                 │
                                                 ▼
                             ┌───────────────────┴───────────────────┐
                             ▼                                       ▼
                  [Forward Validation]                     [Inverse Validation]
              (Plan_gen on D_gt via VAL)               (Plan_gt on D_gen via VAL)
                    = FEASIBILITY                           = INTERPRETABILITY
```

---

## 9. Scope and Non-Goals

### What the Paper Does NOT Try to Do
1. *Does NOT automate problem generation independently of ground truth*: Problems were synthesized to share initial states and goals with the ground-truth benchmark.
2. *Does NOT perform automated semantic repair of unreachable plans*: If a plan fails feasibility or interpretability, SPAR does not run an automated causal fault-localization or repair cycle on the domain; it only records the score.
3. *Does NOT address open-world non-deterministic transitions*: Assumes deterministic STRIPS / numeric planning.
4. *Does NOT learn PDDL from sensory observation traces*: Input is natural language text, not raw robot telemetry or video.

### Known Limitations
- The framework is evaluated exclusively on UAV and aerial robotic applications (domain-specific benchmark).
- Action-by-action generation can sometimes lead to redundant predicates if the dynamic fluent list is not rigorously deduplicated.
- DeepSeek showed structural instability when transferred examples had divergent syntactic structures.

---

## 10. Reference Papers & Literature Context

1. **Guan et al. (NeurIPS 2023)**: *Leveraging Pre-trained LLMs to Construct and Utilize World Models*. Established the format-based prompting baseline and initial syntax feedback loop for PDDL domain generation.
2. **Smirnov et al. (ICRA 2024)**: *Generating Consistent PDDL Domains with Large Language Models*. Introduced intermediate JSON markup, 15 syntax error classifications, and Fast Downward reachability checks.
3. **Zhang et al. / PROC2PDDL (2024)**: Explored procedural text-to-PDDL generation using Zone of Proximal Development (ZPD) prompting.
4. **Mahdavi et al. (NeurIPS 2024)**: Introduced bidirectional environment validation for PDDL domains.
5. **Liu et al. / LLM+P (2023)**: Demonstrated problem-file generation given fixed ground-truth domain models.
6. **Fox & Long (2003) / VAL**: Standard plan validation engine underpinning forward and inverse semantic verification.

---

## 11. Architectural Mapping & Synthesis for Our Master Thesis

This section provides the critical bridge between SPAR's findings and our thesis architecture (`PDDLLifeCycleBench` / `nodes/`):

### A. Core Architectural Alignments
1. **Bidirectional Semantic Validation is Mandatory**:
   - SPAR confirms that **high problem-solving executability (95.19%) is deceptive**. A domain can easily solve its own generated problems while producing physically impossible plans.
   - *Thesis Implementation*: Our evaluation suite must implement SPAR's bidirectional validation metrics:
     - **Semantic Soundness (Feasibility)**: `VAL(D_standard, P_standard, Plan_generated) == VALID`.
     - **Task Completeness (Interpretability)**: `VAL(D_generated, P_standard, Plan_standard) == VALID`.
     - **Logical Consistency**: Zero contradiction between pre-state assertions and action post-conditions across all generated actions.
2. **Dynamic Fluent Registry vs. Blueprint AST**:
   - SPAR discovered that generating actions sequentially requires a dynamic registry of fluents to prevent predicate proliferation.
   - *Our System Advantage*: Our system uses a strongly typed Pydantic AST (`DomainBlueprint`, `ActionBlueprint`, `PredicateBlueprint` in `schemas/pddl_blueprint.py`). Rather than loose natural language fluent lists, our AST enforces predicate arity, parameter scoping, and typing deterministically before PDDL code emission.
3. **Structured Diagnostic Feedback Protocol**:
   - SPAR's syntax feedback (Example 2: *"Head 'at' in 'Preconditions' is a predicate but should be a function"*) mirrors our `nodes/triage.py` and `config/pddl_standards.py` error taxonomy.
   - When an LLM fails, unstructured raw error logs cause hallucinations; structured feedback with explicit error categories and actionable guidance yields reliable multi-turn convergence.

### B. Crucial Divergence: Domain-Agnostic Mandate vs. Aerial Robotics
- **SPAR's Limitation**: SPAR tailored its taxonomy, abstractions, and evaluation entirely to UAVs (aerial robotics).
- **Our Thesis Mandate (AGENTS.md Principle 1 & 2)**:
  - Our agent system is **strictly domain-agnostic**.
  - We must **never** hardcode UAV concepts (`uav`, `fly`, `battery`, `waypoint`) into prompts, heuristics, or repair rules.
  - SPAR's 9-factor domain complexity metric and bidirectional validation protocol can be adopted universally for ANY classical PDDL domain (Blocksworld, Gripper, Barman, Logistics, Rovers, Satellite).

### C. Synthesis Summary Table: SPAR (2025) vs. Our PDDL Lifecycle Agent

| Dimension | SPAR (Huang et al. 2025) | Our Thesis System (`pddl_lifecycle_agent`) |
| :--- | :--- | :--- |
| **Domain Scope** | Specialized: UAV & Aerial Robotics | Universal: Strictly Domain-Agnostic (AGENTS.md) |
| **Generation Paradigm** | Action-by-Action with RAG + 3-step CoT | Holistic Elicitation into Pydantic AST Blueprints |
| **Intermediate Rep.** | Textual Dynamic Fluent List + S-expressions | Formal Pydantic AST (`DomainBlueprint`, `ProblemBlueprint`) |
| **Syntax Validation** | Extended STRIPS + Numeric Syntax Checker | Multi-layer: Pydantic AST Schema + PDDL Standards + Compilers |
| **Semantic Validation** | Bidirectional: Feasibility & Interpretability | Tripartite: Soundness (Feasibility), Completeness (Interpretability), Logical Consistency |
| **Fault Localization** | Local syntax error detection only | Layered: Spectrum-Based Fault Localization + Causal Graphs |
| **Automated Repair** | Basic re-prompting with syntax feedback | Closed-loop iterative semantic repair with targeted AST patching |
| **Physical Embodiment** | 20 Gazebo UAV simulation worlds | Classical Planning Benchmarks (`PDDLLifeCycleBench` / IPC) |
