# Agentic AI PDDL Lifecycle System - Core Architectural Principles

## 1. Domain-Agnostic Agent Mandate (Zero Hardcoding / Zero Overfitting)
- **General-Purpose Goal**: This system is designed as an autonomous, general-purpose agent for PDDL domain lifecycle engineering (Elicitation -> Compilation -> Validation -> Layered Fault Localization -> Repair -> Evolution -> Maintenance).
- **Universal Applicability**: Every component, rule, prompt, heuristic, and validator must be universally applicable to **ANY valid PDDL (STRIPS + Typing) domain**.
- **Strictly Prohibited**:
  - NEVER write rules, heuristics, or prompt patches tailored to a single specific domain (e.g., Blocksworld, Gripper, Barman, Satellite, Rovers, Depot, etc.).
  - NEVER hardcode domain-specific type names, action names, or predicate names (e.g., `shot`, `shaker`, `cocktail`, `spanner`, `rover`, `rock-sample`, `gripper`) as specialized case-handling logic in prompts or code.
  - NEVER alter the agent's logic just to force one specific test case or benchmark instance to pass if that logic does not universally hold for all PDDL domains.

## 2. Universal Formal PDDL Semantics Only
- All rules codified in `config/pddl_standards.py`, fault localization prompts, repair prompts, and compiler modules must strictly derive from:
  1. Classical PDDL 2.1 formal semantics (Fox & Long 2003; McDermott 1998; Haslum et al. 2019).
  2. First-Order Logic (FOL) well-formedness (variable scoping, quantifier semantics, relation invariance).
  3. Formal Planning AST invariants (acyclic type hierarchy under `object`, unique predicate symbols without signature overloading, well-typed grounding).
- **Abstract Illustrative Examples Only**: If an example is needed in prompt instructions to clarify an abstract rule, it must use domain-independent, generic archetypes (e.g., `item`, `container`, `location`, `vehicle`, `agent`) and clearly illustrate a general principle, not a domain-specific workaround.

## 3. Mandatory Pre-Flight Check Before Modifying `config/pddl_standards.py`
- **Mandatory Pre-Flight Check**: Whenever an issue arises on a specific benchmark domain, the developer/agent MUST first consult this file (`AGENTS.md`).
- **Generalizability Test**: Before adding or updating any rule in `config/pddl_standards.py`, answer:
  > *"Is this rule derived from formal PDDL syntax and semantics that apply identically to all possible PDDL domains, or is it a tailored patch for the currently failing domain?"*
  - If it is universal (e.g., "no duplicate predicate symbols in `(:predicates ...)`", "every parameter variable must start with `?`", "parameter types must match declared predicate signatures"), it is permitted.
  - If it relies on domain-specific semantics or assumptions, it is **strictly forbidden**.

## 4. Code Nomenclature, Semantic Accuracy, and Zero Stale Aliases
- **No Stale Aliases**: Never retain or introduce backwards-compatibility alias names (such as `evaluate_bilevel_domain_equivalence = evaluate_action_reconstruction`) across the codebase. Always call and import the canonical, updated name directly.
- **Continuous Logic-to-Code Alignment**: When the algorithmic logic, metric, or architectural component is updated or refactored, you MUST immediately update all function names, variable names, and file names across all calling modules to accurately reflect the true underlying semantics and literature foundation.

* **Empirical Integrity**: If an LLM generates invalid constructs or fails to repair a domain within the allowed iterations, **that failure is scientifically valid and expected**. Do NOT force success through prompt engineering tricks or heuristic fallbacks. Record the result honestly as unverified/failure.
* **Mandatory File Inspection Before Editing**: Always view and inspect existing code files before proposing or applying updates. Never assume file state or contents.
## 5. Execution Environment: Conda `agent_env` Only
* **Target Environment**: The sole active Python environment for this project is Conda `agent_env`.
* **Binary Path**: `C:\Users\Srushti\miniconda3\envs\agent_env\python.exe`
* **Command Rule**: Always execute all Python scripts, tests, dependencies, and Streamlit servers strictly within `agent_env` (never base or global system Python).

