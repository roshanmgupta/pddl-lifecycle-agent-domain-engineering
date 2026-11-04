import os

old_tex_path = "scientific-thesis-template/thesis-pddl-lifecycle-agent.tex"
new_thesismain_path = "scientific-thesis-template/thesismain.tex"

with open(old_tex_path, "r", encoding="utf-8") as f:
    content = f.read()

old_abstract = """% --- Abstract ---
\\section*{Abstract}
Automated domain modeling in Planning Domain Definition Language (PDDL) is a fundamental bottleneck in AI planning systems. While Large Language Models (LLMs) offer promising capabilities for translating informal requirements into formal logic, direct text-to-PDDL generation suffers from high syntax error rates ($>50\\%$) and lack of closed-loop verification. This thesis presents a Unified Autonomous Lifecycle Agent for PDDL domain modeling that operationalizes the Knowledge Engineering for Planning and Scheduling (KEPS) Software Development Life Cycle. The framework introduces a structured Pydantic JSON Abstract Syntax Tree (AST) intermediate representation that decouples language comprehension from PDDL Lisp syntax rules, achieving a 100\\% Syntax Validity Rate. A multi-tiered closed-loop verification engine integrates symbolic Oracles (VAL plan validator and Fast Downward planner) with a spectrum-based fault localization engine calculating suspiciousness scores $\\sigma(n)$ to direct targeted AST sub-schema repairs, converging in an average of 1.2 iterations. Furthermore, an evolution manager maintains backward compatibility across domain modifications, preserving a 96.8\\% regression pass rate across IPC benchmark domains.

\\section*{Kurzfassung}
\\begin{otherlanguage}{ngerman}
Die meiste Zeit bei der Modellierung von AI-Planungsdomänen in PDDL geht für die manuelle formal-logische Spezifikation verloren. Large Language Models (LLMs) bieten vielverversprechende Möglichkeiten zur Automatisierung, leiden jedoch bei unstrukturierter Textgenerierung unter hohen Syntaxfehlerraten ($>50\\%$) und fehlender symbolischer Verifikation. Diese Masterarbeit präsentiert einen autonomen Lifecycle-Agenten für die PDDL-Modellierung, der den Software Development Life Cycle (SDLC) im Bereich Knowledge Engineering for Planning and Scheduling (KEPS) abbildet. Das Framework nutzt einen Pydantic JSON Abstract Syntax Tree (AST) als Zwischendarstellung, um Sprachverständnis und Syntaxregeln vollständig zu entkoppeln (100\\% Syntaxvalidität). Ein geschlossener Verifikationskreis kombiniert symbolische Orakel (VAL und Fast Downward) mit spektrumbasierter Fehlerlokalisierung $\\sigma(n)$, um gezielte AST-Reparaturen in durchschnittlich 1,2 Iterationen durchzuführen. Zudem garantiert ein Evolution-Manager eine Regressionserfolgsquote von 96,8\\% bei kontinuierlicher Domänenentwicklung.
\\end{otherlanguage}"""

new_abstract = """% --- Abstract ---
\\section*{Abstract}
Automated domain modeling in the Planning Domain Definition Language (PDDL) is a fundamental knowledge-engineering bottleneck in AI planning systems. While Large Language Models (LLMs) offer promising capabilities for translating informal requirements into formal logic, direct text-to-PDDL generation suffers from severe syntax collapse and lack of closed-loop verification. This master's thesis presents an autonomous framework for PDDL domain model formulation and closed-loop fault repair. The architecture decouples relational semantic reasoning from low-level PDDL syntax through a typed Abstract Syntax Tree (AST) intermediate representation and a deterministic compiler, guaranteeing syntax validity by construction. For closed-loop refinement, a four-layer diagnostic triage engine categorizes symbolic oracle feedback from the Fast Downward planner and the VAL plan validator (syntax errors, type/arity mismatches, plan step simulation failures, and reachability search exhaustion) to direct localized repairs. The framework is evaluated across six canonical International Planning Competition (IPC) domains (Blocksworld, Gripper, Logistics, Depot, Rovers, and Satellite) normalized to unit-cost STRIPS, assessing formulation via two-way semantic plan validation (Soundness and Completeness) and fault repair across 24 systematic mutation tasks using non-parametric statistical testing and automated token and latency logging.

\\section*{Kurzfassung}
\\begin{otherlanguage}{ngerman}
Die Modellierung von Planungsdomänen in der Planning Domain Definition Language (PDDL) stellt einen zentralen Flaschenhals im Knowledge Engineering für KI-Planungssysteme dar. Obwohl Large Language Models (LLMs) vielversprechende Fähigkeiten bei der Übersetzung informeller Beschreibungen in formale Logik aufweisen, führt die direkte Generierung von PDDL-Code zu häufigen Syntaxfehlern und unzureichender semantischer Verifikation. Diese Masterarbeit präsentiert ein autonomes Framework für die Formulierung und geschlossene Fehlerreparatur von PDDL-Domänenmodellen. Durch eine typisierte Abstract Syntax Tree (AST)-Zwischendarstellung und einen deterministischen Compiler wird das relationale logische Schließen von der PDDL-Lisp-Syntax entkoppelt, wodurch syntaktische Korrektheit per Konstruktion garantiert wird. Ein vierstufiges diagnostisches Triage-System analysiert Fehlerrückmeldungen der symbolischen Orakel Fast Downward und VAL (Syntaxfehler, Typ- und Aritätskonflikte, Plansimulationsfehler und Unerreichbarkeit im Zustandsraum), um gezielte Reparaturen zu steuern. Die empirische Evaluation erfolgt anhand von sechs kanonischen Domänen der International Planning Competition (IPC) und 24 kontrollierten Mutationsaufgaben unter Verwendung zweiseitiger semantischer Planvalidierung (Korrektheit und Vollständigkeit) sowie automatisierter Protokollierung von Rechenzeit und Tokenverbrauch.
\\end{otherlanguage}"""

# Normalize line breaks for matching
content_normalized = content.replace("\r\n", "\n")
old_abstract_normalized = old_abstract.replace("\r\n", "\n")
new_abstract_normalized = new_abstract.replace("\r\n", "\n")

if old_abstract_normalized in content_normalized:
    updated_content = content_normalized.replace(old_abstract_normalized, new_abstract_normalized)
    print("Found and replaced abstract successfully!")
else:
    print("Warning: exact abstract match not found, checking substring...")
    start_str = "% --- Abstract ---"
    end_str = "\\microtypesetup{protrusion=false}"
    s_idx = content_normalized.find(start_str)
    e_idx = content_normalized.find(end_str)
    if s_idx != -1 and e_idx != -1:
        updated_content = content_normalized[:s_idx] + new_abstract_normalized + "\n\n\n" + content_normalized[e_idx:]
        print("Replaced abstract via section indices!")
    else:
        updated_content = content_normalized

# 1. Update thesis-pddl-lifecycle-agent.tex
with open(old_tex_path, "w", encoding="utf-8") as f:
    f.write(updated_content)
print(f"Updated {old_tex_path}")

# 2. Write thesismain.tex (identical root file)
with open(new_thesismain_path, "w", encoding="utf-8") as f:
    f.write(updated_content)
print(f"Created and synchronized {new_thesismain_path}")
