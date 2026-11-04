import sys
import os
from pathlib import Path

# Ensure UTF-8 unbuffered real-time stdout terminal logging
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import json
import os
import time
import re
import glob
import csv
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

load_dotenv(override=True)

from config.paths import (
    get_benchmark_dir,
    get_temp_domain_path,
    get_temp_problem_path,
    get_flaw_output_dir,
    get_elicitation_output_dir,
    get_generated_domain_filename,
    get_generated_problem_filename,
    get_generated_plan_filename,
)

from benchmark.schema import BenchmarkTask, LifecycleTaskType
from benchmark.loader import (
    list_benchmark_domains,
    list_domain_flaws,
    load_flaw_task,
    load_elicitation_task,
    SELECTED_BENCHMARK_DOMAINS,
    list_autoplanbench_domains,
    load_autoplanbench_synthesis_task,
)
from benchmark.pure_strips_benchmarks import (
    AUTOPLANBENCH_PURE_STRIPS_DOMAINS,
    list_autoplanbench_problem_files,
    get_autoplanbench_domain_folder,
)
from eval.metrics import EvaluationMetrics
from eval.benchmark_runner import evaluate_candidate_pddl
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation,
)
from graph import pddl_lifecycle_graph
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
)

# Canonical 6 Core Domains
SIX_CORE_DOMAINS = [
    "blocksworld",
    "gripper",
    "logistics",
    "depot",
    "rovers",
    "satellite"
]

# Supported Architectures
ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_TRIAGE",
    "ABLATION_NO_AST",
    "UNSTRUCTURED_RETRY",
    "ZERO_SHOT"
]

ARCH_DESCRIPTIONS = {
    "CLOSED_LOOP_AST_AGENT": "🧠 Closed-Loop AST Agent (FaultLocalizationNode + Surgical AST)",
    "ABLATION_NO_TRIAGE": "🔬 Ablation: No Fault Localization (AST Blueprint + Raw Truncated Errors)",
    "ABLATION_NO_AST": "🔬 Ablation: No AST (Direct PDDL Text + Fault Localization)",
    "UNSTRUCTURED_RETRY": "⚡ Baseline: Unstructured Retry (Direct PDDL + Raw Truncated Errors)",
    "ZERO_SHOT": "🎯 Baseline: Zero-Shot (Direct PDDL, No Feedback Loop)"
}

FEEDBACK_EXPLANATIONS = {
    "CLOSED_LOOP_AST_AGENT": {
        "title": "Structured Model-Based Fault Localization + Surgical AST Blueprint",
        "mechanism": "Layered Model-Based Fault Localization triages raw oracle logs into root-cause categories, pinpointing the exact faulty AST action schema and preconditions/effects. The surgical repair prompt provides only the target action schema from the Pydantic AST blueprint alongside structured repair hints, preserving non-faulty actions untouched.",
        "target": "Pydantic AST Action Schema Blueprint (JSON / PDDL domain skeleton)"
    },
    "ABLATION_NO_TRIAGE": {
        "title": "Raw Truncated Oracle Errors + Surgical AST Blueprint (No Fault Localization)",
        "mechanism": "Bypasses the Diagnostic LLM Agent entirely. Raw, unparsed compiler/solver logs (truncated to 1500 chars) are passed directly into the surgical AST repair prompt without error classification or causal invariant context.",
        "target": "Pydantic AST Action Schema Blueprint"
    },
    "ABLATION_NO_AST": {
        "title": "Structured Model-Based Fault Localization + Raw Full PDDL Text (No AST)",
        "mechanism": "Uses the Diagnostic LLM Agent for structured fault localization, but repairs by re-generating the entire raw PDDL domain text from scratch without Pydantic AST schemas or programmatic serialization.",
        "target": "Raw PDDL Domain Code (define (domain ...) ...)"
    },
    "UNSTRUCTURED_RETRY": {
        "title": "Raw Truncated Oracle Errors + Raw Full PDDL Text (No AST, No Fault Localization)",
        "mechanism": "Passes raw unparsed compiler/solver logs directly back to the LLM to edit the raw PDDL domain file without structured schemas or diagnostic triage.",
        "target": "Raw PDDL Domain Code (define (domain ...) ...)"
    },
    "ZERO_SHOT": {
        "title": "Single-Pass Direct Prompting (No Feedback Loop)",
        "mechanism": "Single LLM generation pass directly from natural language requirements. No validator or solver feedback is ever passed back to the model.",
        "target": "Raw PDDL Domain Code (define (domain ...) ...)"
    }
}