* **Never use latex format for math formulas** during feedback or response or explanation.

* **While writing any report please use the ARMS template** as it would help to validate, verify and improve the work.

## 6. Canonical Tri-Criteria Semantic Verification Mandate
All domain synthesis, repair, and evolution benchmarks must rigorously evaluate and report the three literature-grounded non-circular semantic criteria:
1. **Executability (Internal Consistency & Solvability)**: `VAL(D_gen, P_gen, pi_gen) == SUCCESS`. Proves internal solvability and causal consistency.
2. **Feasibility (Forward Soundness)**: `VAL(D_gold, P_gold, pi_gen) == SUCCESS`. Proves physical soundness on ground-truth domain dynamics without magic transitions.
3. **Interpretability (Inverse Completeness / Reference Solvability Preservation)**: `VAL(D_gen, P_gold, pi_gold) == SUCCESS` (and preservation of solvability on reference suite Pi_ref). Proves expressive completeness without over-constrained preconditions.

**Strict End-to-End Success Gate (`e2e_success`)**:
A synthesized, repaired, or evolved domain is marked as `e2e_success` ONLY if it passes syntax validity, planner solvability, AND all three semantic criteria (`executability and feasibility and interpretability`). No loose heuristic thresholds (such as F1 alone) may override plan validation failures.

# Important
* **Our central goal is to evaluate our generated domain, problem, and plan against standard reference models for semantic soundness, task completeness, and logical consistency using the tri-criteria framework.** We do not use hardcoded domain-specific logic to force plan generation or validation success. Empirical failure under formal oracles is scientifically valid and must be honestly recorded. 

