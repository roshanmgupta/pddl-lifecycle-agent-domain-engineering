import re
from pathlib import Path

FRESH_DIR = Path("scientific-thesis-template-fresh").resolve()
main_tex = FRESH_DIR / "main-english.tex"
thesismain_tex = FRESH_DIR / "thesismain.tex"

abstract_en = """% -----------------------------------------------------------------------------
% Abstract
% -----------------------------------------------------------------------------
\\section*{Abstract}
This thesis addresses the automated engineering of formal domain models in the Planning Domain Definition Language (PDDL) for classical AI planning systems using Large Language Models (LLMs)~\\cite{ghallab2004,mcdermott1998,georgievski2023}.
Specifically, we investigate how an autonomous agentic framework can formulate syntactically valid and semantically sound PDDL domain models and execute closed-loop fault repair without human intervention~\\cite{x}.
Previous work has failed to address this challenge reliably because unconstrained language models suffer from severe syntax collapse during direct generation, while existing iterative repair approaches re-prompt models with raw, unstructured error traces that lack diagnostic localization and cause backward regression errors~\\cite{oswald2024,bavandpour2026llmonly,patil2024}.
To resolve these limitations, we propose an autonomous lifecycle framework that decouples relational semantic reasoning from concrete PDDL syntax through a typed Abstract Syntax Tree (AST) intermediate representation, while directing closed-loop repair through a four-layer diagnostic triage engine that systematically isolates syntax, typing, plan simulation, and reachability failures~\\cite{x}.
We implemented this architecture in Python using deterministic compilation and symbolic oracles (Fast Downward and VAL), evaluating it on OpenAI GPT-4o across six normalized classical International Planning Competition (IPC) domains for domain formulation and 24 controlled mutation tasks for fault repair under non-parametric statistical testing and automated token and latency logging~\\cite{x}.
The resulting framework demonstrates that neuro-symbolic coupling and structured diagnostic triage enable non-experts to reliably formulate sound planning models and autonomously recover from domain bugs, substantially reducing the knowledge-engineering bottleneck for real-world automated planning systems~\\cite{x}.

\\section*{Kurzfassung}
\\begin{otherlanguage}{ngerman}
Diese Masterarbeit befasst sich mit der automatisierten Erstellung formaler Domänenmodelle in der Planning Domain Definition Language (PDDL) für klassische KI-Planungssysteme mittels großer Sprachmodelle (LLMs).
Konkret untersuchen wir, wie ein autonomes agentenbasiertes Framework syntaktisch valide und semantisch korrekte PDDL-Domänenmodelle formulieren und geschlossene Fehlerreparaturen ohne menschliche Intervention durchführen kann.
Bisherige Arbeiten scheitern an dieser Herausforderung, da ungesteuerte Sprachmodelle bei der direkten Generierung zu schweren Syntaxfehlern neigen und iterative Reparaturansätze Modelle mit unstrukturierten Fehlermeldungen rückkoppeln, was an mangelnder Fehlerlokalisierung leidet und Folgefehler verursacht.
Um diese Einschränkungen zu überwinden, stellen wir ein autonomes Lifecycle-Framework vor, das relationales logisches Schließen durch eine typisierte Abstract-Syntax-Tree-Zwischendarstellung von der PDDL-Syntax entkoppelt und geschlossene Reparaturen über ein vierstufiges diagnostisches Triage-System steuert.
Wir haben diese Architektur unter Einbindung symbolischer Orakel (Fast Downward und VAL) implementiert und mit OpenAI GPT-4o über sechs normierte IPC-Domänen zur Domänenformulierung sowie 24 kontrollierte Mutationsaufgaben zur Fehlerreparatur unter nicht-parametrischen statistischen Tests und automatisierter Protokollierung von Rechenzeit und Tokenverbrauch evaluiert.
Die Ergebnisse zeigen, dass neuro-symbolische Kopplung und strukturierte Fehlerdiagnose die automatisierte Generierung korrekter Planungsmodelle ermöglichen und dadurch den Knowledge-Engineering-Flaschenhals für den praktischen Einsatz von KI-Planungssystemen erheblich reduzieren.
\\end{otherlanguage}"""

for target_file in [main_tex, thesismain_tex]:
    text = target_file.read_text(encoding="utf-8")
    text_norm = text.replace("\r\n", "\n")
    
    # Locate from \section*{Abstract} to \microtypesetup{protrusion=false}
    start_pos = text_norm.find("\\section*{Abstract}")
    end_pos = text_norm.find("\\microtypesetup{protrusion=false}")
    
    if start_pos != -1 and end_pos != -1:
        updated = text_norm[:start_pos] + abstract_en + "\n\n\n" + text_norm[end_pos:]
        target_file.write_text(updated, encoding="utf-8")
        print(f"Successfully updated Abstract in {target_file.name}")
    else:
        print(f"Could not locate abstract boundaries in {target_file.name}")

print("Abstract update complete.")