# ==============================================================================
# Streamlit Page Configuration & Styling
# ==============================================================================
st.set_page_config(
    page_title="PDDL Lifecycle Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5 0%, #7B1FA2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.15rem;
    }
    .sub-header {
        font-size: 0.98rem;
        color: #546E7A;
        margin-bottom: 1.2rem;
    }
    .kpi-container {
        display: flex;
        gap: 0.8rem;
        margin-bottom: 1.2rem;
        flex-wrap: wrap;
    }
    .kpi-card {
        background-color: #F8F9FA;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        min-width: 130px;
        flex: 1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .kpi-title {
        font-size: 0.8rem;
        color: #616161;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }
    .kpi-value {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1565C0;
    }
    .phase-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.82rem;
        margin-bottom: 0.4rem;
    }
    .phase-badge-info { background-color: #E3F2FD; color: #0D47A1; }
    .phase-badge-success { background-color: #E8F5E9; color: #1B5E20; }
    .phase-badge-warning { background-color: #FFF3E0; color: #E65100; }
    .phase-badge-error { background-color: #FFEBEE; color: #B71C1C; }
    .stCodeBlock {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Helper Functions: Benchmark & Disk Persistence
# ==============================================================================
def list_domain_problems(domain_name: str) -> List[str]:
    """Lists problem instance files (.pddl) in autoplanbench/data/<domain>/orig_problems/."""
    p_dir = get_benchmark_dir() / domain_name / "orig_problems"
    if not p_dir.exists():
        return []
    probs = sorted(list(p_dir.glob("*.pddl")), key=lambda p: (len(p.name), p.name))
    return [p.name for p in probs]


def load_domain_synthesis_task(domain_name: str, problem_instance: Optional[str] = None) -> Optional[BenchmarkTask]:
    """Loads a Direct NL Domain Synthesis task from domain_encoding.txt and target problem."""
    dom_dir = get_benchmark_dir() / domain_name
    if not dom_dir.exists():
        return None
    spec_file = dom_dir / "domain_encoding.txt"
    dom_file = dom_dir / "domain.pddl"

    orig_dir = dom_dir / "orig_problems"
    if not orig_dir.exists():
        return None

    if problem_instance:
        prob_file = orig_dir / problem_instance
    else:
        prob_files = sorted(list(orig_dir.glob("*.pddl")), key=lambda p: (len(p.name), p.name))
        prob_file = prob_files[0] if prob_files else None

    if not spec_file.exists() or not dom_file.exists() or not prob_file or not prob_file.exists():
        return None

    spec = spec_file.read_text(encoding="utf-8")
    spec = re.sub(r"\[NOTE:[^\]]+\]\s*", "", spec).strip()
    gt_dom = dom_file.read_text(encoding="utf-8")
    gt_prob = prob_file.read_text(encoding="utf-8")
    prob_stem = prob_file.stem

    return BenchmarkTask(
        task_id=f"{domain_name}_{prob_stem}",
        domain_family=domain_name,
        task_type=LifecycleTaskType.ELICITATION,
        title=f"{domain_name.upper()} Direct NL Synthesis ({prob_file.name})",
        natural_language_requirements=spec,
        initial_domain_pddl=None,
        initial_problem_pddl=gt_prob,
        ground_truth_domain_pddl=gt_dom,
        ground_truth_problem_pddl=gt_prob
    )


def save_output_to_disk(state: dict, task: Optional[Any] = None) -> tuple:
    """Saves compiled domain.pddl, problem.pddl, blueprint.json, diagnostic_report.json, and plan.txt."""
    domain_bp = state.get("pddl_domain_blueprint", {})
    if isinstance(domain_bp, dict):
        d_name = domain_bp.get("domain_name", "generated_domain")
    else:
        d_name = getattr(domain_bp, "domain_name", "generated_domain")

    d_name = re.sub(r'[^a-zA-Z0-9_\-]', '', str(d_name)).lower() or "generated_domain"

    is_flaw = state.get("is_synthetic_repair", False)
    if task:
        tt = getattr(task, "task_type", None)
        if tt == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR or getattr(tt, "value", "") == "SYNTHETIC_FAULT_REPAIR":
            is_flaw = True

    if is_flaw:
        base_dir = str(get_flaw_output_dir())
    else:
        base_dir = str(get_elicitation_output_dir())

    output_dir = os.path.join(base_dir, d_name)
    os.makedirs(output_dir, exist_ok=True)

    dom_stem = Path(get_generated_domain_filename()).stem
    dom_ext = Path(get_generated_domain_filename()).suffix or ".pddl"
    prob_stem = Path(get_generated_problem_filename()).stem
    prob_ext = Path(get_generated_problem_filename()).suffix or ".pddl"
    plan_stem = Path(get_generated_plan_filename()).stem
    plan_ext = Path(get_generated_plan_filename()).suffix or ".txt"

    existing_domain_files = glob.glob(os.path.join(output_dir, f"{dom_stem}_*{dom_ext}"))
    existing_indices = []
    for fpath in existing_domain_files:
        fname = os.path.basename(fpath)
        match = re.search(rf"{re.escape(dom_stem)}_(\d+)\{re.escape(dom_ext)}", fname)
        if match:
            existing_indices.append(int(match.group(1)))

    next_idx = (max(existing_indices) + 1) if existing_indices else 1

    domain_pddl = state.get("generated_domain_pddl", "")
    problem_pddl = state.get("generated_problem_pddl", "")

    dom_file_path = os.path.join(output_dir, f"{dom_stem}_{next_idx}{dom_ext}")
    prob_file_path = os.path.join(output_dir, f"{prob_stem}_{next_idx}{prob_ext}")
    json_file_path = os.path.join(output_dir, f"blueprint_{next_idx}.json")
    diag_file_path = os.path.join(output_dir, f"diagnostic_report_{next_idx}.json")
    plan_file_path = os.path.join(output_dir, f"{plan_stem}_{next_idx}{plan_ext}")

    if domain_pddl:
        with open(dom_file_path, "w", encoding="utf-8") as f:
            f.write(domain_pddl)

    if problem_pddl:
        with open(prob_file_path, "w", encoding="utf-8") as f:
            f.write(problem_pddl)

    meta_content = {
        "domain_name": d_name,
        "run_index": next_idx,
        "domain_blueprint": state.get("pddl_domain_blueprint"),
        "iteration_count": state.get("iteration_count", 0),
        "is_valid": not bool(state.get("verification_errors"))
    }
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(meta_content, f, indent=2, default=str)

    diag_reports = state.get("historical_diagnostic_reports", []) or state.get("diagnostic_reports", [])
    init_errs = state.get("initial_verification_errors", []) or state.get("verification_errors", [])
    curr_errs = state.get("verification_errors", [])
    is_valid = not bool(curr_errs)
    plan_res = state.get("generated_plan_result")

    serializable_reports = []
    for r in diag_reports:
        if hasattr(r, "model_dump"):
            serializable_reports.append(r.model_dump())
        elif isinstance(r, dict):
            serializable_reports.append(r)
        else:
            serializable_reports.append(str(r))

    import datetime
    diag_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "domain_name": d_name,
        "run_index": next_idx,
        "verification_status": "PASSED" if is_valid else "FAILED",
        "repair_iterations_used": state.get("iteration_count", 0),
        "initial_verification_errors": init_errs,
        "final_verification_errors": curr_errs,
        "diagnostic_issues_count": len(serializable_reports),
        "diagnostic_reports": serializable_reports,
        "formatted_diagnostic_feedback": state.get("formatted_diagnostic_feedback", ""),
    }
    with open(diag_file_path, "w", encoding="utf-8") as f:
        json.dump(diag_data, f, indent=2, default=str)

    actual_plan_path = None
    if plan_res and isinstance(plan_res, dict) and plan_res.get("is_solvable") and plan_res.get("plan_steps"):
        with open(plan_file_path, "w", encoding="utf-8") as f:
            for i, step in enumerate(plan_res["plan_steps"], 1):
                f.write(f"{i}: {step}\n")
        actual_plan_path = plan_file_path

    return d_name, next_idx, dom_file_path, prob_file_path, diag_file_path, actual_plan_path


# ==============================================================================
# Session State Initialization
# ==============================================================================
if "results_history" not in st.session_state:
    st.session_state["results_history"] = []
if "active_result" not in st.session_state:
    st.session_state["active_result"] = None
if "active_state" not in st.session_state:
    st.session_state["active_state"] = None
if "active_task" not in st.session_state:
    st.session_state["active_task"] = None
if "last_saved_info" not in st.session_state:
    st.session_state["last_saved_info"] = None
if "phase_events_history" not in st.session_state:
    st.session_state["phase_events_history"] = []
if "six_domains_history" not in st.session_state:
    st.session_state["six_domains_history"] = []


# ==============================================================================
# Header
# ==============================================================================
st.markdown('<div class="main-header">🧠 Autonomous PDDL Domain Lifecycle Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Closed-Loop AST Synthesis, Symbolic Oracle Triage (VAL & Fast Downward), and Transparent Feedback across Baselines & Ablations</div>', unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR CONFIGURATION CONTROLS
# ==============================================================================
st.sidebar.title("⚙️ Lifecycle Architecture Controls")

# 1. Dataset Source Selection
dataset_source = st.sidebar.radio(
    "📂 Dataset Track:",
    options=[
        "AutoPlanBench (Pure STRIPS NL Descriptions)",
        "AutoPlanBench (Curated Lifecycle & Flaw Tasks)"
    ],
    index=0,
    help="Pure STRIPS NL Descriptions: standard IPC domains with natural language action descriptions. Curated Lifecycle Tasks: curated benchmark tasks with specifications and synthetic flaws."
)

st.sidebar.markdown("---")

# 2. Execution Scope (Single Task vs 6 Core Domains vs Custom Batch)
exec_scope = st.sidebar.radio(
    "Execution Scope:",
    options=[
        "🎯 Single Task Run",
        "🏛️ Run 6 Core Domains Benchmark",
        "📦 Custom Batch Benchmark Run"
    ],
    index=0,
    help="Single Task: run one task with live observability. Run 6 Core Domains: evaluate blocksworld, gripper, logistics, depot, rovers, satellite in one go across all architectures. Custom Batch: evaluate a custom set."
)

st.sidebar.markdown("---")

# Operating Modality (for Curated Lifecycle Tasks)
selected_mode = "🌿 Direct NL Domain Synthesis"
if dataset_source == "AutoPlanBench (Curated Lifecycle & Flaw Tasks)":
    selected_mode = st.sidebar.radio(
        "Operating Modality:",
        options=[
            "🌿 Direct NL Domain Synthesis",
            "🔧 Faulty Domain Repair"
        ],
        index=0,
        help="Select which lifecycle engineering phase to execute."
    )

active_single_task: Optional[BenchmarkTask] = None
batch_tasks_to_run: List[BenchmarkTask] = []
batch_agents_to_run: List[str] = ["CLOSED_LOOP_AST_AGENT"]
selected_single_agent: str = "CLOSED_LOOP_AST_AGENT"
max_iterations: int = 5
csv_output_filename: str = "benchmark_results.csv"

# ------------------------------------------------------------------------------
# DOMAIN & TASK SELECTION LOGIC
# ------------------------------------------------------------------------------
if dataset_source == "AutoPlanBench (Pure STRIPS NL Descriptions)":
    apb_domains = list_autoplanbench_domains()
    # Prioritize 6 core domains at the top
    ordered_domains = [d for d in SIX_CORE_DOMAINS if d in apb_domains] + [d for d in apb_domains if d not in SIX_CORE_DOMAINS]

    if exec_scope == "🎯 Single Task Run":
        st.sidebar.markdown("### 🌿 AutoPlanBench Synthesis Task")
        sel_domain = st.sidebar.selectbox("Choose Benchmark Domain:", ordered_domains, index=0)
        avail_problems = list_autoplanbench_problem_files(sel_domain)
        sel_prob = st.sidebar.selectbox("Choose Problem Instance:", avail_problems, index=0 if avail_problems else 0)

        active_single_task = load_autoplanbench_synthesis_task(sel_domain, sel_prob)
        if active_single_task:
            with st.sidebar.expander("📄 Natural Language Requirements", expanded=False):
                st.text(active_single_task.natural_language_requirements)

        selected_single_agent = st.sidebar.selectbox(
            "Select Architecture:",
            ARCHITECTURES,
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x),
            index=0
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Run Filename:", value=f"apb_{sel_domain}_run.csv")

    elif exec_scope == "🏛️ Run 6 Core Domains Benchmark":
        st.sidebar.markdown("### 🏛️ 6 Core Domains Benchmark")
        st.sidebar.info(
            "Evaluates the 6 core domains in one go:\n"
            "• `blocksworld`\n• `gripper`\n• `logistics`\n• `depot`\n• `rovers`\n• `satellite`"
        )
        batch_agents_to_run = st.sidebar.multiselect(
            "Select Architectures to Evaluate:",
            ARCHITECTURES,
            default=ARCHITECTURES,
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x)
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value="six_core_domains_results.csv")

        for d in SIX_CORE_DOMAINS:
            t = load_autoplanbench_synthesis_task(d, "instance-1.pddl")
            if t:
                batch_tasks_to_run.append(t)

    else: # Custom Batch
        st.sidebar.markdown("#### 📦 Custom AutoPlanBench Selection")
        selected_batch_domains = st.sidebar.multiselect(
            "Select Domains to Benchmark:",
            ordered_domains,
            default=[d for d in SIX_CORE_DOMAINS if d in ordered_domains]
        )
        batch_agents_to_run = st.sidebar.multiselect(
            "Select Architectures to Evaluate:",
            ARCHITECTURES,
            default=["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE", "UNSTRUCTURED_RETRY"],
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x)
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value="apb_batch_results.csv")

        for d in selected_batch_domains:
            t = load_autoplanbench_synthesis_task(d, "instance-1.pddl")
            if t:
                batch_tasks_to_run.append(t)

else:
    # AutoPlanBench Curated Lifecycle Tasks
    all_domains = list_benchmark_domains()
    if not all_domains:
        all_domains = SELECTED_BENCHMARK_DOMAINS

    if exec_scope == "🏛️ Run 6 Core Domains Benchmark":
        st.sidebar.markdown("### 🏛️ 6 Core Domains Benchmark")
        st.sidebar.info(
            "Evaluates the 6 core domains in one go:\n"
            "• `blocksworld`\n• `gripper`\n• `logistics`\n• `depot`\n• `rovers`\n• `satellite`"
        )
        batch_agents_to_run = st.sidebar.multiselect(
            "Select Architectures to Evaluate:",
            ARCHITECTURES,
            default=ARCHITECTURES,
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x)
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value="six_core_domains_lifecyclebench.csv")

        for d in SIX_CORE_DOMAINS:
            t = load_domain_synthesis_task(d, "instance-1.pddl") or load_elicitation_task(d)
            if t:
                batch_tasks_to_run.append(t)

    elif selected_mode == "🌿 Direct NL Domain Synthesis":
        st.sidebar.markdown("### 🌿 Direct NL Synthesis Settings")
        default_csv = "synthesis_benchmark_results.csv"

        if exec_scope == "🎯 Single Task Run":
            sel_domain = st.sidebar.selectbox("Choose Canonical Domain:", all_domains, index=0)
            avail_problems = list_domain_problems(sel_domain)
            sel_prob = st.sidebar.selectbox("Choose Problem Instance:", avail_problems, index=0 if avail_problems else 0)

            active_single_task = load_domain_synthesis_task(sel_domain, sel_prob)
            req_text = active_single_task.natural_language_requirements if active_single_task else ""
            with st.sidebar.expander("📄 Requirements Specification (`domain_encoding.txt`)", expanded=False):
                st.text(req_text)

            selected_single_agent = st.sidebar.selectbox(
                "Select Architecture:",
                ARCHITECTURES,
                format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x),
                index=0
            )
            max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
            csv_output_filename = st.sidebar.text_input("CSV Run Filename:", value="synthesis_run.csv")

        else: # Custom Batch
            selected_batch_domains = st.sidebar.multiselect(
                "Select Domains to Benchmark:",
                all_domains,
                default=[d for d in SELECTED_BENCHMARK_DOMAINS if d in all_domains]
            )
            batch_agents_to_run = st.sidebar.multiselect(
                "Select Architectures to Evaluate:",
                ARCHITECTURES,
                default=["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE", "UNSTRUCTURED_RETRY"],
                format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x)
            )
            max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
            csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value=default_csv)

            for d in selected_batch_domains:
                t = load_domain_synthesis_task(d, "instance-1.pddl")
                if t:
                    batch_tasks_to_run.append(t)

    elif selected_mode == "🔧 Faulty Domain Repair":
        st.sidebar.markdown("### 🔧 Synthetic Fault Repair Settings")
        FLAW_LABELS = {
            "flaw_01_syntax_declaration_error": "Flaw 1: Type Signature & Arity Inversion",
            "flaw_02_precondition_misalignment": "Flaw 2: Precondition Misalignment",
            "flaw_03_action_effect_deletion": "Flaw 3: Action Effect Deletion",
            "flaw_04_initial_goal_deadlock": "Flaw 4: Initial / Goal Deadlock",
            "flaw_05_state_reachability_collapse": "Flaw 5: State Reachability Collapse"
        }

        if exec_scope == "🎯 Single Task Run":
            sel_domain = st.sidebar.selectbox("Choose Canonical Domain:", all_domains, index=0)
            avail_flaws = list_domain_flaws(sel_domain) or list(FLAW_LABELS.keys())
            sel_flaw = st.sidebar.selectbox(
                "Choose Flaw Task:",
                avail_flaws,
                format_func=lambda x: FLAW_LABELS.get(x, x),
                index=0
            )
            active_single_task = load_flaw_task(sel_domain, sel_flaw)
            if active_single_task:
                st.sidebar.info(
                    f"**Fault Category**: `{active_single_task.fault_category or 'SYNTAX_PARSE'}`\n\n"
                    f"**Target Gold Action**: `{active_single_task.gold_fault_element or 'General'}`"
                )

            selected_single_agent = st.sidebar.selectbox(
                "Select Architecture:",
                ARCHITECTURES,
                format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x),
                index=0
            )
            max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
            csv_output_filename = st.sidebar.text_input("CSV Run Filename:", value="repair_run.csv")

        else: # Custom Batch
            selected_batch_domains = st.sidebar.multiselect(
                "Select Domains to Benchmark:",
                all_domains,
                default=[d for d in SELECTED_BENCHMARK_DOMAINS if d in all_domains][:5]
            )
            all_flaw_keys = list(FLAW_LABELS.keys())
            selected_batch_flaws = st.sidebar.multiselect(
                "Select Flaw Categories:",
                all_flaw_keys,
                default=all_flaw_keys[:3],
                format_func=lambda x: FLAW_LABELS.get(x, x)
            )
            batch_agents_to_run = st.sidebar.multiselect(
                "Select Architectures to Evaluate:",
                ARCHITECTURES,
                default=["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE", "UNSTRUCTURED_RETRY"],
                format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x)
            )
            max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
            csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value="repair_benchmark_results.csv")

            for d in selected_batch_domains:
                for f in selected_batch_flaws:
                    t = load_flaw_task(d, f)
                    if t:
                        batch_tasks_to_run.append(t)