## 7. Mandatory LaTeX Authoring & Compilation Invariants
When writing, editing, or maintaining any LaTeX document (`.tex`) in the thesis template (`scientific-thesis-template-fresh/`):
1. **Underscore Escaping Invariant**: In text mode, section titles, captions, and `\texttt{...}` blocks, ALL underscores MUST be escaped as `\_` (e.g., `\texttt{compile\_pddl\_programmatically}`). Raw underscores (`_`) are strictly reserved for LaTeX mathematical subscripts (`$x_i$`).
2. **Canonical Cross-Referencing (`zref-clever`)**: The template strictly utilizes `zref-clever`. ALWAYS use `\Zcref{...}` and `\zcref{...}`. NEVER use `\Cref{...}` or `\cref{...}` (which require `cleveref` and trigger undefined control sequences).
3. **Table Formatting Invariant**: Utilize standard LaTeX `tabular` or full-width `\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}...}` paired with `booktabs` (`\toprule`, `\midrule`, `\bottomrule`). NEVER use `tabularx` unless explicitly loaded in the document preamble.
4. **Font-Safe Table Tokens**: NEVER use non-standard Unicode glyphs (e.g., `✓` U+2713 or `✗`) that lack glyph definitions in OpenType serif text fonts like `TeX Gyre Termes`. Always use explicit textual tokens (`Yes`, `No`, `Partial`) or standard math symbols.
5. **Pure LaTeX Syntax (Zero Markdown Leakage)**: NEVER inject Markdown syntax (such as `**bold**`, `*italic*`, `# Heading`, or raw code fences) into `.tex` files. Always format strictly with canonical LaTeX macros (`\textbf{...}`, `\emph{...}`, `\section{...}`).
6. **Glossary & Abbreviation Invariant**: Every `\gls{...}` and `\glspl{...}` symbol invoked in any `.tex` file MUST be explicitly defined in `scientific-thesis-template-fresh/abbreviations.tex` using `\newabbreviation{key}{SHORT}{Long Name}`. Referencing an undeclared key causes `glossaries-extra` to abort the compiler with exit code 1.
7. **Label & Cross-Reference Invariant**: All labels (`\label{...}`) must be globally unique across all chapters. Never duplicate table or section labels. All cross-references (`\zcref{...}`) must resolve to an existing declared label.
8. **Pre-Flight Post-Edit Invariant Check**: After updating any `.tex` file, run the automated script check (`python scientific-thesis-template-fresh/scripts/validate_latex.py`) to verify: (a) zero unescaped underscores outside math mode, (b) zero `\cref`/`\Cref`, (c) all `\cite{...}` keys exist in `bibliography.bib`, (d) all `\gls{...}` keys exist in `abbreviations.tex`, (e) zero duplicate labels, and (f) zero unresolved cross-references.
9. **BibTeX File Immutability Invariant**: The bibliography file `scientific-thesis-template-fresh/bibliography.bib` is strictly read-only and MUST NEVER be edited under any circumstances. When citation discrepancies arise, resolve them strictly by updating the citation calls in chapter `.tex` files to reference the canonical keys already present in `bibliography.bib`.
10. **Unwanted Package Exclusion & Interactive Hang Prevention Invariant**: Do not load demo, legacy, or filter-heavy packages (`markdown`, `currfile`, `mwe`, `blindtext`, `hologo`, `ltgexample`) that bloat the compiler log or cause `latexmk` loop exits. Always enforce `bookmarkpackage=false` in the `\documentclass[...]` options of `main-english.tex` to prevent KOMA-Script from prompting interactively for missing `bookmark.sty` in headless TeX Live Viewer environments.
11. **Abbreviation Consistency Invariant**: Once an abbreviation is introduced and defined (e.g., using `\gls{...}` or explicit expansion on first mention), all subsequent occurrences across the text MUST strictly utilize the abbreviation rather than re-expanding the full phrase (e.g., use `AI`, `PDDL`, `VAL`, `AST`, `LLM` consistently). Never revert to the full phrase once the term has been established.
12. **Section-to-Subsection Transition Invariant**: Never start a subsection (`\subsection{...}`) immediately following a section header (`\section{...}`). Every section MUST contain at least an introductory bridging paragraph or multiple sentences explaining what the section and its constituent subsections cover before the first subsection begins.
13. **Single-Citation Invariant for Monographic Discussions**: In Related Work reviews, when discussing a single work or author within a paragraph, place the citation once at the end of the discussion rather than citing repeatedly across multiple sentences in that paragraph.
14. **Canonical Universal Nomenclature & Non-Self-Referential Headings**: Always use canonical, literature-grounded universal names (e.g., "The Fast Downward Planner" instead of "The Fast Downward Planning System"). Never inject extraneous meta-phrasing (such as "of this thesis" or "in this thesis") into section, subsection, or chapter headings.
15. **Zero Double Abbreviation Expansion Invariant**: The `glossaries-extra` macro `\gls{key}` (and `\glspl{key}`, `\Gls{key}`, `\Glspl{key}`) automatically expands to `Full Name (SHORT)` on its first occurrence in the document and prints `SHORT` on all subsequent occurrences. NEVER write the full name manually followed by `(\gls{key})` or `(\glspl{key})` (e.g., never write `Abstract Syntax Tree (\gls{ast})` or `Large Language Models (\glspl{llm})`), because this causes LaTeX to print the full name twice (`Abstract Syntax Tree (Abstract Syntax Tree (AST))`). Always write strictly `\gls{key}` or `\glspl{key}` directly. If the full name must appear manually (e.g., in a heading or formal definition), use `(\glsentryshort{key})` to print only the short acronym without triggering double expansion.

## 8. University of Stuttgart Scientific Writing Guidelines & Proofreading Invariants (Dr. Ilche Georgievski & Prof. Dr. Marco Aiello, v1.1)
All chapter drafting, editing, proofreading, and audits MUST strictly adhere to the following 15 department-mandated writing standards:

1. **Thesis Structural Alignment (Slide 4)**:
   - Abstract -> Introduction -> Background Information -> State of the Art (Related Work) -> Design of Solution -> Realisation of Solution -> Validation/Evaluation of Solution -> Conclusions and Outlook.
2. **Abstract Invariant (Slide 5)**:
   - Must reflect all parts of the thesis in shortened form: general area, problem and importance, methods used, key results, what is new, and perspectives/conclusions.
   - Absolutely NO copy-pasting from the Introduction.
   - Zero bibliographic citations (`\cite{...}`) in the abstract.
