import re
from pathlib import Path

FRESH_DIR = Path("scientific-thesis-template-fresh").resolve()
main_tex = FRESH_DIR / "main-english.tex"
thesismain_tex = FRESH_DIR / "thesismain.tex"
intro_tex = FRESH_DIR / "chapters-en" / "10 - introduction.tex"

# 1. Update 10 - introduction.tex
intro_text = intro_tex.read_text(encoding="utf-8")
intro_text = intro_text.replace(
    "To address the MRQ systematically, we formulate three operational sub-research questions:",
    "To address the MRQ systematically, three operational sub-research questions are defined:"
)
intro_text = intro_text.replace(
    "We formulate two scientific hypotheses to be statistically tested:",
    "Two scientific hypotheses are formulated for statistical testing:"
)
intro_tex.write_text(intro_text, encoding="utf-8")
print("Updated 10 - introduction.tex to agentless passive voice.")

# 2. Update Abstract in main-english.tex and thesismain.tex
abstract_en = """% -----------------------------------------------------------------------------
% Abstract (Strict Impersonal / Agentless Passive Voice)
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

To address these limitations, an autonomous, feedback-driven lifecycle framework is proposed to formulate and repair PDDL domain models without human intervention~\\cite{x}.
In the initial phase, an LLM generates action preconditions and effects as a structured Abstract Syntax Tree (AST), while ground-truth types, predicates, and action signatures remain fixed for direct model comparability~\\cite{x}.
A deterministic compiler then converts this AST directly into standard PDDL code, completely eliminating syntax and parenthesis errors~\\cite{x}.
When validation fails, a four-layer diagnostic triage engine analyzes the error—checking syntax, typing, plan execution, and reachability—to provide focused feedback that repairs only the faulty action without dumping raw error logs~\\cite{x}.

Once the domain models are formulated, plans are synthesized using the Fast Downward planner and then validated using VAL to ensure logical soundness and successful goal achievement—rigorously verifying two-way semantic correctness through forward Soundness on ground-truth physics and inverse Completeness on reference problem suites~\\cite{howey2004,helmert2006,x}.
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

Um diese Einschränkungen zu überwinden, wird ein autonomes, feedbackgesteuertes Lifecycle-Framework vorgeschlagen, das PDDL-Domänenmodelle ohne menschliche Eingriffe formuliert und repariert.
Im ersten Schritt generiert ein LLM Vorbedingungen und Effekte als strukturierten Abstract Syntax Tree (AST), während kanonische Typen, Prädikate und Aktionssignaturen für eine direkte Vergleichbarkeit beibehalten werden.
Ein deterministischer Compiler überführt diesen AST anschließend direkt in PDDL-Code und schließt Syntax- und Klammerungsfehler vollständig aus.
Schlägt die Validierung fehl, analysiert ein vierstufiges diagnostisches Triage-System den Fehler – über Syntax, Typisierung, Plansimulation und Erreichbarkeit – und liefert gezieltes Feedback, um ausschließlich die fehlerhafte Aktion ohne unstrukturierte Log-Flut zu reparieren.

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
        print(f"Successfully updated impersonal Abstract in {target_file.name}")
    else:
        print(f"Could not locate abstract boundaries in {target_file.name}")

# Re-check for any remaining pronouns
print("\n--- Verifying Pronoun Removal across Files ---")
for fpath in [main_tex, intro_tex]:
    t = fpath.read_text(encoding="utf-8")
    matches = re.findall(r"\b(we|our|us|my|the author|the authors)\b", t, re.IGNORECASE)
    # Filter false positives like "us" in status or focus, or in bib keys
    filtered = [m for m in matches if m.lower() in ["we", "our", "my", "the author", "the authors"]]
    print(f"{fpath.name}: {len(filtered)} personal references found: {filtered}")
