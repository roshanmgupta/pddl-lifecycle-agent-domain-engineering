import os
from pathlib import Path

FRESH_DIR = Path("scientific-thesis-template-fresh").resolve()
main_tex_path = FRESH_DIR / "main-english.tex"
thesismain_path = FRESH_DIR / "thesismain.tex"
intro_tex_path = FRESH_DIR / "chapters-en" / "10 - introduction.tex"

# 1. Update main-english.tex cover settings
main_text = main_tex_path.read_text(encoding="utf-8")

old_cover = """\\usepackage[
  title={Is Oil the future?},
  author={Kim Sonne},
  type=bachelor,
  institute=iaas, % or other institute names - or just a plain string using {Demo\\\\Demo...}
  course={Medieninformatik},
  examiner={Prof.\\ Dr.\\ Eike Kraft},
  supervisor={Luca Wind,\\ M.Sc.,\\\\Janne Strom,\\ M.Sc.},
  startdate={July 5, 2018},
  enddate={January 5, 2019},
  language=english
]{scientific-thesis-cover}"""

new_cover = """\\usepackage[
  title={Towards an Autonomous Lifecycle Agent for PDDL Domain Modelling},
  author={Roshan Gupta},
  type=master,
  institute=iaas,
  course={Information Technology},
  examiner={Prof.\\ Dr.\\ Ilche Georgievski},
  supervisor={PD Dr.\\ Ilche Georgievski},
  startdate={June 15, 2026},
  enddate={November 15, 2026},
  language=english
]{scientific-thesis-cover}"""

main_text_norm = main_text.replace("\r\n", "\n")
old_cover_norm = old_cover.replace("\r\n", "\n")

if old_cover_norm in main_text_norm:
    main_text_norm = main_text_norm.replace(old_cover_norm, new_cover)
    print("Updated cover settings in main-english.tex.")
else:
    print("Warning: cover block mismatch, checking title...")
    import re
    main_text_norm = re.sub(r"title=\{[^}]+\}", "title={Towards an Autonomous Lifecycle Agent for PDDL Domain Modelling}", main_text_norm, count=1)
    main_text_norm = re.sub(r"author=\{[^}]+\}", "author={Roshan Gupta}", main_text_norm, count=1)
    main_text_norm = re.sub(r"type=\w+", "type=master", main_text_norm, count=1)
    main_text_norm = re.sub(r"course=\{[^}]+\}", "course={Information Technology}", main_text_norm, count=1)
    main_text_norm = re.sub(r"examiner=\{[^}]+\}", "examiner={Prof.\\\\ Dr.\\\\ Ilche Georgievski}", main_text_norm, count=1)
    main_text_norm = re.sub(r"supervisor=\{[^}]+\}", "supervisor={PD Dr.\\\\ Ilche Georgievski}", main_text_norm, count=1)
    main_text_norm = re.sub(r"startdate=\{[^}]+\}", "startdate={June 15, 2026}", main_text_norm, count=1)
    main_text_norm = re.sub(r"enddate=\{[^}]+\}", "enddate={November 15, 2026}", main_text_norm, count=1)

# 2. Update Abstract and Kurzfassung
new_abstract_body = """Automated domain modeling in the Planning Domain Definition Language (PDDL) is a fundamental knowledge-engineering bottleneck in AI planning systems. While Large Language Models (LLMs) offer promising capabilities for translating informal requirements into formal logic, direct text-to-PDDL generation suffers from severe syntax collapse and lack of closed-loop verification. This master's thesis presents an autonomous framework for PDDL domain model formulation and closed-loop fault repair. The architecture decouples relational semantic reasoning from low-level PDDL syntax through a typed Abstract Syntax Tree (AST) intermediate representation and a deterministic compiler, guaranteeing syntax validity by construction. For closed-loop refinement, a four-layer diagnostic triage engine categorizes symbolic oracle feedback from the Fast Downward planner and the VAL plan validator (syntax errors, type/arity mismatches, plan step simulation failures, and reachability search exhaustion) to direct localized repairs. The framework is evaluated across six canonical International Planning Competition (IPC) domains (Blocksworld, Gripper, Logistics, Depot, Rovers, and Satellite) normalized to unit-cost STRIPS, assessing formulation via two-way semantic plan validation (Soundness and Completeness) and fault repair across 24 systematic mutation tasks using non-parametric statistical testing and automated token and latency logging."""