3. **Introduction Structural Sequence (Slide 6)**:
   - Must strictly follow this sequence: Context of research (need and importance) -> Brief overview of state of the art -> Gaps in state of the art -> Research questions -> Methodology -> Original contributions -> Preview of the remainder of the paper.
4. **"Avoid 'This' or 'In this' Opening" Invariant (Slide 16)**:
   - NEVER open the thesis, a chapter, a section, a subsection, or any paragraph with the words *"This"* or *"In this"* (e.g., avoid *"This thesis proposes..."*, *"In this section, we present..."*, *"This chapter describes..."*). Always lead with the conceptual topic, an action, or a substantive noun phrase.
5. **Continuous Text Flow & Bridging Invariant (Slide 16)**:
   - Text flow must be guaranteed without breaks between paragraphs or sections.
   - Never place a subsection header immediately under a section header without bridging explanatory text.
6. **Sentence Brevity & Conciseness (Slide 14, 16)**:
   - Use formal, simple, and concise writing.
   - Prefer short, direct sentences. Avoid unnecessary filler phrasing, redundant adverbs, and convoluted parenthetical clauses.
7. **Tense Invariant (Slide 16)**:
   - Use the present tense whenever possible to describe facts, systems, methods, and ongoing theoretical truths. Use past tense strictly when reporting specific completed experimental procedures or historical publications.
8. **Voice & Author Perspective (Slide 15)**:
   - Use "we" instead of "I".
   - Use active voice whenever possible.
   - Use passive voice strictly: (a) to emphasize the action rather than the actor, (b) to keep the grammatical subject and focus consistent throughout a passage, (c) to be tactful without naming actors, or (d) when the actor is unknown or unimportant.
9. **No Noun Strings (Slide 18)**:
   - Avoid long compound strings of nouns (e.g., avoid *"state transition model validation framework error log parser"* -> use *"parser for error logs generated by the state-transition model validation framework"*).
10. **Unambiguous Pronoun References (Slide 18)**:
    - Every pronoun (*it*, *this*, *they*, *these*, *which*) must clearly and unambiguously refer to a specific, definite preceding noun. If any ambiguity is possible, repeat the noun explicitly.
11. **Technical Term Consistency & Zero Synonyms (Slide 17)**:
    - Maintain 100% consistent spelling and usage of technical terms, acronyms, and notations across the entire document.
    - NEVER use synonyms for technical terms (e.g., do not alternate between "action schema", "operator", "action template", and "macro" to describe the same concept; pick one canonical term and use it consistently).
    - Correct capitalization of established terms (e.g., "Artificial Intelligence", "Web").
12. **Zero Contractions (Slide 17)**:
    - Never use contractions (*don't*, *can't*, *won't*, *it's*, *doesn't*). Always write the full forms (*do not*, *cannot*, *will not*, *it is*, *does not*).
13. **Acronym Protocol (Slide 19)**:
    - Define an acronym the first time it is used in the body: first the full name, then the acronym in parentheses (e.g., *Planning Domain Definition Language (PDDL)*).
    - NEVER repeat the full definition once defined.
    - Do not overflow the text with unnecessary acronyms; define acronyms only for terms that appear frequently.
14. **Capitalized Cross-Referencing of Ancillary Elements (Slide 16)**:
    - When referencing chapters, sections, figures, tables, or algorithms in prose, always capitalize the reference token (e.g., `Section~2`, `Chapter~3`, `Figure~4.1`, `Table~3.1`, `Algorithm~1`).
15. **Attribution, Lead-Ins, and Non-Numeric Subjects (Slide 23, 24)**:
    - To summarize someone else's research over several sentences, provide an explicit lead-in at the beginning of the paragraph and cite appropriately.
    - Never use raw numeric citation brackets as grammatical subjects in a sentence (e.g., never write *"[12] shows that..."* or *"\cite{oswald} proves..."*; write *"Oswald et al.~\cite{oswald} show that..."* or *"Empirical evaluations demonstrate that...~\cite{oswald}"*).

