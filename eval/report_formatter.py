"""
eval/report_formatter.py
Standardized, publication-ready reporting utilities for Automated Planning empirical evaluations.
Formats:
- Table 1: Decoupled Multi-Stage Verification Funnel Table
- Table 2: Hierarchical Multi-Granular Fault Localization (H-MGFL) Table
- Aggregate Summary Text with exact funnel percentages
- Full Markdown report files (report.md)
"""

from pathlib import Path
from typing import Dict, List, Any, Optional

def format_funnel_table(results: List[Dict[str, Any]], domain_col_width: int = 14) -> str:
    """Formats Table 1: Decoupled Multi-Stage Verification Funnel Table."""
    lines = [
        "=" * 125,
        " TABLE 1: DECOUPLED MULTI-STAGE VERIFICATION FUNNEL (SYNTAX -> SOLVE -> EXEC -> FEAS -> INTERP -> SOUND -> E2E)",
        "=" * 125,
        f"{'DOMAIN':<{domain_col_width}} | {'TASK / FLAW':<26} | {'AGENT':<22} | {'SYNTAX':<6} | {'SOLVE':<7} | {'EXEC':<6} | {'FEAS':<6} | {'INTERP':<6} | {'SOUND':<6} | {'E2E':<6} | {'ITERS'}",
        "-" * 125
    ]
    for r in results:
        d = str(r.get("domain", ""))[:domain_col_width]
        task_label = str(r.get("flaw_category") or r.get("task_type") or r.get("flaw") or "")[:26]
        a = str(r.get("agent") or r.get("agent_type") or "")[:22]
        syn = "PASS" if r.get("is_syntax_valid") else "FAIL"
        solv = "TIMEOUT" if r.get("planner_timeout") else ("PASS" if r.get("is_solvable") else "FAIL")
        exc = "PASS" if r.get("executability_valid") else "FAIL"
        feas = "PASS" if r.get("feasibility_valid") else "FAIL"
        interp = "PASS" if r.get("interpretability_valid") else "FAIL"
        sound = "PASS" if r.get("semantic_soundness") else "FAIL"
        e2e = "PASS" if r.get("e2e_success") else "FAIL"
        it = f"{r.get('iterations_used', 1)}"
        lines.append(f"{d:<{domain_col_width}} | {task_label:<26} | {a:<22} | {syn:<6} | {solv:<7} | {exc:<6} | {feas:<6} | {interp:<6} | {sound:<6} | {e2e:<6} | {it}")
    lines.append("-" * 125)
    return "\n".join(lines)

def format_hmgfl_table(results: List[Dict[str, Any]], domain_col_width: int = 14) -> str:
    """Formats Table 2: Hierarchical Multi-Granular Fault Localization (H-MGFL) Table."""
    lines = [
        "=" * 125,
        " TABLE 2: HIERARCHICAL MULTI-GRANULAR FAULT LOCALIZATION (H-MGFL) & REPAIR PERFORMANCE",
        "=" * 125,
        f"{'DOMAIN':<{domain_col_width}} | {'IDENTIFIER':<24} | {'L1: TOP-1 ELEM':<24} | {'L2: REPAIR OP':<28} | {'REPAIRED':<10} | {'ITERS'}",
        "-" * 125
    ]
    for r in results:
        d = str(r.get("domain", ""))[:domain_col_width]
        ident = str(r.get("flaw") or r.get("task_id") or r.get("flaw_category") or r.get("agent_type") or "")[:24]
        t1_elem = str(r.get("top1_element") or "NONE")[:24]
        t1_op = str(r.get("top1_repair_op") or "NONE")[:28]
        repaired = "YES" if r.get("is_repaired") else ("N/A" if r.get("iterations_used", 1) <= 1 else "NO")
        it = str(r.get("iterations_used", 1))
        lines.append(f"{d:<{domain_col_width}} | {ident:<24} | {t1_elem:<24} | {t1_op:<28} | {repaired:<10} | {it}")
    lines.append("-" * 125)
    return "\n".join(lines)

