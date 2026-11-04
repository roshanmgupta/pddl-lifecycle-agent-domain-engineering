import re
from pathlib import Path

target_file = Path("scientific-thesis-template-fresh/main-english.tex")
text = target_file.read_text(encoding="utf-8")

new_abstract = r"""\section*{Abstract}
Domain model generation is a foundational challenge in automated planning, requiring models that are both syntactically correct and semantically robust for effective plan synthesis and execution~\cite{ghallab2004,mcdermott1998}.
This master's thesis addresses this challenge by establishing an autonomous, closed-loop lifecycle framework for Planning Domain Definition Language (\gls{pddl}) domain model formulation and fault repair~\cite{x}.
Constructing a correct, complete, and efficient PDDL domain model is traditionally time-consuming, error-prone, and requires substantial knowledge-engineering expertise~\cite{georgievski2023,patil2024}.
Recent advancements in Large Language Models (LLMs) have motivated their application to automated planning knowledge acquisition, with a rapidly expanding body of literature exploring LLMs for model construction, editing, and planning interfaces~\cite{chen2021,tantakoun2025}.

However, fully automating the engineering of domain models from natural language remains a persistent challenge~\cite{x}.
Existing approaches predominantly treat domain modelling as an isolated, single-step generation task rather than an iterative engineering lifecycle~\cite{georgievski2023}.
Outputs from unguided LLMs often suffer from severe syntax collapse, while generated action schemas frequently contain subtle precondition omissions, unsatisfiable constraints, and logical faults that render planning tasks mathematically unsolvable~\cite{oswald2024,kambhampati2024,valmeekam2023}.
Additionally, current iterative refinement processes pass raw, unparsed planner logs or compiler traces back to the model without explicit fault localization, failing to isolate why an action fails and frequently requiring manual expert adjustments, which contradicts the aim of autonomous operation~\cite{bavandpour2026llmonly,patil2024}.

To address these limitations, an autonomous, feedback-driven lifecycle framework is proposed to formulate and repair PDDL domain models without human intervention~\cite{x}.
Relational semantic reasoning is decoupled from concrete syntax by prompting the LLM to synthesize only action preconditions and effects into a typed Abstract Syntax Tree (AST) blueprint, preserving canonical types, predicates, and action signatures for direct model comparability~\cite{x}.
A deterministic compiler translates this AST directly into standard PDDL code, guaranteeing syntactic validity and balanced parentheses by construction~\cite{x}.
When domain validation fails, a structured four-layer diagnostic triage engine isolates faults across compiler syntax, translator typing, plan simulation, and search reachability, transforming raw engine failures into targeted action-level repair directives without log bloat~\cite{x}.

Once the domain models are formulated, plans are synthesized using the Fast Downward planner and then validated using VAL to ensure logical soundness and successful goal achievement---rigorously verifying two-way semantic correctness through forward Soundness on ground-truth physics and inverse Completeness on reference problem suites~\cite{howey2004,helmert2006,x}.
The framework is evaluated using OpenAI GPT-4o across six canonical International Planning Competition (IPC) benchmark domains (Blocksworld, Gripper, Logistics, Depot, Rovers, and Satellite) normalized to unit-cost STRIPS, alongside 24 controlled single-action mutation tasks for fault repair~\cite{x}.
Performance is evaluated using Soundness, Completeness, two-way task success, Syntactic Validity Rate (SVR), repair success rate, convergence iterations, wall-clock latency, and token consumption under non-parametric statistical testing (McNemar's test and Wilcoxon signed-rank test)~\cite{x}.
The results demonstrate that decoupling AST relational reasoning from concrete syntax eliminates syntax failure, while structured diagnostic triage enables LLMs to reliably repair domain bugs in significantly fewer iterations than unstructured error feedback~\cite{x}.

\section*{Kurzfassung}
\begin{otherlanguage}{ngerman}
Die Erstellung von Dom{\"a}nenmodellen ist eine grundlegende Herausforderung in der automatisierten Planung, die sowohl syntaktisch korrekte als auch semantisch robuste Modelle f{\"u}r eine effektive Plansynthese und -ausf{\"u}hrung erfordert~\cite{ghallab2004,mcdermott1998}.
Diese Masterarbeit begegnet dieser Herausforderung durch die Entwicklung eines autonomen, geschlossenen Lifecycle-Frameworks f{\"u}r die Formulierung und Fehlerreparatur von Dom{\"a}nenmodellen in der Planning Domain Definition Language (PDDL)~~\cite{x}.
Die manuelle Erstellung korrekter und vollst{\"a}ndiger PDDL-Modelle ist traditionell zeitaufwendig, fehleranf{\"a}llig und erfordert erhebliche Expertise im Knowledge Engineering~\cite{georgievski2023,patil2024}.
J{\"u}ngste Fortschritte bei gro{\ss}en Sprachmodellen (LLMs) haben deren Einsatz zur Wissensakquisition in der KI-Planung motiviert, wobei eine stetig wachsende Zahl wissenschaftlicher Arbeiten den Einsatz von LLMs f{\"u}r Modellgenerierung, -editierung und Benutzerschnittstellen untersucht~\cite{chen2021,tantakoun2025}.

Dennoch bleibt die vollst{\"a}ndige Automatisierung der Dom{\"a}nenmodellierung aus nat{\"u}rlicher Sprache eine anhaltende Herausforderung~\cite{x}.
Bestehende Ans{\"a}tze behandeln die Modellierung {\"u}berwiegend als isolierte Einzelgenerierung anstelle eines iterativen Software-Engineering-Lebenszyklus~\cite{georgievski2023}.
Ausgaben ungesteuerter LLMs leiden h{\"a}ufig unter Syntaxfehlern, w{\"a}hrend generierte Aktionsschemata subtile Vorbedingungsfehler oder logische M{\"a}ngel aufweisen, die Planungsaufgaben mathematisch unl{\"o}sbar machen~\cite{oswald2024,kambhampati2024,valmeekam2023}.
Zudem {\"u}bergeben bestehende iterative Systeme unstrukturierte Fehlermeldungen ohne explizite Fehlerlokalisierung an das Modell zur{\"u}ck, was h{\"a}ufig manuelle Korrekturen erfordert und dem Ziel einer vollst{\"a}ndigen Autonomie widerspricht~\cite{bavandpour2026llmonly,patil2024}.

Um diese Einschr{\"a}nkungen zu {\"u}berwinden, wird ein autonomes, feedbackgesteuertes Lifecycle-Framework vorgeschlagen, das PDDL-Dom{\"a}nenmodelle ohne menschliche Eingriffe formuliert und repariert~\cite{x}.
Die relationale semantische Modellierung wird von der konkreten Syntax entkoppelt, indem das LLM ausschlie{\ss}lich Aktionsvorbedingungen und -effekte in einen getypten Abstract Syntax Tree (AST) {\"u}berf{\"u}hrt, wodurch kanonische Typen, Pr{\"a}dikate und Signaturen f{\"u}r eine direkte Vergleichbarkeit erhalten bleiben~\cite{x}.
Ein deterministischer Compiler transformiert diesen AST direkt in PDDL-Code mit konstruktionsbedingt garantierter syntaktischer Korrektheit~\cite{x}.
Schl{\"a}gt die Validierung fehl, lokalisiert ein vierstufiges diagnostisches Triage-System Fehler {\"u}ber Compiler-Syntax, Translator-Typisierung, Plansimulation und Erreichbarkeitsanalyse und erzeugt zielgerichtete Reparaturanweisungen auf Aktionsebene ohne unstrukturierte Log-Flut~\cite{x}.

Nach der Formulierung werden Pl{\"a}ne mit dem Fast Downward-Planer generiert und mit dem VAL-Validator auf zweiseitige semantische Korrektheit (Korrektheit auf der Referenzphysik und Vollst{\"a}ndigkeit auf den Referenzaufgaben) gepr{\"u}ft~\cite{howey2004,helmert2006,x}.
Die Evaluation erfolgt mit OpenAI GPT-4o {\"u}ber sechs normierte IPC-Benchmark-Dom{\"a}nen sowie 24 kontrollierte Mutationsaufgaben zur Fehlerreparatur~\cite{x}.
Die Bewertung erfolgt anhand von Korrektheit (Soundness), Vollst{\"a}ndigkeit (Completeness), zweiseitigem Aufgabenerfolg, syntaktischer Validit{\"a}tsrate (SVR), Reparaturerfolgsrate, Konvergenziterationen, Laufzeit und Tokenverbrauch unter nicht-parametrischen statistischen Tests (McNemar-Test und Wilcoxon-Vorzeichen-Rang-Test)~\cite{x}.
Die Ergebnisse zeigen, dass die AST-Entkopplung Syntaxfehler eliminiert und die strukturierte Fehlerdiagnose eine zuverl{\"a}ssige Reparatur in signifikant weniger Iterationen als unstrukturiertes Feedback erm{\"o}glicht~\cite{x}.
\end{otherlanguage}"""

old_pattern = r"\\section\*\{Abstract\}.*?\\end\{otherlanguage\}"
new_text, count = re.subn(old_pattern, lambda m: new_abstract, text, flags=re.DOTALL)
print(f"Replacements made in main-english.tex: {count}")
assert count == 1, "Replacement failed"

target_file.write_text(new_text, encoding="utf-8")
print("Successfully written to main-english.tex.")