# ==============================================================================
# MAIN WORKSPACE: CONTROL BAR & TRIGGER BUTTONS
# ==============================================================================
col_banner, col_trigger = st.columns([3, 1])

with col_banner:
    if exec_scope == "🎯 Single Task Run":
        if active_single_task:
            st.markdown(f"### 🎯 Task: `{active_single_task.title}`")
            st.caption(f"Source: **{dataset_source}** | Domain: **`{active_single_task.domain_family}`** | Architecture: **`{selected_single_agent}`**")
        else:
            st.warning("No active task loaded. Please select a valid domain and task from the sidebar.")
    elif exec_scope == "🏛️ Run 6 Core Domains Benchmark":
        st.markdown(f"### 🏛️ 6 Core Domains Benchmark")
        st.caption(f"Running **6 Domains** (`{', '.join(SIX_CORE_DOMAINS)}`) × **{len(batch_agents_to_run)} Architectures** = **{6 * len(batch_agents_to_run)} Runs**")
    else:
        st.markdown(f"### 📦 Batch Benchmark: `{len(batch_tasks_to_run)} Tasks` × `{len(batch_agents_to_run)} Architectures`")
        st.caption(f"Source: **{dataset_source}** | Output File: **`{csv_output_filename}`**")

with col_trigger:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if exec_scope == "🎯 Single Task Run":
        btn_label = f"🚀 Run {selected_single_agent}"
        run_single = st.button(btn_label, type="primary", use_container_width=True, disabled=(active_single_task is None))
        run_six = False
        run_batch = False
    elif exec_scope == "🏛️ Run 6 Core Domains Benchmark":
        btn_label = f"🚀 Run All 6 Core Domains"
        run_six = st.button(btn_label, type="primary", use_container_width=True, disabled=(len(batch_agents_to_run) == 0))
        run_single = False
        run_batch = False
    else:
        btn_label = f"🚀 Execute Batch Benchmark"
        run_batch = st.button(btn_label, type="primary", use_container_width=True, disabled=(len(batch_tasks_to_run) == 0 or len(batch_agents_to_run) == 0))
        run_single = False
        run_six = False