new_kurzfassung_body = """Die Modellierung von Planungsdomänen in der Planning Domain Definition Language (PDDL) stellt einen zentralen Flaschenhals im Knowledge Engineering für KI-Planungssysteme dar. Obwohl Large Language Models (LLMs) vielversprechende Fähigkeiten bei der Übersetzung informeller Beschreibungen in formale Logik aufweisen, führt die direkte Generierung von PDDL-Code zu häufigen Syntaxfehlern und unzureichender semantischer Verifikation. Diese Masterarbeit präsentiert ein autonomes Framework für die Formulierung und geschlossene Fehlerreparatur von PDDL-Domänenmodellen. Durch eine typisierte Abstract Syntax Tree (AST)-Zwischendarstellung und einen deterministischen Compiler wird das relationale logische Schließen von der PDDL-Lisp-Syntax entkoppelt, wodurch syntaktische Korrektheit per Konstruktion garantiert wird. Ein vierstufiges diagnostisches Triage-System analysiert Fehlerrückmeldungen der symbolischen Orakel Fast Downward und VAL (Syntaxfehler, Typ- und Aritätskonflikte, Plansimulationsfehler und Unerreichbarkeit im Zustandsraum), um gezielte Reparaturen zu steuern. Die empirische Evaluation erfolgt anhand von sechs kanonischen Domänen der International Planning Competition (IPC) und 24 kontrollierten Mutationsaufgaben unter Verwendung zweiseitiger semantischer Planvalidierung (Korrektheit und Vollständigkeit) sowie automatisierter Protokollierung von Rechenzeit und Tokenverbrauch."""

# Replace abstract text
abstract_marker = "% -----------------------------------------------------------------------------\n% Abstract\n% -----------------------------------------------------------------------------"
if abstract_marker in main_text_norm:
    # Find section*{Kurzfassung}
    k_idx = main_text_norm.find("\\section*{Kurzfassung}")
    if k_idx != -1:
        prefix = main_text_norm[:main_text_norm.find(abstract_marker) + len(abstract_marker)]
        kurz_end = main_text_norm.find("\\end{otherlanguage}", k_idx) + len("\\end{otherlanguage}")
        suffix = main_text_norm[kurz_end:]
        
        abstract_block = f"""\n\n\\section*{{Abstract}}\n{new_abstract_body}\n\n\\section*{{Kurzfassung}}\n\\begin{{otherlanguage}}{{ngerman}}\n  {new_kurzfassung_body}\n\\end{{otherlanguage}}"""
        main_text_norm = prefix + abstract_block + suffix
        print("Updated Abstract and Kurzfassung in main-english.tex.")

# Write updated main-english.tex
main_tex_path.write_text(main_text_norm, encoding="utf-8")

# Write synchronized thesismain.tex
thesismain_path.write_text(main_text_norm, encoding="utf-8")
print(f"Created synchronized {thesismain_path.name}")

