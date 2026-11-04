import re
from pathlib import Path

target_file = Path("scientific-thesis-template-fresh/chapters-en/10 - introduction.tex")
text = target_file.read_text(encoding="utf-8")

old_pattern = r"% ---------------------------------------------------------------------------------\s*\\section\{Research Questions and Hypotheses\}.*?(?=% ---------------------------------------------------------------------------------\s*\\section\{Method or Approach)"

new_section = r"""% ---------------------------------------------------------------------------------
\section{Research Questions and Hypotheses}\label{sec:introduction:research-question}
% ---------------------------------------------------------------------------------

To address these limitations, the following primary research question is investigated:

\begin{quote}
\textbf{Main Research Question (MRQ):} \textit{How can an autonomous agentic framework integrate Large Language Models (LLMs) with deterministic compilation and symbolic planning oracles to enable reliable PDDL domain model formulation and closed-loop fault repair without human intervention?}~\cite{x}
\end{quote}

To address the MRQ systematically, three operational sub-research questions are formulated:

\begin{description}[leftmargin=1.5em]
    \item[\textbf{RQ1 (AST-Centric Formulation \& Two-Way Semantic Correctness):}] When provided with natural-language domain descriptions alongside ground-truth types, predicates, and action signatures, to what extent does decoupling relational semantic reasoning (via an Abstract Syntax Tree blueprint and deterministic compilation) from concrete syntax generation improve two-way semantic task success---satisfying both forward Soundness on ground-truth physics and inverse Completeness on reference problems---compared to direct text generation (\texttt{ZERO\_SHOT}) and uncompiled AST generation (\texttt{ABLATION\_NO\_AST})?~\cite{x}
    \item[\textbf{RQ2 (Diagnostic Triage \& Fault Repair Efficiency):}] To what extent does structured, layered diagnostic triage (analyzing compiler syntax, translator typing, plan simulation, and search reachability) improve repair success and reduce the repair iterations required to resolve systematic single-action domain mutations (unsatisfiable preconditions and missing goal add-effects) compared to re-prompting with raw, unstructured error traces (\texttt{ABLATION\_NO\_TRIAGE})?~\cite{x}
    \item[\textbf{RQ3 (Descriptive Computational Telemetry):}] What are the operational computational costs---measured by prompt and completion token consumption, wall-clock inference latency, and convergence iterations---incurred across experimental conditions under deterministic decoding ($T = 0.0$)?~\cite{x}
\end{description}

Based on these research questions, two scientific hypotheses are formulated for statistical testing:

\begin{enumerate}[label=\textbf{(H\arabic*)}, leftmargin=2.2em]
    \item When an LLM synthesizes only action preconditions and effects over fixed ground-truth signatures, generating domains via an intermediate AST blueprint and deterministic compilation achieves significantly higher two-way semantic task success (where plans found on the generated domain are valid on the ground-truth domain, and plans found on the ground-truth domain are valid on the generated domain across all task problems) than direct zero-shot text generation (\texttt{ZERO\_SHOT}) and AST generation without deterministic compilation (\texttt{ABLATION\_NO\_AST}), as evaluated by McNemar's test~\cite{x}. Syntactic Validity Rate (\gls{svr}) is reported as a sanity check~\cite{x}.
    \item Structured, layered diagnostic triage achieves significantly higher repair success (evaluated via McNemar's test) and requires significantly fewer repair iterations (evaluated via the Wilcoxon signed-rank test, with failed runs assigned a maximum penalty of 6 iterations) to repair controlled single-action domain mutations than re-prompting with raw, unstructured error traces (\texttt{ABLATION\_NO\_TRIAGE})~\cite{x}.
\end{enumerate}

Research Question RQ3 is evaluated descriptively by logging token consumption, wall-clock latency, and repair iterations across all experimental conditions, providing a transparent operational accounting of computational requirements without hypothesis testing~\cite{x}.

"""

new_text, count = re.subn(old_pattern, lambda m: new_section, text, flags=re.DOTALL)
print(f"Replacements made in 10 - introduction.tex: {count}")
assert count == 1, "Pattern replacement failed in 10 - introduction.tex"

target_file.write_text(new_text, encoding="utf-8")
print("Successfully updated 10 - introduction.tex")