# ==============================================================================
# EXECUTION ROUTINES WITH OBSERVABILITY
# ==============================================================================
def execute_task_with_telemetry(
    task: BenchmarkTask,
    agent_type: str,
    max_iters: int,
    status_box: Optional[Any] = None
) -> Tuple[EvaluationMetrics, dict, List[dict]]:
    """Executes a single benchmark task with full phase-by-phase observability."""
    start_time = time.time()
    phase_events: List[dict] = []

    print("\n" + "=" * 80, flush=True)
    print(f" [STREAMLIT TASK START]: {task.task_id} | Domain: {task.domain_family} | Agent: {agent_type}", flush=True)
    print(f" Phase: {task.task_type.value} | Max Iterations: {max_iters}", flush=True)
    if getattr(task, "fault_category", None):
        print(f" Injected Flaw Category : {task.fault_category}", flush=True)
        print(f" Target Gold Action     : {task.gold_fault_element or 'General'}", flush=True)
    print("=" * 80 + "\n", flush=True)

    # Record Phase 1: Task Elicitation & Requirements
    phase_events.append({
        "phase": "elicit",
        "iteration": 0,
        "requirements": task.natural_language_requirements,
        "problem_pddl": task.ground_truth_problem_pddl or task.initial_problem_pddl or "",
        "note": f"Initial requirements provided for domain '{task.domain_family}' ({len(task.natural_language_requirements)} chars)."
    })

    if status_box:
        status_box.write(f"⚙️ Running Phase 1: Problem Elicitation & Requirements Setup...")

    # 1. Closed-Loop AST Agent & Ablation No-Triage
    if agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
        is_flaw = (task.task_type == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR)
        bench_probs = getattr(task, "baseline_benchmark_problems", []) or []

        initial_state = {
            "requirements": task.natural_language_requirements,
            "pddl_domain_blueprint": {},
            "initial_domain_pddl": task.initial_domain_pddl or "",
            "initial_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "reference_domain_pddl": task.ground_truth_domain_pddl or "",
            "is_synthetic_repair": is_flaw,
            "skip_elicitation": is_flaw,
            "generated_domain_pddl": task.initial_domain_pddl or "",
            "generated_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "baseline_benchmark_problems": bench_probs,
            "benchmark_problem_distribution": bench_probs,
            "verification_errors": [],
            "diagnostic_reports": [],
            "formatted_diagnostic_feedback": "",
            "iteration_count": 0,
            "max_iterations": max_iters,
            "generated_plan_result": {},
            "historical_plan_results": [],
            "skip_fault_localization": (agent_type == "ABLATION_NO_TRIAGE"),
            "system_type": agent_type
        }

        if is_flaw and task.initial_domain_pddl:
            fault_cat = task.fault_category or "SYNTAX_PARSE"
            initial_state["verification_errors"] = [f"VAL Error: Fault category {fault_cat} detected in initial model."]

        if status_box:
            status_box.write(f"🔬 Invoking LangGraph agent workflow ({agent_type})...")

        final_state = dict(initial_state)
        for output in pddl_lifecycle_graph.stream(initial_state):
            for node_name, node_update in output.items():
                if isinstance(node_update, dict):
                    final_state.update(node_update)

                if status_box:
                    if node_name == "elicit":
                        bp = node_update.get("pddl_domain_blueprint", {})
                        n_acts = len(bp.get("actions", [])) if isinstance(bp, dict) else 0
                        status_box.write(f"* **Phase 1 (Requirements Elicitation)**: Synthesized domain blueprint with {n_acts} action schema(s).")
                    elif node_name == "compile":
                        dom_p = node_update.get("generated_domain_pddl", "")
                        status_box.write(f"* **Phase 2 (AST Compilation)**: Programmatically compiled AST blueprint into PDDL ({len(dom_p)} chars).")
                    elif node_name == "validate":
                        ot = node_update.get("oracle_trace", {})
                        it = final_state.get("iteration_count", 0)
                        val_ok = ot.get("val_ok", False)
                        fd_ok = ot.get("fd_ok", False)
                        plan_steps = ot.get("plan_steps", [])
                        if val_ok and fd_ok:
                            status_box.write(f"* **Phase 3 (Oracle Validation - Iteration {it})**: Syntax Valid [PASS] | Fast Downward Plan Found ({len(plan_steps)} steps)")
                        elif val_ok:
                            status_box.write(f"* **Phase 3 (Oracle Validation - Iteration {it})**: Syntax Valid [PASS] | Fast Downward Unsolvable / Searching [INCOMPLETE]")
                        else:
                            clean_err = (ot.get("val_log") or "VAL Syntax error").strip().splitlines()[0][:100]
                            status_box.write(f"* **Phase 3 (Oracle Validation - Iteration {it})**: Syntax Rejection ({clean_err}) [FAIL]")
                    elif node_name == "fault_localization":
                        reps = node_update.get("diagnostic_reports", [])
                        if reps:
                            top_rep = reps[0]
                            target = top_rep.get("faulty_element", "domain") if isinstance(top_rep, dict) else getattr(top_rep, "faulty_element", "domain")
                            cat = top_rep.get("error_category", "Defect") if isinstance(top_rep, dict) else getattr(top_rep, "error_category", "Defect")
                            op = top_rep.get("repair_operation_type", "") if isinstance(top_rep, dict) else getattr(top_rep, "repair_operation_type", "")
                            status_box.write(f"* **Phase 4 (Hierarchical Fault Localization)**: Triaged {len(reps)} defect(s). Root cause: `{target}` ({cat}) -> Recommended Op: `{op}`.")
                        else:
                            status_box.write(f"* **Phase 4 (Hierarchical Fault Localization)**: Validation clean, no defect diagnosed.")
                    elif node_name == "repair":
                        it = final_state.get("iteration_count", 0)
                        status_box.write(f"* **Phase 5 (Targeted AST Repair - Iteration {it})**: Applied causal repair operation to action schemas.")

        exec_time = time.time() - start_time

        dom_pddl = final_state.get("generated_domain_pddl", "")
        prob_pddl = final_state.get("generated_problem_pddl", "")
        iters_used = max(1, final_state.get("iteration_count", 1))
        tot_tok = final_state.get("total_tokens", 0)
        est_cost = final_state.get("estimated_cost_usd", 0.0)
        diag_reps = final_state.get("diagnostic_reports", []) or final_state.get("historical_diagnostic_reports", [])
        err_sum = " ".join(final_state.get("verification_errors", [])) if final_state.get("verification_errors") else None

        # Record oracle traces from state
        oracle_trace = final_state.get("oracle_trace", {})
        phase_events.append({
            "phase": "validate",
            "iteration": iters_used,
            "val_ok": oracle_trace.get("val_ok", not bool(err_sum and "VAL Error" in err_sum)),
            "val_log": oracle_trace.get("val_log", ""),
            "fd_ran": oracle_trace.get("fd_ran", False),
            "fd_ok": oracle_trace.get("fd_ok", False),
            "fd_log": oracle_trace.get("fd_log", ""),
            "plan_steps": oracle_trace.get("plan_steps", []),
            "executability_valid": oracle_trace.get("executability_valid"),
            "feasibility_valid": oracle_trace.get("feasibility_valid"),
            "interpretability_valid": oracle_trace.get("interpretability_valid"),
        })

        # Record repair feedback log from state
        for rf in final_state.get("repair_feedback_log", []):
            phase_events.append({
                "phase": "fault_feedback_passed_to_llm",
                "iteration": rf.get("iteration", 1),
                "feedback_type": rf.get("feedback_source", "ast_triage"),
                "feedback_payload": rf.get("diagnostic_feedback", ""),
                "target_actions": rf.get("target_actions", []),
                "causal_context": rf.get("causal_context", ""),
                "prompt": rf.get("repair_prompt", ""),
                "model_target": "ast_blueprint"
            })

        metrics = evaluate_candidate_pddl(
            task=task,
            agent_type=agent_type,
            generated_domain_pddl=dom_pddl,
            generated_problem_pddl=prob_pddl,
            iterations_used=iters_used,
            execution_time_seconds=exec_time,
            total_tokens=tot_tok,
            estimated_cost_usd=est_cost,
            diagnostic_reports=diag_reps,
            error_summary=err_sum
        )
        if "oracle_trace" in final_state:
            final_state["oracle_trace"]["feasibility_valid"] = metrics.feasibility_valid
            final_state["oracle_trace"]["interpretability_valid"] = metrics.interpretability_valid
        final_state["phase_events"] = phase_events

        print("\n" + "=" * 80, flush=True)
        print(f" [STREAMLIT TASK COMPLETED]: {task.task_id} | Agent: {agent_type}", flush=True)
        print(f" * End-to-End Success Gate   : {'PASS [OK]' if metrics.e2e_success else 'FAIL [X]'}", flush=True)
        print(f" * SVR (Syntax Valid Rate)  : {metrics.svr_syntax_valid_rate >= 1.0}", flush=True)
        print(f" * Plan Solvable            : {metrics.is_solvable} (Plan Length: {metrics.plan_length or 'N/A'})", flush=True)
        print(f" * Executability (VAL D_gen): {metrics.executability_valid}", flush=True)
        print(f" * Feasibility (VAL D_gold) : {metrics.feasibility_valid}", flush=True)
        print(f" * Interpretability (Inv)   : {metrics.interpretability_valid}", flush=True)
        print(f" * Iterations Consumed      : {metrics.iterations_used}/{max_iters}", flush=True)
        print(f" * Execution Latency        : {exec_time:.2f}s", flush=True)
        print(f" * Total Tokens Consumed    : {tot_tok:,} (Estimated: ${est_cost:.5f})", flush=True)
        if not metrics.e2e_success and metrics.error_summary:
            print(f" * Remaining Oracle Error   : {metrics.error_summary[:160]}", flush=True)
        print("=" * 80 + "\n", flush=True)

        if status_box:
            status_box.write(f"📊 Completed validation in {exec_time:.2f}s across {iters_used} iteration(s).")
            if metrics.e2e_success:
                status_box.write("🎯 All formal criteria satisfied: Executable, Feasible, Interpretable!")
            else:
                status_box.write(f"⚠️ SVR={metrics.svr_syntax_valid_rate >= 1.0} | Solvable={metrics.is_solvable} | Feasible={metrics.feasibility_valid}")

        return metrics, final_state, phase_events

    # 2. Baselines (Unstructured Retry, Ablation No-AST, Zero-Shot)
    else:
        def _app_trace_callback(event: Dict[str, Any]) -> None:
            phase_events.append(event)
            if status_box:
                p = event.get("phase")
                it = event.get("iteration", 0)
                if p == "validate":
                    status_box.write(f"⚖️ Iteration {it}: VAL Valid={event.get('val_ok')} | Fast Downward Solvable={event.get('fd_ok')}")
                elif p == "fault_feedback_passed_to_llm":
                    status_box.write(f"🔄 Iteration {it}: Passing feedback ({event.get('feedback_type')}) back to LLM...")

        if agent_type == "UNSTRUCTURED_RETRY":
            base_res = run_unstructured_retry_baseline(task, max_retries=max_iters, on_event=_app_trace_callback)
        elif agent_type == "ABLATION_NO_AST":
            base_res = run_no_ast_ablation(task, max_retries=max_iters, on_event=_app_trace_callback)
        elif agent_type == "ZERO_SHOT":
            base_res = run_zero_shot_baseline(task, on_event=_app_trace_callback)
        else:
            raise ValueError(f"Unknown agent: {agent_type}")

        exec_time = time.time() - start_time
        dom_pddl = base_res.get("generated_domain_pddl", "")
        prob_pddl = base_res.get("generated_problem_pddl", "")
        iters_used = base_res.get("iterations_used", 1)
        tot_tok = base_res.get("total_tokens", 0)
        est_cost = base_res.get("estimated_cost_usd", 0.0)
        diag_reps = base_res.get("diagnostic_reports", [])
        err_sum = base_res.get("error")

        metrics = evaluate_candidate_pddl(
            task=task,
            agent_type=agent_type,
            generated_domain_pddl=dom_pddl,
            generated_problem_pddl=prob_pddl,
            iterations_used=iters_used,
            execution_time_seconds=exec_time,
            total_tokens=tot_tok,
            estimated_cost_usd=est_cost,
            diagnostic_reports=diag_reps,
            error_summary=err_sum
        )

        print("\n" + "=" * 80, flush=True)
        print(f" [STREAMLIT TASK COMPLETED]: {task.task_id} | Agent: {agent_type}", flush=True)
        print(f" * End-to-End Success Gate   : {'PASS [OK]' if metrics.e2e_success else 'FAIL [X]'}", flush=True)
        print(f" * SVR (Syntax Valid Rate)  : {metrics.svr_syntax_valid_rate >= 1.0}", flush=True)
        print(f" * Plan Solvable            : {metrics.is_solvable}", flush=True)
        print(f" * Executability (VAL D_gen): {metrics.executability_valid}", flush=True)
        print(f" * Feasibility (VAL D_gold) : {metrics.feasibility_valid}", flush=True)
        print(f" * Interpretability (Inv)   : {metrics.interpretability_valid}", flush=True)
        print(f" * Iterations Consumed      : {metrics.iterations_used}/{max_iters}", flush=True)
        print(f" * Execution Latency        : {exec_time:.2f}s", flush=True)
        print("=" * 80 + "\n", flush=True)

        current_state = {
            "system_type": agent_type,
            "requirements": task.natural_language_requirements,
            "generated_domain_pddl": dom_pddl,
            "generated_problem_pddl": prob_pddl,
            "initial_domain_pddl": task.initial_domain_pddl or "",
            "initial_problem_pddl": task.initial_problem_pddl or "",
            "verification_errors": [err_sum] if err_sum else [],
            "diagnostic_reports": diag_reps,
            "iteration_count": iters_used,
            "total_tokens": tot_tok,
            "estimated_cost_usd": est_cost,
            "phase_events": phase_events,
            "oracle_trace": {
                "val_ok": metrics.svr_syntax_valid_rate >= 1.0,
                "fd_ok": metrics.is_solvable,
                "executability_valid": metrics.executability_valid,
                "feasibility_valid": metrics.feasibility_valid,
                "interpretability_valid": metrics.interpretability_valid,
                "val_log": "",
                "fd_log": "",
            },
            "generated_plan_result": {
                "is_solvable": metrics.is_solvable,
                "val_plan_valid": metrics.tpv_target_plan_valid,
                "plan_length": metrics.plan_length,
                "plan_steps": []
            }
        }
        return metrics, current_state, phase_events