# 3. Update chapters-en/10 - introduction.tex
intro_content = """% !TeX root = ../thesismain.tex
%%% ===============================================================================
\\chapter{Introduction}\\label{sec:introduction}
%%% ===============================================================================

Automated planning, also known as Artificial Intelligence (AI) planning, is a foundational discipline of computer science focused on the algorithmic generation of action sequences that transition an agent or system from an initial state to a desired goal state in complex, dynamic environments~\\cite{ghallab2004}. Across industrial and scientific domains—including autonomous robotics, space exploration, supply-chain logistics, and cyber operations—automated planning enables intelligent agents to anticipate future states, manage operational constraints, and achieve designated objectives~\\cite{georgievski2023,kambhampati2024}.

At the center of domain-independent planning systems is the formal domain model~\\cite{ghallab2004}. Standardized in the Planning Domain Definition Language (\\gls{pddl})~\\cite{mcdermott1998}, the domain model formalizes the environment's invariant physics: the hierarchy of object types, the relational predicates that define state facts, and the parameterized action schemas that specify state transitions via preconditions and effects~\\cite{mcdermott1998,howey2004}. The validity, correctness, and solvability of any synthesized plan depend directly on the semantic accuracy of this underlying model~\\cite{georgievski2023}. An automated planner is fundamentally constrained by the rules encoded in its domain description~\\cite{ghallab2004}.

Despite significant progress in classical planning algorithms—such as SAS+ translation and heuristic state-space search in Fast Downward~\\cite{helmert2006}—authoring, debugging, and maintaining correct PDDL domain models remains a major bottleneck in AI planning~\\cite{georgievski2023,patil2024}. Writing PDDL models requires defining action schemas while capturing intricate causal dependencies, type hierarchies, and state-transition invariants~\\cite{patil2024,tantakoun2025}. In practice, manual domain authoring is labor-intensive, error-prone, and difficult to maintain in dynamic environments that require frequent updates~\\cite{georgievski2023,shetye2025}.

Small errors in domain authoring—such as missing preconditions, undeclared variable types, or missing delete effects—can make domain models unusable, leading to planning failures or logically flawed execution traces~\\cite{patil2024,smirnov2024}. Automating the generation and repair of domain models from natural-language descriptions would make AI planning accessible to non-experts, accelerate prototyping, and reduce human engineering overhead~\\cite{patil2024,shetye2025}.

The emergence of frontier Large Language Models (\\gls{llm}s) offers a promising avenue for automating domain acquisition and formalization~\\cite{oswald2024,guan2023,huang2025}. Possessing broad world knowledge from web-scale pre-training, autoregressive language models can interpret natural-language requirements and translate informal user intent into structured representations~\\cite{guan2023,huang2025}.

However, deploying unguided language models for formal PDDL modeling introduces critical challenges~\\cite{kambhampati2024,valmeekam2023}. Classical PDDL operates under First-Order Logic (FOL) and the Closed World Assumption, requiring strict syntactic balance, sound type declarations, and exact causal semantics~\\cite{mcdermott1998,howey2004}. Unlike natural language generation, where minor token variations can be understood by readers, classical planning formalisms have zero tolerance for syntax or typing errors~\\cite{patil2024,bavandpour2026llmonly}:
\\begin{itemize}
    \\item A single missing parenthesis or misplaced keyword prefix invalidates the entire domain file during parser validation~\\cite{howey2004,patil2024}.
    \\item A single undeclared variable type or arity mismatch causes the planner's grounding preprocessor to abort execution immediately~\\cite{helmert2006,patil2024}.
    \\item Subtle logical omissions, such as omitting a negative delete effect or over-constraining a precondition, produce models that are either mathematically unsolvable or cause invalid physical execution~\\cite{kambhampati2024,valmeekam2023,huang2025}.
\\end{itemize}

Empirical evaluations by Kambhampati et al.~\\cite{kambhampati2024} and Valmeekam et al.~\\cite{valmeekam2023} have demonstrated that LLMs lack internal world models capable of autonomous state-transition tracking, with zero-shot planning solvability dropping below $3\\%$ under symbol obfuscation. Furthermore, recent evaluations by Bavandpour and Bercher~\\cite{bavandpour2026llmonly} showed that LLMs tasked with domain repair fail to satisfy test constraints reliably, achieving pass rates as low as $6\\%$ on complex combinatorial domains.

These findings show that LLMs cannot serve as unguided, stand-alone planning modelers~\\cite{kambhampati2024}. Instead, they motivate an LLM-modulo architecture, where language models are combined with deterministic compilers and symbolic planning oracles in a closed feedback loop~\\cite{kambhampati2024,shetye2025}.

% ---------------------------------------------------------------------------------
\\section{Overview of the State of the Art}\\label{sec:introduction:state-of-art}
% ---------------------------------------------------------------------------------

Existing methodologies that use LLMs for PDDL domain modeling have explored three main directions:

\\begin{enumerate}
    \\item \\textbf{Direct Prompt-Based Generation (Open-Loop Translation):}
    Early studies prompted LLMs to translate natural-language domain descriptions directly into PDDL code in a single prompt~\\cite{oswald2024,silver2022}. While straightforward, open-loop generation requires the model to handle semantic extraction and low-level Lisp formatting simultaneously~\\cite{oswald2024}. As a result, direct text generation suffers from high syntax failure rates ($>50\\%$) and low plan solvability ($<15\\%$) across standard International Planning Competition (\\gls{ipc}) domains~\\cite{oswald2024}.

    \\item \\textbf{In-Context Retrieval and Structured Prompting:}
    To improve output quality, subsequent approaches integrated few-shot demonstrations, Chain-of-Thought (CoT) prompting, and semantic retrieval~\\cite{guan2023,huang2025}. Guan et al.~\\cite{guan2023} provided in-context examples, while Huang et al.~\\cite{huang2025} developed SPAR, using dense semantic retrieval and action-by-action CoT generation. While SPAR achieved high internal problem-solving rates ($95.19\\%$), it revealed a divergence between internal solvability and physical feasibility, showing that LLMs tend to generate overly permissive actions that violate ground-truth dynamics~\\cite{huang2025}.

    \\item \\textbf{Iterative Repair and Intermediate Scaffolding:}
    To resolve errors autonomously, recent systems have explored closed-loop feedback. Smirnov et al.~\\cite{smirnov2024} implemented consistency checks for generated models, while Bavandpour and Bercher~\\cite{bavandpour2026llmonly} evaluated feeding raw planner and validator error traces back into the prompt (\\texttt{WITHTRACE}). Concurrently, researchers have investigated intermediate declarative formalisms, such as Answer Set Programming (\\gls{asp})~\\cite{agarwal2024,shetye2025}, using ASP solvers (Clingo) to verify logical consistency prior to PDDL translation. However, translating across disparate formalisms introduces representation mismatch~\\cite{shetye2025}, and feeding raw error logs frequently causes prompt bloat and side-effect regressions~\\cite{bavandpour2026llmonly}.
\\end{enumerate}

% ---------------------------------------------------------------------------------
\\section{Gaps in the State of the Art}\\label{sec:introduction:gaps}
% ---------------------------------------------------------------------------------

Despite recent advancements, existing literature exhibits three primary gaps:

\\subsection{Syntax Collapse in Unconstrained Generation (The Coupling Problem)}
Current approaches predominantly prompt the language model to emit raw PDDL Lisp S-expressions directly~\\cite{oswald2024,silver2022}. This couples relational semantic reasoning (identifying entities, relations, and action dynamics) with low-level lexical formatting (balancing parentheses, prefix colons, and hyphens)~\\cite{oswald2024}. When the LLM must generate formatting syntax and logical relations simultaneously, syntax errors occur frequently ($>50\\%$ syntax failure in unconstrained generation~\\cite{oswald2024}). There is an absence of architectures that decouple relational reasoning from concrete PDDL syntax generation through an intermediate typed Abstract Syntax Tree (\\gls{ast}) blueprint and deterministic compilation~\\cite{x}.

\\subsection{Unstructured Error Feedback and Absence of Layered Diagnosis}
When a generated domain fails validator or planner execution, existing iterative repair approaches pass raw, unparsed compiler outputs or execution traces directly back into the LLM context~\\cite{bavandpour2026llmonly}. Lacking diagnostic triage, the model cannot distinguish whether the failure is caused by lexical syntax violations, variable typing mismatches, unsatisfied preconditions, or state-space reachability deadlocks~\\cite{bavandpour2026llmonly,patil2024}. This unstructured feedback leads to prompt context bloat, repetitive repair loops, and unintended mutations that break previously working action schemas~\\cite{bavandpour2026llmonly}.

\\subsection{Permissive and Circular Evaluation Metrics}
Many existing benchmarks evaluate LLM-generated models solely on syntactic parseability or single-instance plan solvability on tasks generated by the model itself~\\cite{huang2025,rosa2026grounded}. A permissive domain model (for example, an action that asserts a goal fact without requiring necessary preconditions) can be easily solved by a planner, but it represents an unsound model of the domain~\\cite{huang2025,rosa2026grounded}. Current benchmarks lack non-circular, two-way semantic validation gates that verify both forward soundness (plans generated from the synthesized model execute successfully on ground-truth physics) and completeness (ground-truth plans execute successfully on the synthesized model)~\\cite{x}.

% ---------------------------------------------------------------------------------
\\section{Research Questions and Hypotheses}\\label{sec:introduction:research-question}
% ---------------------------------------------------------------------------------

To address these limitations, this thesis investigates the following primary research question:

\\begin{quote}
\\textbf{Main Research Question (MRQ):} \\textit{How can an autonomous agentic framework integrate Large Language Models (LLMs) with deterministic compilation and symbolic planning oracles to enable reliable PDDL domain model formulation and closed-loop fault repair without human intervention?}~\\cite{x}
\\end{quote}

To address the MRQ systematically, we formulate three operational sub-research questions:

\\begin{description}[leftmargin=1.5em]
    \\item[\\textbf{RQ1 (AST-Centric Formulation \\& Syntax Decoupling):}] What is the effect of decoupling relational semantic reasoning (using an Abstract Syntax Tree blueprint) from concrete PDDL syntax generation via deterministic compilation on syntactic correctness and two-way semantic plan validity compared to direct text generation?~\\cite{x}
    \\item[\\textbf{RQ2 (Diagnostic Triage \\& Repair Convergence):}] To what extent does structured, layered diagnostic triage reduce the repair iterations and improve repair success required to resolve domain defects compared to unstructured error feedback?~\\cite{x}
    \\item[\\textbf{RQ3 (Descriptive Computational Cost and Telemetry):}] What are the computational costs (token consumption, inference latency, and convergence iterations) incurred across experimental conditions under deterministic decoding ($T = 0.0$)?~\\cite{x}
\\end{description}

We formulate two scientific hypotheses to be statistically tested:

\\begin{enumerate}[label=\\textbf{(H\\arabic*)}, leftmargin=2.2em]
    \\item When provided with natural-language domain specifications alongside ground-truth types, predicates, and action signatures, generating precondition and effect schemas via an intermediate AST blueprint and deterministic compilation achieves significantly higher two-way semantic task success (Soundness and Completeness across all reference problems) than direct zero-shot text generation (\\texttt{ZERO\\_SHOT}) and AST generation without deterministic compilation (\\texttt{ABLATION\\_NO\\_AST})~\\cite{x}.
    \\item Structured, layered diagnostic triage achieves significantly higher repair success and requires significantly fewer repair iterations to resolve systematic mutation defects than re-prompting with raw, unstructured error traces (\\texttt{ABLATION\\_NO\\_TRIAGE})~\\cite{x}.
\\end{enumerate}

Research Question RQ3 is evaluated descriptively by automatically logging token usage, wall-clock latency, and repair iterations across all experimental conditions, providing a transparent operational accounting of computational requirements~\\cite{x}.

% ---------------------------------------------------------------------------------
\\section{Method or Approach: The Autonomous Lifecycle Agent}\\label{sec:introduction:method}
% ---------------------------------------------------------------------------------

To address these research questions, this thesis introduces a domain-agnostic \\textbf{Autonomous PDDL Lifecycle Agent}~\\cite{x}. In accordance with classical PDDL 2.1 formal semantics, the framework operates without hardcoded domain heuristics, domain-specific type names, or manual overrides~\\cite{mcdermott1998}.

The architecture comprises three core operational phases and a diagnostic feedback loop~\\cite{x}:
\\begin{enumerate}
    \\item \\textbf{Phase 1: Knowledge Ingestion \\& AST Blueprint Extraction:} Receives natural-language domain descriptions alongside ground-truth types, predicates, and action signatures, instructing the LLM to generate only preconditions and effects within a strongly-typed Pydantic JSON Abstract Syntax Tree (\\texttt{DomainBlueprint})~\\cite{x}.
    \\item \\textbf{Phase 2: Formulation \\& Deterministic Compilation:} Validates the AST schema and compiles it into valid PDDL 2.1 Lisp text via an algorithmic compiler, mathematically guaranteeing balanced parentheses and keyword syntax by construction~\\cite{x}.
    \\item \\textbf{Phase 3: Symbolic Verification \\& Layered Diagnostic Triage:} Evaluates compiled domain files on reference problems using symbolic oracles (VAL~\\cite{howey2004} and Fast Downward~\\cite{helmert2006}). When execution fails, errors are categorized across a \\textbf{Four-Layer Diagnostic Triage Engine}~\\cite{x}:
    \\begin{itemize}
        \\item \\textit{Layer 1 (VAL Syntax Check):} Verifies syntactic well-formedness and structural PDDL compliance~\\cite{howey2004}.
        \\item \\textit{Layer 2 (Fast Downward Translator Type Check):} Verifies predicate signatures, variable typing, and arity consistency~\\cite{helmert2006}.
        \\item \\textit{Layer 3 (VAL Plan Simulation Step Verification):} Simulates plan execution to identify failing actions, unsatisfied preconditions, or missing effects~\\cite{howey2004}.
        \\item \\textit{Layer 4 (Fast Downward Search Exhaustion):} Detects state reachability deadlocks when the planner terminates without finding a plan~\\cite{helmert2006}.
    \\end{itemize}
    The triage engine constructs localized repair prompts that instruct the LLM to patch only the isolated defective action schema, preventing prompt bloat and unintended regression mutations~\\cite{x}.
\\end{enumerate}

The framework evaluates generated domains against ground-truth reference models using a \\textbf{Two-Way Semantic Verification Protocol}~\\cite{x}:
\\begin{enumerate}
    \\item \\textbf{Soundness (Plan Transfer Solvability):} Plans found by Fast Downward using the generated domain $\\mathcal{D}_{\\text{gen}}$ on ground-truth problems $P_{\\text{gt}}$ must be valid when executed against the ground-truth domain $\\mathcal{D}_{\\text{gt}}$ via VAL~\\cite{howey2004}:
    \\begin{equation}
        \\text{Soundness}(\\mathcal{D}_{\\text{gen}}, P_{\\text{gt}}) \\iff \\text{VAL}(\\mathcal{D}_{\\text{gt}}, P_{\\text{gt}}, \\text{FD}(\\mathcal{D}_{\\text{gen}}, P_{\\text{gt}})) = \\text{Valid}
    \\end{equation}
    \\item \\textbf{Completeness (Reference Solvability Preservation):} Plans found by Fast Downward using the ground-truth domain $\\mathcal{D}_{\\text{gt}}$ on ground-truth problems $P_{\\text{gt}}$ must remain valid when executed against the generated domain $\\mathcal{D}_{\\text{gen}}$ via VAL~\\cite{howey2004}:
    \\begin{equation}
        \\text{Completeness}(\\mathcal{D}_{\\text{gen}}, P_{\\text{gt}}) \\iff \\text{VAL}(\\mathcal{D}_{\\text{gen}}, P_{\\text{gt}}, \\text{FD}(\\mathcal{D}_{\\text{gt}}, P_{\\text{gt}})) = \\text{Valid}
    \\end{equation}
\\end{enumerate}
A formulation task succeeds if and only if both Soundness and Completeness hold across all reference problems associated with the domain~\\cite{x}.

% ---------------------------------------------------------------------------------
\\section{Summary of Contributions}\\label{sec:introduction:contributions}
% ---------------------------------------------------------------------------------

The primary contributions of this master's thesis are as follows:

\\begin{itemize}
    \\item \\textbf{Decoupled AST Formulation Engine:} The design and implementation of the intermediate \\texttt{DomainBlueprint} data contract and a deterministic programmatic compiler that guarantees PDDL syntactic validity by construction, eliminating token-level syntax errors~\\cite{x}.
    \\item \\textbf{Four-Layer Diagnostic Triage Engine:} A structured fault diagnosis framework that maps raw symbolic oracle outputs into targeted, action-level repair prompts, eliminating unstructured error dumps~\\cite{x}.
    \\item \\textbf{Two-Way Semantic Evaluation Protocol:} An empirical verification methodology assessing both forward Soundness and inverse Completeness against ground-truth reference models and problems, addressing circular self-solving evaluations~\\cite{x}.
    \\item \\textbf{Controlled Empirical Evaluation on Classical IPC Benchmarks:} An experimental evaluation across six canonical International Planning Competition domains (Blocksworld, Gripper, Logistics, Depot, Rovers, Satellite)—normalized by removing action costs—and 24 controlled mutation tasks. The evaluation tests formulation (H1) and repair (H2) using non-parametric statistics (McNemar's test and Wilcoxon signed-rank test) and automatically logs token consumption and wall-clock latency across all conditions~\\cite{x}.
\\end{itemize}

% ---------------------------------------------------------------------------------
\\section{Structure of the Thesis}\\label{sec:introduction:structure}
% ---------------------------------------------------------------------------------

The remainder of this thesis is structured in accordance with the IAAS guidelines:

\\begin{itemize}
    \\item \\textbf{Chapter~2 (Theoretical Background):} Formalizes classical state-transition systems, PDDL 2.1 STRIPS semantics, the operational mechanics of Fast Downward and VAL, the diagnostic triage hierarchy, and deterministic greedy LLM decoding ($T = 0.0$).
    \\item \\textbf{Chapter~3 (Related Work):} Systematically surveys foundational literature across LLM planning capabilities, open-loop code generation, intermediate representations, and automated repair, providing an analytical comparison matrix.
    \\item \\textbf{Chapter~4 (System Architecture):} Details the lifecycle agent architecture, the intermediate Pydantic AST schema, the deterministic compiler, the four-layer diagnostic triage engine, and the two-way semantic verification gate.
    \\item \\textbf{Chapter~5 (Implementation Details):} Documents the Python 3.12 implementation, Pydantic V2 data contracts, C++ symbolic oracle subprocess wrappers, LangGraph state graph orchestration, and automated token and latency telemetry.
    \\item \\textbf{Chapter~6 (Experimental Evaluation):} Outlines the experimental design across the six normalized IPC domains, specifies the evaluation metrics and non-parametric statistical testing protocols, and presents empirical results addressing RQ1--RQ3 and hypotheses H1--H2.
    \\item \\textbf{Chapter~7 (Conclusion and Future Work):} Synthesizes the core findings, discusses architectural limitations, and outlines future research directions, including continuous domain evolution and multi-agent collaborative modeling.
\\end{itemize}
"""

intro_tex_path.write_text(intro_content, encoding="utf-8")
print(f"Updated {intro_tex_path.name}")
