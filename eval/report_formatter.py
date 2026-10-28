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
        " TABLE 2: HIERARCHICAL MULTI-GRANULAR FAULT LOCALIZATION (H-MGFL) PERFORMANCE",
        "=" * 125,
        f"{'DOMAIN':<{domain_col_width}} | {'IDENTIFIER':<20} | {'L1: TOP-1 ELEM':<18} | {'L1: FLA':<7} | {'L1: MRR':<7} | {'L2: REPAIR OP':<24} | {'ARITY':<8} | {'PRE F1':<6} | {'ADD F1':<6} | {'DEL F1'}",
        "-" * 125
    ]
    for r in results:
        d = str(r.get("domain", ""))[:domain_col_width]
        ident = str(r.get("flaw") or r.get("task_id") or r.get("flaw_category") or "")[:20]
        t1_elem = str(r.get("top1_element") or "NONE")[:18]
        fla_t1 = "TRUE" if r.get("fla_top1") else ("FALSE" if r.get("fla_top1") is not None else "N/A")
        mrr_val = f"{r.get('fla_mrr', 0.0):.2f}" if r.get("fla_mrr") is not None else "N/A"
        t1_op = str(r.get("top1_repair_op") or "NONE")[:24]
        arity_val = f"{r.get('parameter_arity_match', 0.0)*100:.0f}%" if r.get("parameter_arity_match") is not None else "N/A"
        p_f1 = f"{r.get('precondition_f1', 0.0):.2f}"
        a_f1 = f"{r.get('add_effect_f1', 0.0):.2f}"
        d_f1 = f"{r.get('delete_effect_f1', 0.0):.2f}"
        lines.append(f"{d:<{domain_col_width}} | {ident:<20} | {t1_elem:<18} | {fla_t1:<7} | {mrr_val:<7} | {t1_op:<24} | {arity_val:<8} | {p_f1:<6} | {a_f1:<6} | {d_f1}")
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

    avg_f1 = sum(r.get("macro_structural_f1", 0.0) for r in results) / total_tasks
    fla_top1_count = sum(1 for r in results if r.get("fla_top1"))
    fla_top3_count = sum(1 for r in results if r.get("fla_top3"))
    avg_mrr = sum(r.get("fla_mrr", 0.0) for r in results if r.get("fla_mrr") is not None) / max(1, sum(1 for r in results if r.get("fla_mrr") is not None))
    avg_act_f1 = sum(r.get("action_f1", 0.0) for r in results) / total_tasks
    avg_arity = sum(r.get("parameter_arity_match", 0.0) for r in results) / total_tasks
    avg_pre_f1 = sum(r.get("precondition_f1", 0.0) for r in results) / total_tasks
    avg_add_f1 = sum(r.get("add_effect_f1", 0.0) for r in results) / total_tasks
    avg_del_f1 = sum(r.get("delete_effect_f1", 0.0) for r in results) / total_tasks
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
        "HIERARCHICAL MULTI-GRANULAR FAULT LOCALIZATION (H-MGFL):",
        f"  - Level 1: FLA Top-1 Accuracy           : {fla_top1_count}/{total_tasks} ({fla_top1_count/total_tasks*100:.1f}%)",
        f"  - Level 1: FLA Top-3 Accuracy           : {fla_top3_count}/{total_tasks} ({fla_top3_count/total_tasks*100:.1f}%)",
        f"  - Level 1: Mean Reciprocal Rank (MRR)   : {avg_mrr:.4f}",
        f"  - Level 1: Action Schema F1             : {avg_act_f1:.4f}",
        f"  - Level 2: Parameter Arity Alignment    : {avg_arity*100:.1f}%",
        f"  - Level 2: Mean Precondition F1         : {avg_pre_f1:.4f}",
        f"  - Level 2: Mean Add-Effect F1           : {avg_add_f1:.4f}",
        f"  - Level 2: Mean Delete-Effect F1        : {avg_del_f1:.4f}",
        f"  - Mean Macro Structural F1              : {avg_f1:.4f}",
        f"  - Mean Repair Iterations (k)            : {avg_iters:.2f}",
        f"  - Total Elapsed Execution Time          : {elapsed_seconds:.2f}s"
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
        "| Domain | Identifier | Gold Fault Element | L1: Top-1 Element | L1: Top-1 Match | L1: MRR | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |",
        "|:---|:---|:---|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|"
    ])
    for r in results:
        ident = r.get("flaw") or r.get("task_id") or r.get("flaw_category") or ""
        gold_elem = r.get("gold_target_action") or r.get("gold_fault_element") or "N/A"
        top1_elem = r.get("top1_element") or "NONE"
        mrr_str = f"{r.get('fla_mrr', 0.0):.2f}" if r.get("fla_mrr") is not None else "N/A"
        match_str = str(r.get("fla_top1")) if r.get("fla_top1") is not None else "N/A"
        arity_str = f"{r.get('parameter_arity_match', 0.0)*100:.0f}%" if r.get("parameter_arity_match") is not None else "N/A"
        report_lines.append(
            f"| `{r.get('domain')}` | `{ident}` | `{gold_elem}` | "
            f"`{top1_elem}` | {match_str} | {mrr_str} | "
            f"`{r.get('top1_repair_op') or 'NONE'}` | {arity_str} | "
            f"{r.get('precondition_f1', 0.0):.3f} | {r.get('add_effect_f1', 0.0):.3f} | {r.get('delete_effect_f1', 0.0):.3f} |"
        )

    content = "\n".join(report_lines) + "\n"
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    return content