def metrics_to_row_dict(m: EvaluationMetrics, task: Optional[BenchmarkTask] = None, diag_reports: Optional[List[Any]] = None) -> dict:
    """Converts EvaluationMetrics into a flat dictionary covering all formal metrics."""
    return {
        "Task ID": m.task_id,
        "Domain": m.domain_family,
        "Task Type": m.task_type,
        "Architecture": m.agent_type,
        "Status": "Verified [PASS]" if m.e2e_success else "Unverified [FAIL]",
        "SVR": round(m.svr_syntax_valid_rate, 2),
        "TPV": "PASS" if m.tpv_target_plan_valid else "FAIL",
        "Executability": "Certified" if m.executability_valid else ("FAIL" if m.is_syntax_valid else "N/A"),
        "Feasibility": "PASS" if m.feasibility_valid else ("FAIL" if m.feasibility_valid is False else "N/A"),
        "Interpretability": "PASS" if m.interpretability_valid else ("FAIL" if m.interpretability_valid is False else "N/A"),
        "Plan Length": m.plan_length if m.plan_length is not None else "N/A",
        "Iterations (k)": m.iterations_used,
        "Latency (s)": round(m.execution_time_seconds, 2),
        "Cost ($)": f"${m.estimated_cost_usd:.5f}",
        "Error Summary": (m.error_summary or "")[:120]
    }


def save_metrics_to_csv_file(filename: str, rows: List[dict]):
    """Appends/writes metrics rows into designated CSV file under results/ or root."""
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    csv_path = results_dir / filename if not Path(filename).is_absolute() else Path(filename)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ------------------------------------------------------------------------------
# TRIGGER 1: RUN SINGLE TASK
# ------------------------------------------------------------------------------
if run_single and active_single_task:
    status_container = st.status(f"🚀 Running {selected_single_agent} on '{active_single_task.task_id}'...", expanded=True)
    status_container.write("Initializing symbolic environment and agent workflow...")

    try:
        metrics, final_state, events = execute_task_with_telemetry(
            active_single_task, selected_single_agent, max_iterations, status_container
        )

        saved_info = save_output_to_disk(final_state, active_single_task)
        st.session_state["last_saved_info"] = saved_info
        st.session_state["active_result"] = metrics
        st.session_state["active_state"] = final_state
        st.session_state["active_task"] = active_single_task
        st.session_state["phase_events_history"] = events

        diag_reps = final_state.get("diagnostic_reports", [])
        row = metrics_to_row_dict(metrics, active_single_task, diag_reps)
        st.session_state["results_history"].append(row)
        save_metrics_to_csv_file(csv_output_filename, st.session_state["results_history"])

        if metrics.e2e_success:
            status_container.update(label=f"[PASS] Verified Lifecycle Success! (Plan Length: {metrics.plan_length or 'N/A'}, Iters: {metrics.iterations_used})", state="complete")
        else:
            status_container.update(label=f"[FAIL] Model Unverified: {metrics.error_summary or 'Oracle checks did not fully pass.'}", state="error")

    except Exception as e:
        status_container.update(label=f"[ERROR] Execution Error: {str(e)}", state="error")
        st.error(f"Execution Error: {str(e)}")


