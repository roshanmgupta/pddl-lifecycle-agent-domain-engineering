from pathlib import Path

target_file = Path("scientific-thesis-template-fresh/chapters-en/30 - problem exposition.tex")

content = r"""% !TeX root = ../thesismain.tex
%%% ===============================================================================
\chapter{Related Work}\label{sec:related-work}
%%% ===============================================================================

Learning, synthesizing, and maintaining declarative domain models has been a central challenge in automated planning for decades~\cite{ghallab2004,georgievski2023}.
Traditionally, domain engineering required specialized human knowledge engineers to manually translate operational requirements into formal \gls{pddl} action schemas—a process that is notoriously laborious, time-consuming, and error-prone~\cite{mcdermott1998,georgievski2023,patil2024}.
Early computational efforts addressed this bottleneck through machine learning techniques that induced action models from empirical state trajectories, execution logs, or partially observed plan traces~\cite{shetye2025}.
However, trace-based induction methods critically depend on the availability of extensive, high-quality execution data, which is rarely accessible when designing novel planning environments from scratch~\cite{shetye2025,tantakoun2025}.

The rapid emergence of Large Language Models (\gls{llm}s) has catalyzed a paradigm shift, enabling automated domain acquisition directly from unstructured natural language task specifications~\cite{chen2021,tantakoun2025}.
This chapter provides a comprehensive review of prior research directly relevant to this thesis, structured into three primary research areas:
First, automated planning domain generation using \gls{llm}s is examined (\zcref{sec:related:domain-generation}).
Second, formal verification engines and neuro-symbolic planning architectures are analyzed (\zcref{sec:related:verification}).
Third, automated \gls{pddl} domain model fault localization and repair frameworks are reviewed (\zcref{sec:related:repair}).
Finally, the identified research gaps are synthesized to establish the concrete positioning of the autonomous lifecycle agent developed in this thesis (\zcref{sec:related:positioning}).

% ---------------------------------------------------------------------------------
\section{LLM-Based Planning Domain Generation}\label{sec:related:domain-generation}
% ---------------------------------------------------------------------------------

The paper ``Large Language Models as Planning Domain Generators'' by Oswald et al.~\cite{oswald2024} explores how to automate the generation of \gls{pddl} domain models using \gls{llm}s.
The study provides an automated evaluation framework that uses \gls{llm}s to convert natural language descriptions into \gls{pddl} domain files.
Model outputs are measured with automated syntactic and plan-level tests, including Action Reconstruction Error and heuristic domain equivalence.
This method represents a significant improvement over previous studies that relied on subjective human assessment, offering a scalable and objective methodology to evaluate model quality.
Their research tests seven \gls{llm}s across nine planning domains.
The results indicate that although larger models can identify key aspects of domain models, their outputs frequently have persistent syntactic errors and semantic mismatches.
Crucially, the findings reveal that syntactic correctness does not ensure similar planning performance, pointing out a critical gap between plausible-looking generation and real planning usability.
The paper concludes that better feedback and correction methods are necessary for robust domain model induction.
These insights directly support this thesis, which tackles these limitations by decoupling relational semantic reasoning into an Abstract Syntax Tree (\gls{ast}) intermediate representation~\cite{x}.
By employing a deterministic algorithmic compiler, syntactic validity is mathematically guaranteed by construction, while a four-layer diagnostic triage engine isolates semantic errors and guides targeted repair without relying on raw, unstructured log dumps~\cite{oswald2024,x}.

The paper ``Generating Domain Models for Automated Planning from Natural Language Descriptions'' by Acitelli et al.~\cite{acitelli2024} presents a modular pipeline for translating unstructured natural language texts into formal \gls{pddl} domain specifications.
The study observes that generating full \gls{pddl} domains in a single end-to-end prompt overloads the language model, leading to missing predicates and mismatched parameter bindings.
To address this challenge, domain construction is decomposed into a sequence of discrete extraction and refinement stages: first extracting entities and types, then deriving relational predicates, and finally generating action preconditions and effects.
Evaluating this pipeline on thirty benchmark domains from the TEXT2WORLD dataset using human judges and \gls{llm}-as-a-judge evaluators, the study demonstrates that structured stage-wise decomposition substantially improves syntactic validity and domain coherence.
However, generated domains are evaluated primarily through static schema inspection and \gls{llm}-based judgments rather than running dynamic plan validation on reference problems using automated planners.
Consequently, generated domains that appear semantically coherent may still be mathematically unsolvable or physically unsound during plan execution.
This research is important to this thesis because it illustrates the advantage of modularizing the knowledge extraction process~\cite{acitelli2024}.
This thesis advances this principle by using a typed \gls{ast} schema to preserve canonical types, predicates, and signatures, while validating generated domains through rigorous symbolic plan execution via Fast Downward and \gls{val}~\cite{acitelli2024,x}.

The article ``Generating Consistent PDDL Domains with Large Language Models'' by Smirnov et al.~\cite{smirnov2024} examines the problem of semantic inconsistency in automated \gls{pddl} domain modeling.
It is observed that while \gls{llm}s readily generate syntactically plausible Lisp markup from natural language, the resulting action definitions frequently suffer from internal contradictions—such as conflicting preconditions, mutual exclusion violations, and unreachable actions—that render the domain unusable.
To overcome this, an automated consistency-checking mechanism is introduced to evaluate candidate action schemas during the generation process, detecting dead-end states and providing corrective feedback to reduce the burden on human modelers.
Their study evaluates the error-detection framework across five robotics and household domains, showing that consistency checks catch substantial numbers of semantic flaws prior to plan execution.
However, their consistency checking strategies cannot guarantee complete correctness or task solvability, ultimately requiring a human in the loop to finalize the models.
This research is directly relevant to this thesis because it confirms that unguided \gls{llm} text generation is insufficient without automated internal checking~\cite{smirnov2024}.
This thesis goes beyond this approach by replacing heuristic human-in-the-loop checking with a closed-loop autonomous lifecycle, where an intermediate \gls{ast} blueprint eliminates syntax errors by construction, and symbolic planners (Fast Downward and \gls{val}) provide sound, fully automated two-way semantic verification~\cite{smirnov2024,x}.

The paper ``SPAR: Scalable LLM-based PDDL Domain Generation for Aerial Robotics'' by Huang et al.~\cite{huang2025} investigates the automatic generation of \gls{pddl} domain models from natural language task specifications.
The study highlights that manually crafting domain schemas for complex autonomous systems is labor-intensive and error-prone, which impedes the real-world deployment of symbolic planners.
To solve this problem, SPAR is presented as a structured prompting pipeline that guides \gls{llm}s to translate textual descriptions into complete \gls{pddl} domains.
A notable contribution of that work is the introduction of a rigorous multi-criteria evaluation methodology comprising syntax validity, executability, feasibility, and interpretability.
Their empirical evaluation demonstrates that structured prompting enables \gls{llm}s to accelerate domain synthesis across varied robotic tasks.
However, SPAR relies on monolithic text prompting that combines type, predicate, and action generation in an unconstrained manner, leaving the pipeline vulnerable to parenthesis errors and arity mismatches.
Furthermore, when generated models fail execution checks, SPAR does not provide localized, action-level diagnostic repair.
This research is directly relevant to this thesis because it validates the literature-grounded semantic criteria (executability, feasibility, and interpretability)~\cite{huang2025}.
This thesis advances this line of work by introducing an intermediate \gls{ast} layer that eliminates syntax errors entirely and incorporating a four-layer diagnostic triage engine that isolates and repairs domain defects autonomously~\cite{huang2025,x}.

The research article ``PDDLCoder: Agentic PDDL Generation for LLM-Assisted Symbolic Planning'' by Laule et al.~\cite{laule2025pddlcoder} addresses the fragility of direct natural language to \gls{pddl} translation.
The paper argues that existing generation pipelines are overly rigid and lack automated mechanisms to detect and resolve semantic inconsistencies in generated planning models.
To overcome these limitations, PDDLCoder is proposed as an agentic framework that iteratively generates, analyzes, and refines \gls{pddl} models using symbolic feedback.
The work also establishes the NL-pddlgym benchmark, covering 711 planning tasks across 23 domains, to systematically evaluate plan applicability.
Their experimental results show that incorporating agentic verification and iterative refinement increases the plan applicability rate to 89.6\%, substantially outperforming direct \gls{llm} prompting.
However, PDDLCoder prompts the model with raw compiler and validator error messages, which causes prompt bloat and often leads the \gls{llm} to introduce secondary regressions in unrelated actions.
This research is pertinent to this thesis because it emphasizes the power of closed-loop agentic feedback in \gls{pddl} engineering~\cite{laule2025pddlcoder}.
This thesis addresses the feedback granularity limitation of PDDLCoder by implementing a structured four-layer diagnostic triage engine, which parses raw oracle errors into surgical, action-level repair directives, preventing prompt pollution and ensuring efficient convergence~\cite{laule2025pddlcoder,x}.

The paper ``Plan2Evolve: LLM Self-Evolution for Improved Planning Capability via Automated Domain Generation'' by Pan et al.~\cite{plan2evolve2024} explores the role of automated \gls{pddl} domain generation in improving the reasoning capabilities of language models.
An autonomous loop is proposed where an \gls{llm} generates novel planning domains and problems from high-level task goals, which are subsequently validated using classical planners to ensure logical consistency and task solvability.
These verified symbolic models are then used to build training curricula for the model, demonstrating that autonomous domain generation can enhance planning proficiency without manual supervision.
However, Plan2Evolve treats domain generation as an unconstrained open-ended synthesis task, where the model frequently invents arbitrary predicate vocabularies that lack standard benchmarking correspondence.
In addition, when generated domains fail planner validation, the framework discards the domain entirely rather than diagnosing and repairing the faulty action schema.
This study is pertinent to this thesis because it confirms that automated domain generation can be driven autonomously by symbolic solver feedback~\cite{plan2evolve2024}.
This thesis addresses its lack of repair capability by providing a targeted diagnostic triage engine that isolates specific precondition or effect failures, enabling fine-grained, action-level model repair across standardized \gls{ipc} benchmarks~\cite{plan2evolve2024,x}.

% ---------------------------------------------------------------------------------
\section{Formal Verification and Neuro-Symbolic Integration}\label{sec:related:verification}
% ---------------------------------------------------------------------------------

The article ``LLMs Can't Plan, But Can Help Planning in LLM-Modulo Frameworks'' by Kambhampati et al.~\cite{kambhampati2024} offers a critical look at how \gls{llm}s are used in automated planning.
The paper argues that although \gls{llm}s are effective at producing coherent text, they do not possess the internal world models or logical reasoning required for autonomous plan generation and self-checking.
Through extensive empirical investigations across leading models, it is demonstrated that standalone \gls{llm}s rarely generate valid plans and struggle to critique or repair their own mistakes, even when aided by prompting techniques like Chain-of-Thought or iterative self-reflection.
To overcome these inherent limits, the LLM-Modulo framework is introduced, treating \gls{llm}s as heuristic, approximate knowledge generators embedded within an external neuro-symbolic pipeline.
In this architecture, candidate outputs must pass verification by sound, model-based symbolic critics—such as Fast Downward and \gls{val}—before acceptance.
This research is foundational to this thesis because it establishes the necessity of pairing \gls{llm} linguistic synthesis with external formal oracles to guarantee correctness~\cite{kambhampati2024}.
This thesis adopts this modular neuro-symbolic philosophy, but moves beyond plan generation to formalize the complete lifecycle of \gls{pddl} domain model formulation and closed-loop fault repair, utilizing deterministic compilation and two-way semantic verification on ground-truth physics~\cite{kambhampati2024,x}.

The article ``VAL: Automatic Plan Validation, Continuous Effects and Mixed Initiative Planning Using PDDL'' introduces the \gls{val} tool by Howey, Long, and Fox~\cite{howey2004} as the canonical reference standard for validating \gls{pddl} plans.
\gls{val} provides sound execution simulation according to the formal mathematical semantics of \gls{pddl} 2.1, tracking sequential state transitions, precondition satisfiability, and goal satisfaction step by step.
While \gls{val} plays an indispensable role in ensuring that plans are semantically correct and executable, its traditional usage was primarily designed for post-hoc plan validation and mixed-initiative planning workflows where human modelers manually review failure reports.
This thesis builds upon \gls{val}'s formal execution mechanics by integrating its step-by-step simulation directly into the automated lifecycle pipeline~\cite{howey2004,x}.
Rather than serving merely as a terminal plan checker, \gls{val}'s causal execution traces are programmatically captured by the diagnostic triage engine to pinpoint failing actions, identify unsatisfied precondition literals, and construct surgical repair prompts without human inspection~\cite{howey2004,x}.

The paper ``Leveraging Pre-trained Large Language Models to Construct and Use World Models for Model-based Task Planning'' by Guan et al.~\cite{guan2023} introduces a hybrid workflow where pre-trained \gls{llm}s construct \gls{pddl} world models that are subsequently refined through iterative feedback from validators and human experts.
In this paradigm, \gls{llm}s act as collaborative modeling assistants, converting natural language game and task descriptions into declarative planning representations.
Their results show that iterative validation improves plan success rates compared to unguided generation.
However, relying on manual human review during each validation round represents a severe operational bottleneck that prevents autonomous scaling.
Furthermore, the unconstrained mapping from natural language directly into \gls{pddl} text lacks an intermediate representation, resulting in frequent parameter typing mismatches and syntax rejections.
This thesis addresses these limitations by establishing a completely autonomous, closed-loop agent architecture that removes the human from the loop~\cite{guan2023,x}.
By mediating synthesis through an intermediate \gls{ast} blueprint and automating fault localization via four-layer diagnostic triage, the framework achieves autonomous convergence on sound models~\cite{guan2023,x}.

The paper ``There and Back Again: Extracting Formal Domains for Controllable Neurosymbolic Reasoning'' by Silver et al.~\cite{silver2022} investigates neuro-symbolic methods for narrative planning and extraction.
Language models are employed to extract formal, \gls{pddl}-style domain representations from natural language stories, utilizing symbolic planners to generate structured, causal narrative progressions.
The resulting system acts as a human-in-the-loop tool where authors and domain experts review, refine, and correct the generated planning specifications.
While that work illustrates the benefits of combining language model expressiveness with symbolic planning formalisms, it requires ongoing manual oversight to resolve modeling defects.
This thesis builds on the neuro-symbolic synthesis concept demonstrated by Silver et al., but replaces manual oversight with automated symbolic verification and diagnostic triage, demonstrating that domain engineering can be conducted autonomously across standardized planning benchmarks~\cite{silver2022,x}.

% ---------------------------------------------------------------------------------
\section{PDDL Domain Model Fault Localization and Repair}\label{sec:related:repair}
% ---------------------------------------------------------------------------------

The article ``LLM-Only PDDL Domain Repair with Open-Weight Models'' by Bavandpour and Bercher~\cite{bavandpour2026llmonly} investigates whether modern open-weight language models can repair defective \gls{pddl} domain models without external symbolic assistance.
Models are evaluated on their ability to modify faulty action schemas using sets of positive and negative test plans as behavioral constraints.
Their experimental findings show that while top-tier reasoning models can improve repair accuracy over classical heuristic baselines in simpler settings, their reliability drops sharply on complex tasks, falling to a pass rate of just 6\% in challenging domains.
The study identifies that \gls{llm}s frequently struggle with subtle logical dependencies, often breaking valid actions while attempting to fix defective ones.
It is concluded that relying exclusively on an \gls{llm} without symbolic validation is insufficient for dependable model repair.
These insights provide direct empirical motivation for this thesis~\cite{bavandpour2026llmonly}.
Rather than attempting unguided repair, the framework presented in this thesis tightly couples the \gls{llm} with symbolic planning oracles (Fast Downward and \gls{val}) and a structured diagnostic triage engine, providing localized causal failure traces that guide the model to repair isolated mutations without regressing existing action semantics~\cite{bavandpour2026llmonly,x}.

The paper ``Finding Semantically Guided Repairs in PDDL Domains Using LLMs'' by Bavandpour and Bercher~\cite{bavandpour2025} investigates how to repair defective \gls{pddl} domain models using behavioral plan traces and language models.
It is observed that classical model-repair algorithms based on minimum hitting sets identify syntactic fixes from positive (whitelist) and negative (blacklist) execution traces, but lack semantic understanding to distinguish between physically plausible and absurd repairs.
To address this limitation, a hybrid framework is proposed that integrates \gls{llm}s with a formal hitting-set solver, using the semantic cues present in predicate and action names to steer the repair search toward human-interpretable fixes.
While this approach combines formal trace-satisfaction guarantees with \gls{llm} semantic heuristics, it relies on having access to pre-computed positive and negative execution traces, which are often unavailable when authoring new domains from scratch.
Furthermore, the repair process operates globally over propositional grounding sets rather than diagnosing individual action schema components.
This research is directly pertinent to this thesis because it demonstrates the necessity of integrating semantic reasoning with formal verification in domain repair~\cite{bavandpour2025}.
This thesis builds on this foundation by formalizing a four-layer diagnostic triage engine that isolates compiler syntax, translator typing, \gls{val} step simulation, and search reachability deadlocks, repairing isolated single-action mutations without requiring empirical negative execution traces~\cite{bavandpour2025,x}.

The master's thesis ``Error Detection and Correction in PDDL Domain Models Using Large Language Models'' by Patil~\cite{patil2024} explores the use of GPT-4 for identifying and repairing structural and logical defects in \gls{pddl} domain models.
A systematic benchmark is designed containing synthetic syntactic errors, invalid parameters, unmet preconditions, and contradictory effects.
The study evaluates the capacity of GPT-4 to interpret raw error feedback and autonomously repair the faulty models.
The results indicate that while the model exhibits competence in correcting surface-level syntactic mistakes, its performance on semantic bugs is inconsistent.
In particular, errors involving complex relational dependencies and action preconditions frequently lead to cyclic repair failures or regressions.
The study concludes that providing raw, unparsed validator logs to an \gls{llm} is insufficient for dependable error correction.
Patil's findings directly inspire the fault localization architecture of this thesis~\cite{patil2024}.
To overcome the failure modes identified by Patil, this thesis replaces unparsed log dumping with a layered diagnostic triage engine that isolates compiler syntax, translator typing, simulation failures, and search deadlocks, generating focused repair instructions that enable GPT-4o to achieve rapid convergence~\cite{patil2024,x}.

The master's thesis ``Towards LLM-Driven Domain Model Generation Using Answer Set Programming and Formal Validation'' by Shetye~\cite{shetye2025} proposes an automated framework to generate \gls{pddl} domain models from natural language without human intervention.
To address the syntax collapse and semantic inconsistencies common in direct \gls{llm} generation, Answer Set Programming (\gls{asp}) is introduced as an intermediate relational representation.
In that pipeline, the \gls{llm} first formalizes natural language requirements into \gls{asp} rules, which are subsequently translated into \gls{pddl} models via iterative prompting and feedback from the Clingo \gls{asp} solver, Fast Downward, and \gls{val}.
The framework is evaluated across five \gls{llm}s on International Planning Competition benchmark domains.
The results demonstrate that intermediate formalisms and multi-stage symbolic validation substantially improve the solvability and soundness of generated models.
However, Shetye's approach requires two consecutive \gls{llm} translation steps (Text-to-\gls{asp} followed by \gls{asp}-to-\gls{pddl}), compounding token costs and introducing translation drift between the two representations.
Furthermore, fault repair is performed globally across the entire domain file rather than isolating individual defective action schemas.
This thesis builds upon Shetye's foundational insight regarding intermediate representations, but replaces the second non-deterministic \gls{llm} step with a strongly-typed Abstract Syntax Tree (\gls{ast}) blueprint and a deterministic algorithmic compiler~\cite{shetye2025,x}.
This guarantees balanced syntax by construction, while a four-layer diagnostic triage engine enables surgical, action-level repair of isolated mutations~\cite{shetye2025,x}.

% ---------------------------------------------------------------------------------
\section{Synthesis and Positioning of this Thesis}\label{sec:related:positioning}
% ---------------------------------------------------------------------------------

The detailed examination of prior work reveals that while substantial progress has been achieved in applying \gls{llm}s to automated planning, critical limitations persist across existing approaches.
\Cref{tab:related-work-comparison} provides a structured comparative synthesis of the key frameworks in the literature alongside the autonomous lifecycle agent developed in this thesis.

\begin{table}[htbp]
\centering
\small
\caption{Comparative taxonomy of prior works and the proposed autonomous lifecycle agent across representation, compilation, verification oracles, diagnostic triage, and semantic criteria.}\label{tab:related-work-comparison}
\begin{tabularx}{\textwidth}{l p{2.2cm} p{2.2cm} p{2.5cm} p{2.5cm} X}
\toprule
\textbf{Framework} & \textbf{Synthesis Modality} & \textbf{Compilation Approach} & \textbf{Verification Oracles} & \textbf{Diagnostic Triage Level} & \textbf{Evaluation Criteria} \\
\midrule
Oswald et al.~\cite{oswald2024} & Direct PDDL text & Non-deterministic prompting & Fast Downward & None (No repair loop) & Action Reconstruction Error, SVR \\
Guan et al.~\cite{guan2023} & Direct PDDL text & Iterative re-prompting & Planners, Human experts & Raw logs + Human inspection & Plan success rate \\
Huang et al. (SPAR)~\cite{huang2025} & Direct PDDL text & Multi-step prompting & Fast Downward, VAL & None (Single-pass generation) & Executability, Feasibility, Interpretability \\
Laule et al. (PDDLCoder)~\cite{laule2025pddlcoder} & Direct PDDL text & Agentic feedback loop & PDDL parsers, Gym simulators & Raw error logs (Prompt bloat) & Plan applicability \\
Smirnov et al.~\cite{smirnov2024} & Direct PDDL text & Heuristic checking & Custom consistency checker & Heuristic flags + Human review & Syntactic consistency \\
Bavandpour \& Bercher~\cite{bavandpour2026llmonly} & Direct PDDL text & Test-trace re-prompting & Positive/negative test plans & Minimal hitting sets & Token F1, Test pass rate (TR) \\
Patil~\cite{patil2024} & Direct PDDL text & Iterative repair prompting & Fast Downward, VAL & Raw unparsed error traces & Repair success, Error rate \\
Shetye~\cite{shetye2025} & Intermediate ASP rules & Two-stage LLM translation & Clingo, Fast Downward, VAL & Global domain re-prompting & Accuracy, Makespan, Plan cost \\
\midrule
\textbf{This Thesis}~\cite{x} & \textbf{Typed AST Blueprint} & \textbf{Deterministic Compiler} & \textbf{Fast Downward \& VAL} & \textbf{4-Layer Diagnostic Triage} & \textbf{Two-Way Success (Soundness \& Completeness)} \\
\bottomrule
\end{tabularx}
\end{table}

As illustrated in \zcref{tab:related-work-comparison}, existing frameworks predominantly operate directly on unstructured \gls{pddl} Lisp text, leaving them vulnerable to syntax collapse and parenthesis errors~\cite{oswald2024,huang2025}.
Approaches that incorporate repair loops frequently dump raw, unparsed engine logs directly back into the language model's prompt, inducing context bloat, regression thrashing, and high iteration counts~\cite{patil2024,laule2025pddlcoder}.
Furthermore, evaluation across prior works has largely relied on relaxed proxy metrics—such as token-level F1 scores, syntactic validity rates, or unilateral plan transfer—failing to rigorously verify two-way semantic correctness against formal ground-truth physics~\cite{bavandpour2026llmonly,oswald2024}.

This thesis addresses these foundational gaps by introducing three core innovations:
\begin{enumerate}
    \item \textbf{Decoupled AST Formulation:} Semantic relational reasoning is separated from concrete syntax generation by prompting the model to author only action preconditions and effects into a strongly-typed \gls{ast} blueprint, while an algorithmic compiler deterministically renders standardized \gls{pddl} 2.1 code with syntax validity guaranteed by construction~\cite{x}.
    \item \textbf{Structured Four-Layer Diagnostic Triage:} Raw oracle failures are algorithmically decomposed across four hierarchical layers (VAL syntax, Fast Downward translator typing, VAL step simulation, and Fast Downward search exhaustion), transforming noisy log dumps into surgical, action-level repair directives~\cite{x}.
    \item \textbf{Rigorous Two-Way Semantic Verification:} Rather than relying on loose heuristic thresholds, domain models are verified under strict two-way semantic criteria, requiring both forward Soundness on ground-truth physics and inverse Completeness on reference benchmark problem suites~\cite{howey2004,helmert2006,x}.
\end{enumerate}
"""

target_file.write_text(content, encoding="utf-8")
print(f"Successfully written {len(content)} characters to {target_file}")
