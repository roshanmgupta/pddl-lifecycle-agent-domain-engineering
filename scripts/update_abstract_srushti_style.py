from pathlib import Path

FRESH_DIR = Path("scientific-thesis-template-fresh").resolve()
main_tex = FRESH_DIR / "main-english.tex"
thesismain_tex = FRESH_DIR / "thesismain.tex"

abstract_en = """% -----------------------------------------------------------------------------
% Abstract (Calibrated to Srushti Shetye Blueprint & Project Description)
% -----------------------------------------------------------------------------
\\section*{Abstract}
Domain model generation is a foundational challenge in automated planning, requiring models that are both syntactically correct and semantically robust for effective plan synthesis and execution~\\cite{ghallab2004,mcdermott1998}.
This master's thesis addresses this challenge by establishing an autonomous, closed-loop lifecycle framework for Planning Domain Definition Language (\\gls{pddl}) domain model formulation and fault repair~\\cite{x}.
Constructing a correct, complete, and efficient PDDL domain model is traditionally time-consuming, error-prone, and requires substantial knowledge-engineering expertise~\\cite{georgievski2023,patil2024}.
Recent advancements in Large Language Models (LLMs) have motivated their application to automated planning knowledge acquisition, with over eighty recent works exploring LLMs for model construction, editing, and planning interfaces~\\cite{chen2021,tantakoun2025}.

However, fully automating the engineering of domain models from natural language remains a persistent challenge~\\cite{x}.
Existing approaches predominantly treat domain modelling as an isolated, single-step generation task rather than an iterative engineering lifecycle~\\cite{georgievski2023}.
Outputs from unguided LLMs often suffer from severe syntax collapse, while generated action schemas frequently contain subtle precondition omissions, unsatisfiable constraints, and logical faults that render planning tasks mathematically unsolvable~\\cite{oswald2024,kambhampati2024,valmeekam2023}.
Additionally, current iterative refinement processes pass raw, unparsed planner logs or compiler traces back to the model without explicit fault localization, failing to isolate why an action fails and frequently requiring manual expert adjustments, which contradicts the aim of autonomous operation~\\cite{bavandpour2026llmonly,patil2024}.

To address these limitations, this thesis proposes an autonomous, feedback-driven lifecycle framework that enables LLMs to formulate and repair PDDL domain models through a fully automated pipeline with no human intervention~\\cite{x}.
The first step decouples relational semantic reasoning from concrete PDDL syntax by prompting the LLM to synthesize only action preconditions and effects into a typed Abstract Syntax Tree (AST) intermediate representation, preserving canonical types, predicates, and action signatures to guarantee direct model comparability~\\cite{x}.
A deterministic algorithmic compiler then translates this AST blueprint into standardized PDDL 2.1 Lisp text, mathematically guaranteeing balanced parentheses and keyword validity by construction~\\cite{x}.
When domain validation fails, the framework resolves faults through a structured four-layer diagnostic triage engine that categorizes compiler syntax errors, translator typing and arity conflicts, plan step simulation failures, and search reachability deadlocks into surgical, action-level repair directives without raw log bloat~\\cite{x}.

Once the domain models are formulated, plans are synthesized using the Fast Downward planner and then validated using VAL to rigorously verify two-way semantic correctness—ensuring both forward Soundness on ground-truth physics and inverse Completeness on reference problem suites~\\cite{howey2004,helmert2006,x}.
The framework is evaluated using OpenAI GPT-4o across six canonical International Planning Competition (IPC) benchmark domains (Blocksworld, Gripper, Logistics, Depot, Rovers, and Satellite) normalized to unit-cost STRIPS, alongside 24 controlled single-action mutation tasks for fault repair~\\cite{x}.
Performance is assessed based on two-way task success rates, convergence iterations, wall-clock latency, and token consumption under non-parametric statistical testing (McNemar's test and Wilcoxon signed-rank test)~\\cite{x}.
The results demonstrate that decoupling AST relational reasoning from concrete syntax eliminates syntax failure, while structured diagnostic triage enables LLMs to reliably repair domain bugs in significantly fewer iterations than unstructured error feedback~\\cite{x}.

\\section*{Kurzfassung}
\\begin{otherlanguage}{ngerman}
Die Erstellung von Domänenmodellen ist eine grundlegende Herausforderung in der automatisierten Planung, die sowohl syntaktisch korrekte als auch semantisch robuste Modelle für eine effektive Plansynthese und -ausführung erfordert.
Diese Masterarbeit begegnet dieser Herausforderung durch die Entwicklung eines autonomen, geschlossenen Lifecycle-Frameworks für die Formulierung und Fehlerreparatur von Domänenmodellen in der Planning Domain Definition Language (PDDL).
Die manuelle Erstellung korrekter und vollständiger PDDL-Modelle ist traditionell zeitaufwendig, fehleranfällig und erfordert erhebliche Expertise im Knowledge Engineering.
Jüngste Fortschritte bei großen Sprachmodellen (LLMs) haben deren Einsatz zur Wissensakquisition in der KI-Planung motiviert, wobei über achtzig Arbeiten den Einsatz von LLMs für Modellgenerierung, -editierung und Benutzerschnittstellen untersuchen.

Dennoch bleibt die vollständige Automatisierung der Domänenmodellierung aus natürlicher Sprache eine anhaltende Herausforderung.
Bestehende Ansätze behandeln die Modellierung überwiegend als isolierte Einzelgenerierung anstelle eines iterativen Software-Engineering-Lebenszyklus.
Ausgaben ungesteuerter LLMs leiden häufig unter Syntaxfehlern, während generierte Aktionsschemata subtile Vorbedingungsfehler oder logische Mängel aufweisen, die Planungsaufgaben mathematisch unlösbar machen.
Zudem übergeben bestehende iterative Systeme unstrukturierte Fehlermeldungen ohne explizite Fehlerlokalisierung an das Modell zurück, was häufig manuelle Korrekturen erfordert und dem Ziel einer vollständigen Autonomie widerspricht.

Um diese Einschränkungen zu überwinden, stellt diese Arbeit ein autonomes, feedbackgesteuertes Lifecycle-Framework vor, das PDDL-Domänenmodelle ohne menschliche Eingriffe formuliert und repariert.
Der erste Schritt entkoppelt das relationale logische Schließen von der PDDL-Syntax, indem das LLM lediglich Vorbedingungen und Effekte in einen typisierten Abstract Syntax Tree (AST) überführt, während kanonische Typen und Prädikatssignaturen beibehalten werden.
Ein deterministischer Compiler überführt diese AST-Zwischendarstellung in PDDL 2.1 Lisp-Code und garantiert syntaktische Validität per Konstruktion.
Im Fehlerfall analysiert ein vierstufiges diagnostisches Triage-System Fehlermeldungen der symbolischen Orakel Fast Downward und VAL, um gezielte, aktionsbezogene Reparaturprompts ohne Kontextüberlauf zu erzeugen.

Nach der Formulierung werden Pläne mit dem Fast Downward-Planer generiert und mit dem VAL-Validator auf zweiseitige semantische Korrektheit (Korrektheit auf der Referenzphysik und Vollständigkeit auf den Referenzaufgaben) geprüft.
Die Evaluation erfolgt mit OpenAI GPT-4o über sechs normierte IPC-Benchmark-Domänen sowie 24 kontrollierte Mutationsaufgaben zur Fehlerreparatur unter nicht-parametrischen statistischen Tests und automatisierter Protokollierung von Laufzeit und Tokenverbrauch.
Die Ergebnisse zeigen, dass die AST-Entkopplung Syntaxfehler eliminiert und die strukturierte Fehlerdiagnose eine zuverlässige Reparatur in signifikant weniger Iterationen als unstrukturiertes Feedback ermöglicht.
\\end{otherlanguage}"""

for target_file in [main_tex, thesismain_tex]:
    text = target_file.read_text(encoding="utf-8")
    text_norm = text.replace("\r\n", "\n")
    
    start_pos = text_norm.find("\\section*{Abstract}")
    end_pos = text_norm.find("\\microtypesetup{protrusion=false}")
    
    if start_pos != -1 and end_pos != -1:
        updated = text_norm[:start_pos] + abstract_en + "\n\n\n" + text_norm[end_pos:]
        target_file.write_text(updated, encoding="utf-8")
        print(f"Successfully updated Abstract in {target_file.name}")
    else:
        print(f"Could not locate abstract boundaries in {target_file.name}")

print("Abstract reframing complete.")