# ------------------------------------------------------------------------------
# TRIGGER 2: RUN 6 CORE DOMAINS BENCHMARK
# ------------------------------------------------------------------------------
if run_six and batch_agents_to_run:
    total_runs = len(SIX_CORE_DOMAINS) * len(batch_agents_to_run)
    progress_bar = st.progress(0.0)
    batch_status = st.empty()
    st.info(f"🏛️ Evaluating 6 Core Domains across **{len(batch_agents_to_run)} Architectures** ({total_runs} total runs)...")
    run_idx = 0

    for domain in SIX_CORE_DOMAINS:
        if dataset_source == "AutoPlanBench (IPC Pure STRIPS)":
            task = load_autoplanbench_synthesis_task(domain, "instance-1.pddl")
        else:
            task = load_domain_synthesis_task(domain, "instance-1.pddl") or load_elicitation_task(domain)

        if not task:
            st.warning(f"Failed to load domain '{domain}', skipping.")
            continue

        for arch in batch_agents_to_run:
            run_idx += 1
            progress_bar.progress(run_idx / total_runs)
            batch_status.markdown(f"**Run [{run_idx}/{total_runs}]**: Running `{arch}` on **`{domain}`**...")

            try:
                metrics, final_state, events = execute_task_with_telemetry(task, arch, max_iterations)
                save_output_to_disk(final_state, task)

                diag_reps = final_state.get("diagnostic_reports", [])
                row = metrics_to_row_dict(metrics, task, diag_reps)
                st.session_state["results_history"].append(row)
                st.session_state["six_domains_history"].append(row)
                st.session_state["active_result"] = metrics
                st.session_state["active_state"] = final_state
                st.session_state["active_task"] = task
                st.session_state["phase_events_history"] = events

                save_metrics_to_csv_file(csv_output_filename, st.session_state["results_history"])
            except Exception as e:
                st.error(f"Run failed on '{domain}' with '{arch}': {e}")

    progress_bar.progress(1.0)
    batch_status.success(f"🎉 Completed 6 Core Domains Benchmark! Results saved to `results/{csv_output_filename}`.")


# ------------------------------------------------------------------------------
# TRIGGER 3: RUN CUSTOM BATCH BENCHMARK
# ------------------------------------------------------------------------------
if run_batch and batch_tasks_to_run and batch_agents_to_run:
    total_runs = len(batch_tasks_to_run) * len(batch_agents_to_run)
    progress_bar = st.progress(0.0)
    batch_status = st.empty()
    st.info(f"🚀 Launching Batch Benchmark across **{len(batch_tasks_to_run)} tasks** and **{len(batch_agents_to_run)} architectures**...")
    run_idx = 0

    for task in batch_tasks_to_run:
        for agent in batch_agents_to_run:
            run_idx += 1
            progress_bar.progress(run_idx / total_runs)
            batch_status.markdown(f"**Run [{run_idx}/{total_runs}]**: Evaluating `{agent}` on `{task.task_id}`...")

            try:
                metrics, final_state, events = execute_task_with_telemetry(task, agent, max_iterations)
                save_output_to_disk(final_state, task)

                diag_reps = final_state.get("diagnostic_reports", [])
                row = metrics_to_row_dict(metrics, task, diag_reps)
                st.session_state["results_history"].append(row)
                st.session_state["active_result"] = metrics
                st.session_state["active_state"] = final_state
                st.session_state["active_task"] = task
                st.session_state["phase_events_history"] = events

                save_metrics_to_csv_file(csv_output_filename, st.session_state["results_history"])
            except Exception as e:
                st.error(f"Run failed on '{task.task_id}' with '{agent}': {e}")

    progress_bar.progress(1.0)
    batch_status.success(f"🎉 Batch Benchmark Complete! Saved to `results/{csv_output_filename}`.")


# ==============================================================================
# MAIN DISPLAY TABS
# ==============================================================================
tab_results, tab_pddl, tab_phases, tab_fault_loc, tab_telemetry = st.tabs([
    "📊 Evaluation Results & Metrics",
    "📄 Generated Models & Plan Validation",
    "🔍 Phase Observability & Transparent Feedback",
    "🩺 Layered Model-Based Fault Localization",
    "⏱️ Telemetry & Cost Analytics"
])