def format_aggregate_funnel_summary(results: List[Dict[str, Any]], elapsed_seconds: float = 0.0) -> str:
    """Formats statistical text aggregations answering research questions."""
    total_tasks = len(results)
    if total_tasks == 0:
        return "No evaluation tasks to aggregate."

    num_domains = len(set(r.get("domain") for r in results if r.get("domain")))
    svr_count = sum(1 for r in results if r.get("is_syntax_valid"))
    solv_count = sum(1 for r in results if r.get("is_solvable"))
    timeout_count = sum(1 for r in results if r.get("planner_timeout"))
    exec_count = sum(1 for r in results if r.get("executability_valid"))
    feas_count = sum(1 for r in results if r.get("feasibility_valid"))
    interp_count = sum(1 for r in results if r.get("interpretability_valid"))
    sound_count = sum(1 for r in results if r.get("semantic_soundness"))
    e2e_count = sum(1 for r in results if r.get("e2e_success"))

    repaired_count = sum(1 for r in results if r.get("is_repaired"))
    multi_iter_tasks = [r for r in results if r.get("iterations_used", 1) > 1]
    rsr_pct = (repaired_count / len(multi_iter_tasks) * 100) if multi_iter_tasks else 100.0
    avg_iters = sum(r.get("iterations_used", 1) for r in results) / total_tasks

    lines = [
        f"DECOUPLED MULTI-STAGE VERIFICATION FUNNEL ({total_tasks} evaluated tasks across {num_domains} pure domain(s)):",
        f"  Stage 1: Syntactic Validity Rate (SVR)      : {svr_count}/{total_tasks} ({svr_count/total_tasks*100:.1f}%)",
        f"  Stage 2a: Planner Solvability Rate (PSR)    : {solv_count}/{total_tasks} ({solv_count/total_tasks*100:.1f}%) [Timeouts: {timeout_count}]",
        f"  Stage 2b: Internal Executability (Self-Val) : {exec_count}/{total_tasks} ({exec_count/total_tasks*100:.1f}%)",
        f"  Stage 3a: Forward Soundness (Feasibility)   : {feas_count}/{total_tasks} ({feas_count/total_tasks*100:.1f}%)",
        f"  Stage 3b: Inverse Completeness (Interp.)    : {interp_count}/{total_tasks} ({interp_count/total_tasks*100:.1f}%)",
        f"  Stage 3c: Strict Semantic Soundness         : {sound_count}/{total_tasks} ({sound_count/total_tasks*100:.1f}%)",
        f"  Overall: Strict E2E Gate (All Combined)     : {e2e_count}/{total_tasks} ({e2e_count/total_tasks*100:.1f}%)",
        "",
        "FAULT LOCALIZATION & REPAIR DYNAMICS:",
        f"  - Multi-iteration Tasks Requiring Repair   : {len(multi_iter_tasks)}",
        f"  - Repair Success Rate (RSR)                 : {repaired_count}/{len(multi_iter_tasks)} ({rsr_pct:.1f}%)" if multi_iter_tasks else "  - Repair Success Rate (RSR)                 : 100.0% (No repair needed)",
        f"  - Mean Total Iterations (k)                 : {avg_iters:.2f}",
        f"  - Total Elapsed Execution Time              : {elapsed_seconds:.2f}s"
    ]
    return "\n".join(lines)

def generate_markdown_report(
    title: str,
    results: List[Dict[str, Any]],
    output_path: Optional[Path] = None
) -> str:
    """Generates publication-ready Markdown evaluation report."""
    report_lines = [
        f"# {title}",
        "",
        "## 1. Decoupled Multi-Stage Verification Funnel Summary",
        "",
        "| Domain | Task / Flaw | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |",
        "|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]
    for r in results:
        task_lbl = r.get("flaw_category") or r.get("task_type") or r.get("flaw") or ""
        agent_lbl = r.get("agent") or r.get("agent_type") or ""
        solv_str = "Timeout" if r.get("planner_timeout") else str(r.get('is_solvable'))
        report_lines.append(
            f"| `{r.get('domain')}` | `{task_lbl}` | `{agent_lbl}` | "
            f"{r.get('is_syntax_valid')} | {solv_str} | {r.get('executability_valid')} | "
            f"{r.get('feasibility_valid')} | {r.get('interpretability_valid')} | {r.get('semantic_soundness')} | **{r.get('e2e_success')}** | {r.get('iterations_used')} |"
        )

    report_lines.extend([
        "",
        "## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance",
        "",
        "| Domain | Identifier | L1: Top-1 Element | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |",
        "|:---|:---|:---|:---|:---:|:---:|:---:|:---:|"
    ])
    for r in results:
        ident = r.get("flaw") or r.get("task_id") or r.get("flaw_category") or ""
        top1_elem = r.get("top1_element") or "NONE"
        arity_str = f"{r.get('parameter_arity_match', 0.0)*100:.0f}%" if r.get("parameter_arity_match") is not None else "N/A"
        report_lines.append(
            f"| `{r.get('domain')}` | `{ident}` | "
            f"`{top1_elem}` | "
            f"`{r.get('top1_repair_op') or 'NONE'}` | {arity_str} | "
            f"{r.get('precondition_f1', 0.0):.3f} | {r.get('add_effect_f1', 0.0):.3f} | {r.get('delete_effect_f1', 0.0):.3f} |"
        )

    content = "\n".join(report_lines) + "\n"
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    return content