# ==============================================================================
# TAB 1: 📊 EVALUATION RESULTS & METRICS TABLE
# ==============================================================================
with tab_results:
    st.markdown("### 📊 Benchmark Evaluation Scorecard & Comparative Matrix")
    st.caption("Standardized automated planning evaluation metrics grounded in VAL and Fast Downward symbolic oracles.")

    results_list = st.session_state.get("results_history", [])

    if not results_list:
        st.info("👈 **No benchmark runs executed yet in this session.** Select a task in the sidebar and click **'🚀 Run'** or execute **'🎓 Run 6 Core Domains'** to populate this table.")
        st.markdown("#### 📐 Supported Quantitative Metrics Reference")
        st.markdown("""
        - **SVR (Syntax Validity Rate)**: VAL parse rate (100% iff domain and problem parse without syntax or typing errors).
        - **TPV (Target Plan Validity)**: Plan validity certified by VAL on target task instance.
        - **PTS / Executability**: Internal solvability certificate (`VAL(D_gen, P_gen, pi_gen) == SUCCESS`).
        - **Feasibility (Forward Soundness)**: Physical soundness certificate on ground-truth domain (`VAL(D_gold, P_gold, pi_gen) == SUCCESS`).
        - **Interpretability (Inverse Completeness)**: Reference solvability preservation on generated domain (`VAL(D_gen, P_gold, pi_gold) == SUCCESS`).
        """)
    else:
        df_results = pd.DataFrame(results_list)
        total_runs = len(df_results)
        passed_runs = len(df_results[df_results["Status"].astype(str).str.contains("Verified")])
        pass_rate = (passed_runs / total_runs) * 100.0 if total_runs > 0 else 0.0

        numeric_iters = pd.to_numeric(df_results["Iterations (k)"], errors="coerce")
        avg_iters = numeric_iters.dropna().mean() if not numeric_iters.dropna().empty else 1.0

        numeric_svr = pd.to_numeric(df_results["SVR"], errors="coerce")
        mean_svr = numeric_svr.dropna().mean() * 100.0 if not numeric_svr.dropna().empty else 0.0

        tpv_passes = len(df_results[df_results["TPV"] == "PASS"])
        tpv_rate = (tpv_passes / total_runs * 100.0) if total_runs > 0 else 0.0

        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-title">Total Evaluated</div>
                <div class="kpi-value">{total_runs} Runs</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Verified Pass Rate</div>
                <div class="kpi-value">{pass_rate:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Mean SVR Rate</div>
                <div class="kpi-value">{mean_svr:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Mean TPV Rate</div>
                <div class="kpi-value">{tpv_rate:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Avg Iterations (k)</div>
                <div class="kpi-value">{avg_iters:.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📋 Consolidated Empirical Results Table")
        st.dataframe(df_results, use_container_width=True)

        csv_data = df_results.to_csv(index=False).encode("utf-8")
        col_dl, col_clr = st.columns([2, 1])
        with col_dl:
            st.download_button(
                label=f"📥 Download Results as CSV (`{csv_output_filename}`)",
                data=csv_data,
                file_name=csv_output_filename,
                mime="text/csv",
                type="secondary"
            )
        with col_clr:
            if st.button("🗑️ Clear Session Results", type="secondary"):
                st.session_state["results_history"] = []
                st.session_state["six_domains_history"] = []
                st.rerun()


# ==============================================================================
# TAB 2: 📄 GENERATED MODELS, PLAN VALIDATION & METRICS SCORECARD
# ==============================================================================
with tab_pddl:
    st.markdown("### 📄 Generated PDDL Models, Oracle Validation & Plan Report")
    st.caption("Inspect the compiled domain and problem files, symbolic oracle logs (VAL & Fast Downward), synthesized plan, and the complete evaluation metrics scorecard below.")

    active_state = st.session_state.get("active_state")
    active_result = st.session_state.get("active_result")
    saved_info = st.session_state.get("last_saved_info")

    if active_state:
        dom_pddl = active_state.get("generated_domain_pddl", "")
        prob_pddl = active_state.get("generated_problem_pddl", "")
        domain_bp = active_state.get("pddl_domain_blueprint", {})
        has_errors = bool(active_state.get("verification_errors", []))
        oracle_trace = active_state.get("oracle_trace", {})

        # 1. ORACLE VALIDATION BANNER & SUMMARY
        if has_errors:
            st.warning("⚠️ **Candidate Model (Unverified)**: Oracle verification did not fully pass.")
        else:
            st.success("**Verified Domain Model**: 100% syntactically valid and certified solvable by VAL & Fast Downward.")

        col_val, col_fd = st.columns(2)
        with col_val:
            st.markdown("#### 🛡️ VAL Syntax Validation Report")
            val_ok = oracle_trace.get("val_ok", not bool(has_errors and "VAL Error" in str(active_state.get("verification_errors", []))))
            if val_ok:
                st.success("VAL Syntax Check: **PASSED (Exit Code: 0)**")
            else:
                st.error("VAL Syntax Check: **FAILED**")
            val_log = oracle_trace.get("val_log") or "\n".join(active_state.get("verification_errors", []))
            with st.expander("Show Raw VAL Validator Log", expanded=not val_ok):
                st.code(val_log or "No syntax warnings reported.", language="text")

        with col_fd:
            st.markdown("#### ⚡ Fast Downward Solvability Report")
            plan_res = active_state.get("generated_plan_result") or {}
            fd_ok = oracle_trace.get("fd_ok", plan_res.get("is_solvable", False))
            if fd_ok:
                p_len = plan_res.get("plan_length", len(plan_res.get("plan_steps", [])))
                st.success(f"Fast Downward Search: **PLAN FOUND ({p_len} steps)**")
            else:
                st.error("Fast Downward Search: **NO PLAN FOUND / UNSOLVABLE**")
            fd_log = oracle_trace.get("fd_log") or plan_res.get("raw_fd_log", "")
            with st.expander("Show Raw Fast Downward Log", expanded=not fd_ok):
                st.code(fd_log or "Solver log not captured.", language="text")

        if saved_info:
            s_name, s_idx, s_dom, s_prob = saved_info[:4]
            clean_dom_path = os.path.relpath(s_dom).replace("\\", "/")
            st.caption(f"💾 Saved to local disk: `{clean_dom_path}`")

        # 2. GENERATED DOMAIN CODE
        st.markdown("---")
        st.markdown("#### `domain.pddl` (Generated / Repaired)")
        st.code(dom_pddl, language="lisp")

        with st.expander("Domain Blueprint AST (JSON)", expanded=False):
            st.json(domain_bp if domain_bp else {"info": "Blueprint empty or generated via direct text baseline."})

        # 3. GENERATED PROBLEM CODE
        st.markdown("#### `problem.pddl`")
        st.code(prob_pddl, language="lisp")

        # 4. SYNTHESIZED CLASSICAL PLAN
        if plan_res and plan_res.get("is_solvable") and plan_res.get("plan_steps"):
            st.markdown("---")
            st.markdown("#### 📋 Synthesized Classical Plan (`sas_plan`)")
            p_len = plan_res.get("plan_length", len(plan_res["plan_steps"]))
            p_time = plan_res.get("search_time", 0.0)
            st.caption(f"Plan Length: **{p_len} steps** | Fast Downward Search Time: **{p_time:.4f}s** | VAL Certificate: **Valid 🛡️**")

            steps = plan_res["plan_steps"]
            formatted_steps = [{"Step": i, "Action Schema & Grounded Parameters": s} for i, s in enumerate(steps, 1)]
            st.dataframe(formatted_steps, use_container_width=True)

        # 5. ALL METRICS OUTPUT PRINTED CLEARLY BELOW (AS REQUESTED)
        if active_result:
            st.markdown("---")
            st.markdown("### 🏆 Comprehensive Evaluation Metrics Scorecard")
            st.caption("Formal Tri-Criteria Semantic Verification and Structural F1 Alignment metrics calculated on the final model.")

            m = active_result
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            col_m1.metric("SVR (Syntax)", f"{m.svr_syntax_valid_rate * 100.0:.0f}%")
            col_m2.metric("TPV (Plan Valid)", "PASS" if m.tpv_target_plan_valid else "FAIL")
            col_m3.metric("Executability", "PASS" if m.executability_valid else ("FAIL" if m.is_syntax_valid else "N/A"))
            col_m4.metric("Feasibility", "PASS" if m.feasibility_valid else ("FAIL" if m.feasibility_valid is False else "N/A"))
            col_m5.metric("Interpretability", "PASS" if m.interpretability_valid else ("FAIL" if m.interpretability_valid is False else "N/A"))

            col_len, col_it, col_lat, col_cost = st.columns(4)
            col_len.metric("Plan Length", f"{m.plan_length} steps" if m.plan_length is not None else "N/A")
            col_it.metric("Iterations (k)", f"{m.iterations_used}")
            col_lat.metric("Latency", f"{m.execution_time_seconds:.2f}s")
            col_cost.metric("Estimated Cost", f"${m.estimated_cost_usd:.5f}")

            metrics_table = [
                {"Metric": "SVR (Syntax Validity Rate)", "Value": f"{m.svr_syntax_valid_rate * 100.0:.1f}%", "Formal Criterion": "VAL Syntax Check"},
                {"Metric": "TPV (Target Plan Validity)", "Value": "PASS" if m.tpv_target_plan_valid else "FAIL", "Formal Criterion": "VAL Plan Validator"},
                {"Metric": "Internal Solvability (Executability)", "Value": "PASS" if m.executability_valid else "FAIL", "Formal Criterion": "VAL(D_gen, P_gen, pi_gen)"},
                {"Metric": "Forward Soundness (Feasibility)", "Value": "PASS" if m.feasibility_valid else ("FAIL" if m.feasibility_valid is False else "N/A"), "Formal Criterion": "VAL(D_gold, P_gold, pi_gen)"},
                {"Metric": "Inverse Completeness (Interpretability)", "Value": "PASS" if m.interpretability_valid else ("FAIL" if m.interpretability_valid is False else "N/A"), "Formal Criterion": "VAL(D_gen, P_gold, pi_gold)"},
                {"Metric": "Repair Iterations Used", "Value": f"{m.iterations_used}", "Formal Criterion": "Convergence Speed (k)"},
                {"Metric": "Execution Wall Time", "Value": f"{m.execution_time_seconds:.2f} seconds", "Formal Criterion": "Latency"},
                {"Metric": "API Token Consumption", "Value": f"{m.total_tokens:,} tokens", "Formal Criterion": "Compute Cost"},
            ]
            st.dataframe(metrics_table, use_container_width=True)

    else:
        st.info("👈 Run a task to inspect the generated domain, problem, validation report, and metrics scorecard here.")


# ==============================================================================
# TAB 3: 🔍 PHASE OBSERVABILITY & TRANSPARENT FEEDBACK LOOP
# ==============================================================================
with tab_phases:
    st.markdown("### 🔍 Phase-by-Phase Observability & Transparent Feedback Loop")
    st.caption("Complete breakdown of what was produced in each lifecycle phase and exactly what error feedback was passed back to the model/AST.")

    active_state = st.session_state.get("active_state")
    events = st.session_state.get("phase_events_history", [])
    active_agent = (active_state.get("system_type") if active_state else None) or selected_single_agent

    # 1. High-Level Mode Feedback Mechanism Card
    fb_meta = FEEDBACK_EXPLANATIONS.get(active_agent, FEEDBACK_EXPLANATIONS["CLOSED_LOOP_AST_AGENT"])
    st.markdown(f"""
    <div style="background-color: #F0F4F8; border-left: 5px solid #1976D2; padding: 1rem; border-radius: 6px; margin-bottom: 1.2rem;">
        <h4 style="margin: 0; color: #0D47A1;">🔄 Feedback Loop Policy: <code>{active_agent}</code></h4>
        <p style="margin: 0.4rem 0 0.2rem 0; font-size: 0.95rem;"><strong>Mechanism</strong>: {fb_meta['mechanism']}</p>
        <p style="margin: 0; font-size: 0.92rem; color: #37474F;"><strong>Target Representation Handled by Model</strong>: <code>{fb_meta['target']}</code></p>
    </div>
    """, unsafe_allow_html=True)

    if active_state:
        # Phase 1: Requirements & Elicitation
        with st.expander("🌿 Phase 1: Natural Language Requirements & Problem Instance", expanded=True):
            req_str = active_state.get("requirements", "")
            st.markdown(f"**Natural Language Specification ({len(req_str)} chars):**")
            st.code(req_str[:1500] + ("..." if len(req_str) > 1500 else ""), language="text")
            prob_str = active_state.get("initial_problem_pddl") or active_state.get("generated_problem_pddl", "")
            if prob_str:
                st.markdown("**Target Problem Instance (`problem.pddl`):**")
                st.code(prob_str, language="lisp")

        # Phase 2: Compilation & Generated Artifact
        with st.expander("⚙️ Phase 2: Domain Compilation & Generated Artifact", expanded=False):
            dom_code = active_state.get("generated_domain_pddl", "")
            st.markdown("**Compiled Domain Definition (`domain.pddl`):**")
            st.code(dom_code[:1200] + ("..." if len(dom_code) > 1200 else ""), language="lisp")

        # Phase 3: Symbolic Oracle Checks
        with st.expander("⚖️ Phase 3: Symbolic Oracle Checks (VAL & Fast Downward)", expanded=True):
            trace = active_state.get("oracle_trace", {})
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**VAL Syntax Oracle:**")
                st.write(f"- Status: `{'PASSED' if trace.get('val_ok') else 'FAILED'}`")
                if trace.get("val_log"):
                    st.code(trace["val_log"][:600], language="text")
            with c2:
                st.markdown("**Fast Downward Solver Oracle:**")
                st.write(f"- Status: `{'SOLVABLE' if trace.get('fd_ok') else 'UNSOLVABLE'}`")
                st.write(f"- Plan Steps: `{len(trace.get('plan_steps', []))}`")
                if trace.get("fd_log"):
                    st.code(trace["fd_log"][:600], language="text")

        # Phase 4: Diagnostic Triage / Fault Localization
        with st.expander("🩺 Phase 4: Model-Based Diagnostic Triage & Causal Analysis", expanded=True):
            diag_reports = active_state.get("historical_diagnostic_reports", []) or active_state.get("diagnostic_reports", [])
            fmt_diag = active_state.get("formatted_diagnostic_feedback", "")
            if diag_reports:
                st.markdown(f"**{len(diag_reports)} Diagnostic Issues Triaged:**")
                for i, r in enumerate(diag_reports, 1):
                    cat = r.get("error_category") if isinstance(r, dict) else getattr(r, "error_category", "UNKNOWN")
                    op = r.get("repair_operation_type") if isinstance(r, dict) else getattr(r, "repair_operation_type", "GENERAL")
                    el = r.get("faulty_element") if isinstance(r, dict) else getattr(r, "faulty_element", "General")
                    hint = r.get("suggested_repair_hint") if isinstance(r, dict) else getattr(r, "suggested_repair_hint", "")
                    st.markdown(f"- **Issue #{i}**: Category=`{cat}` | Target Action=`{el}` | Operation=`{op}`")
                    if hint:
                        st.info(f"Hint: {hint}")
            elif fmt_diag:
                st.markdown("**Diagnostic Feedback:**")
                st.code(fmt_diag[:800], language="text")
            else:
                st.success("Zero diagnostic errors found in the final model.")

        # Phase 5: Transparent Feedback Loop - What was Passed Back
        with st.expander("🔄 Phase 5: Transparent Feedback Passed Back to the Model / AST", expanded=True):
            st.markdown(f"#### 🔍 What was given back to `{active_agent}`:")

            # Check if Closed-Loop Agent feedback log exists
            rf_log = active_state.get("repair_feedback_log", [])
            fb_events = [e for e in events if e.get("phase") == "fault_feedback_passed_to_llm"]

            if rf_log:
                st.markdown(f"Found **{len(rf_log)} Repair Iteration Logs** in agent state:")
                for entry in rf_log:
                    it = entry.get("iteration", 1)
                    src = entry.get("feedback_source", "ast_triage")
                    targets = entry.get("target_actions", [])
                    fb_text = entry.get("diagnostic_feedback", "")
                    prompt_text = entry.get("repair_prompt", "")

                    st.markdown(f"##### 🔁 Iteration {it} Feedback Package:")
                    st.markdown(f"- **Feedback Source**: `{src}`")
                    st.markdown(f"- **Target Actions for Surgical Repair**: `{targets}`")
                    st.markdown("**Diagnostic Feedback Text Injected into Prompt:**")
                    st.code(str(fb_text), language="text")
                    if prompt_text:
                        with st.expander(f"Inspect Full LLM Repair Prompt (Iteration {it})", expanded=False):
                            st.code(prompt_text, language="text")

            elif fb_events:
                st.markdown(f"Found **{len(fb_events)} Feedback Events** recorded during baseline execution:")
                for fe in fb_events:
                    it = fe.get("iteration", 1)
                    fb_type = fe.get("feedback_type", "raw_trace")
                    payload = fe.get("feedback_payload", "")
                    prompt = fe.get("prompt", "")

                    st.markdown(f"##### 🔁 Iteration {it} Feedback Package:")
                    st.markdown(f"- **Feedback Type**: `{fb_type}`")
                    st.markdown(f"- **Model Target**: `{fe.get('model_target', 'pddl_text')}`")
                    st.markdown("**Feedback Payload Delivered to Model:**")
                    st.code(str(payload), language="text")
                    if prompt:
                        with st.expander(f"Inspect Full Baseline Prompt (Iteration {it})", expanded=False):
                            st.code(prompt, language="text")
            else:
                if active_agent == "ZERO_SHOT":
                    st.info("🎯 **Zero-Shot Baseline**: Single generation pass. Strictly zero feedback is passed back to the model.")
                else:
                    st.info("Domain model was solved on iteration 1 without needing a repair feedback pass.")

    else:
        st.info("👈 Run a task to observe the phase-by-phase trace and feedback payloads here.")


# ==============================================================================
# TAB 4: 🩺 LAYERED MODEL-BASED FAULT LOCALIZATION
# ==============================================================================
with tab_fault_loc:
    st.markdown("### 🩺 Layered Model-Based Fault Localization & Causal Diagnostics")
    st.caption("Deep causal invariant analysis (Torralba & Hoffmann DTG invariants) and structured diagnostic items.")

    active_state = st.session_state.get("active_state")
    if active_state:
        init_errors = active_state.get("initial_verification_errors", []) or active_state.get("verification_errors", [])
        reports = active_state.get("historical_diagnostic_reports", []) or active_state.get("diagnostic_reports", [])

        from tools.causal_fault_analyzer import run_causal_fault_analysis
        d_bp = active_state.get("pddl_domain_blueprint") or {}
        p_pddl = active_state.get("initial_problem_pddl") or active_state.get("generated_problem_pddl") or ""
        causal_data = active_state.get("causal_graph_analysis")
        if not causal_data and d_bp and d_bp.get("actions"):
            causal_data = run_causal_fault_analysis(d_bp, p_pddl, init_errors)

        if causal_data and causal_data.get("diagnostic_summary"):
            with st.expander("🕸️ Causal Graph & DTG Structural Diagnostics (Invariants Analysis)", expanded=True):
                st.code(causal_data.get("diagnostic_summary"), language="text")

        if init_errors:
            st.markdown("#### 🚨 Captured Oracle Diagnostic Error Output (Prior to Repair)")
            for err_idx, err_text in enumerate(init_errors, 1):
                first_line = err_text.strip().split("\n")[0][:120]
                with st.expander(f"⚠️ Raw Oracle Error #{err_idx}: {first_line}...", expanded=False):
                    st.code(err_text, language="text")

        if reports:
            st.markdown("#### 📌 Structured Diagnostic Fault Localization Items")
            for idx, r in enumerate(reports, 1):
                if isinstance(r, dict):
                    err_cat = r.get("error_category", "UNKNOWN")
                    op_type = r.get("repair_operation_type", "GENERAL")
                    element = r.get("faulty_element", "General")
                    hint = r.get("suggested_repair_hint", "")
                    raw_log = r.get("raw_log", "")
                else:
                    err_cat = getattr(r, "error_category", "UNKNOWN")
                    op_type = getattr(r, "repair_operation_type", "GENERAL")
                    element = getattr(r, "faulty_element", "General")
                    hint = getattr(r, "suggested_repair_hint", "")
                    raw_log = getattr(r, "raw_log", "")

                with st.expander(f"Issue #{idx}: [{err_cat}] - Faulty Action/Element: '{element or 'General'}'", expanded=True):
                    st.markdown(f"- **Target AST Operation**: `{op_type}`")
                    if hint:
                        st.info(f"**Actionable Repair Hint**: {hint}")
                    if raw_log:
                        st.markdown("**Solver / Validator Error Trace:**")
                        st.code(raw_log, language="text")
        elif not init_errors:
            st.success("🎉 Zero diagnostic issues found! Domain and problem models verified cleanly.")
    else:
        st.info("👈 Run a task to inspect diagnostic fault localization feedback.")


# ==============================================================================
# TAB 5: ⏱️ TELEMETRY & COST ANALYTICS
# ==============================================================================
with tab_telemetry:
    st.markdown("### ⚡ LLM Execution Telemetry & Cost Analytics")
    st.caption("Token consumption, estimated API cost, and per-node execution latencies.")

    active_state = st.session_state.get("active_state")
    if active_state:
        tot_tok = active_state.get("total_tokens", 0)
        prompt_tok = active_state.get("total_prompt_tokens", 0)
        comp_tok = active_state.get("total_completion_tokens", 0)
        est_cost = active_state.get("estimated_cost_usd", 0.0)

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total Tokens", f"{tot_tok:,}")
        t2.metric("Prompt Tokens", f"{prompt_tok:,}")
        t3.metric("Completion Tokens", f"{comp_tok:,}")
        t4.metric("Estimated Cost", f"${est_cost:.5f}")

        node_lat = active_state.get("node_latencies", {})
        if node_lat:
            st.markdown("---")
            st.markdown("#### ⏱️ Per-Node Execution Latency Breakdown")
            st.dataframe([
                {"Node": "Node 1: Elicitation (LLM)", "Latency (s)": f"{node_lat.get('elicit', 0.0):.3f}s"},
                {"Node": "Node 2: Deterministic Compiler (Python)", "Latency (s)": f"{node_lat.get('generate', 0.0):.3f}s"},
                {"Node": "Node 3: Symbolic Oracles (VAL & FD)", "Latency (s)": f"{node_lat.get('validate', 0.0):.3f}s"},
                {"Node": "Node 4: FaultLocalizationNode (LLM Agent)", "Latency (s)": f"{node_lat.get('fault_localization', 0.0):.3f}s"},
                {"Node": "Node 5: Targeted AST Repair (LLM)", "Latency (s)": f"{node_lat.get('repair', 0.0):.3f}s"},
            ], use_container_width=True)
    else:
        st.info("👈 Run a task or benchmark to view telemetry metrics.")
