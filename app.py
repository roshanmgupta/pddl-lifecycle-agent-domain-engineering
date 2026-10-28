import sys
from pathlib import Path

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
    get_temp_gt_domain_path,
    get_temp_eval_plan_path,
    get_flaw_output_dir,
    get_evolve_output_dir,
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
    list_domain_evolutions,
    load_evolution_task,
    load_elicitation_task,
    SELECTED_BENCHMARK_DOMAINS,
)
from eval.metrics import EvaluationMetrics
from eval.benchmark_runner import evaluate_candidate_pddl, run_evaluation_on_task, compute_fault_localization_metrics
from eval.baselines import (
    run_zero_shot_baseline,
    run_unstructured_retry_baseline,
    run_no_ast_ablation,
)
from graph import pddl_lifecycle_graph
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness,
)
from eval.action_reconstruction import evaluate_action_reconstruction

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
    .stCodeBlock {
        border-radius: 8px;
    }
    [data-testid="stSidebar"] pre {
        max-height: 350px !important;
        overflow-y: auto !important;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Helper Functions: Benchmark & Disk Persistence
# ==============================================================================
def list_domain_problems(domain_name: str) -> List[str]:
    """Lists problem instance files (.pddl) in PDDLLifeCycleBench/<domain>/orig_problems/."""
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
    """
    Saves compiled domain.pddl, problem.pddl, blueprint.json, diagnostic_report.json, and plan.txt
    into track-specific benchmark output directories with auto-incrementing indices.
    """
    domain_bp = state.get("pddl_domain_blueprint", {})
    if isinstance(domain_bp, dict):
        d_name = domain_bp.get("domain_name", "generated_domain")
    else:
        d_name = getattr(domain_bp, "domain_name", "generated_domain")
        
    d_name = re.sub(r'[^a-zA-Z0-9_\-]', '', str(d_name)).lower() or "generated_domain"

    is_flaw = state.get("is_synthetic_repair", False)
    is_evolve = state.get("is_evolution_task", False)
    if task:
        tt = getattr(task, "task_type", None)
        if tt == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR or getattr(tt, "value", "") == "SYNTHETIC_FAULT_REPAIR":
            is_flaw = True
        elif tt == LifecycleTaskType.DOMAIN_EVOLUTION or getattr(tt, "value", "") == "DOMAIN_EVOLUTION":
            is_evolve = True

    if is_flaw:
        base_dir = str(get_flaw_output_dir())
    elif is_evolve:
        base_dir = str(get_evolve_output_dir())
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
if "last_saved_info" not in st.session_state:
    st.session_state["last_saved_info"] = None


# ==============================================================================
# Header
# ==============================================================================
st.markdown('<div class="main-header">🧠 Autonomous PDDL Domain Lifecycle Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Closed-Loop AST Domain Synthesis, Layered Model-Based Fault Localization & Surgical Repair, and Continuous Evolution (Classical STRIPS PDDL 2.1)</div>', unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR CONFIGURATION CONTROLS
# ==============================================================================
st.sidebar.title("⚙️ Lifecycle Architecture Controls")

# 1. Operating Modality
selected_mode = st.sidebar.radio(
    "Operating Modality:",
    options=[
        "🌿 Direct NL Domain Synthesis",
        "🔧 Faulty Domain Repair",
        "🚀 Continuous Domain Evolution"
    ],
    index=0,
    help="Select which lifecycle engineering phase to execute."
)

# 2. Execution Scope (Single vs Batch)
exec_scope = st.sidebar.radio(
    "Execution Scope:",
    options=["🎯 Single Task Run", "📦 Batch Benchmark Run"],
    index=0,
    help="Run an individual task interactively with live telemetry, or execute a batch benchmark."
)

st.sidebar.markdown("---")

# Canonical 24 Domains from PDDLLifeCycleBench
all_domains = list_benchmark_domains()
if not all_domains:
    all_domains = SELECTED_BENCHMARK_DOMAINS

# Architectures available
ARCHITECTURES = [
    "CLOSED_LOOP_AST_AGENT",
    "ABLATION_NO_TRIAGE",
    "ABLATION_NO_AST",
    "UNSTRUCTURED_RETRY",
    "ZERO_SHOT"
]

ARCH_DESCRIPTIONS = {
    "CLOSED_LOOP_AST_AGENT": "🧠 Closed-Loop AST Agent (FaultLocalizationNode + Surgical AST)",
    "ABLATION_NO_TRIAGE": "🔬 Ablation: No Fault Localization (AST Blueprint + Raw Trace Errors)",
    "ABLATION_NO_AST": "🔬 Ablation: No AST (Direct PDDL Text + Fault Localization)",
    "UNSTRUCTURED_RETRY": "⚡ Baseline: Unstructured Retry (Direct PDDL + Raw Trace Errors)",
    "ZERO_SHOT": "🎯 Baseline: Zero-Shot (Direct PDDL, No Feedback Loop)"
}

# Mode-Specific Sidebar Controls
active_single_task: Optional[BenchmarkTask] = None
batch_tasks_to_run: List[BenchmarkTask] = []
batch_agents_to_run: List[str] = ["CLOSED_LOOP_AST_AGENT"]
selected_single_agent: str = "CLOSED_LOOP_AST_AGENT"
max_iterations: int = 5
csv_output_filename: str = "benchmark_results.csv"

# ------------------------------------------------------------------------------
# MODALITY 1: DIRECT NL DOMAIN SYNTHESIS
# ------------------------------------------------------------------------------
if selected_mode == "🌿 Direct NL Domain Synthesis":
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
            
        enable_regression = st.sidebar.checkbox(
            "Verify Phase 4 Historical Regression Suite",
            value=False,
            help="Evaluate solvability preservation across historical instances."
        )
        if enable_regression and avail_problems and active_single_task:
            chosen_hist = st.sidebar.multiselect(
                "Historical Problems (P_1, ..., P_k):",
                avail_problems,
                default=[p for p in avail_problems if p != sel_prob][:3]
            )
            hist_pddls = []
            for hp in chosen_hist:
                hp_path = get_benchmark_dir() / sel_domain / "orig_problems" / hp
                if hp_path.exists():
                    hist_pddls.append(hp_path.read_text(encoding="utf-8"))
            active_single_task.baseline_benchmark_problems = hist_pddls

        selected_single_agent = st.sidebar.selectbox(
            "Select Architecture:",
            ARCHITECTURES,
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x),
            index=0
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Run / Output Filename:", value="synthesis_run.csv")

    else: # Batch Run
        st.sidebar.markdown("#### 📦 Batch Domain Selection")
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

# ------------------------------------------------------------------------------
# MODALITY 2: FAULTY DOMAIN REPAIR
# ------------------------------------------------------------------------------
elif selected_mode == "🔧 Faulty Domain Repair":
    st.sidebar.markdown("### 🔧 Synthetic Fault Repair Settings")
    default_csv = "repair_benchmark_results.csv"

    FLAW_LABELS = {
        "flaw_01_syntax_declaration_error": "Flaw 1: Type Signature & Arity Inversion",
        "flaw_02_precondition_misalignment": "Flaw 2: Precondition Misalignment",
        "flaw_03_action_effect_deletion": "Flaw 3: Action Effect Deletion",
        "flaw_04_initial_goal_deadlock": "Flaw 4: Initial / Goal Deadlock",
        "flaw_05_state_reachability_collapse": "Flaw 5: State Reachability Collapse"
    }

    if exec_scope == "🎯 Single Task Run":
        sel_domain = st.sidebar.selectbox("Choose Canonical Domain:", all_domains, index=0)
        avail_flaws = list_domain_flaws(sel_domain)
        if not avail_flaws:
            avail_flaws = list(FLAW_LABELS.keys())
            
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
        csv_output_filename = st.sidebar.text_input("CSV Run / Output Filename:", value="repair_run.csv")

    else: # Batch Run
        st.sidebar.markdown("#### 📦 Batch Flaw Selection")
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
        csv_output_filename = st.sidebar.text_input("CSV Output Filename:", value=default_csv)

        for d in selected_batch_domains:
            for f in selected_batch_flaws:
                t = load_flaw_task(d, f)
                if t:
                    batch_tasks_to_run.append(t)

# ------------------------------------------------------------------------------
# MODALITY 3: CONTINUOUS DOMAIN EVOLUTION
# ------------------------------------------------------------------------------
else:
    st.sidebar.markdown("### 🚀 Domain Evolution Settings")
    default_csv = "evolution_benchmark_results.csv"

    EVO_LABELS = {
        "evolution_01_feature_addition": "Evolution 1: New Capability Feature Addition",
        "evolution_02_composite_action": "Evolution 2: Composite Macro Action"
    }

    if exec_scope == "🎯 Single Task Run":
        sel_domain = st.sidebar.selectbox("Choose Canonical Domain:", all_domains, index=0)
        avail_evos = list_domain_evolutions(sel_domain)
        if not avail_evos:
            avail_evos = list(EVO_LABELS.keys())
            
        sel_evo = st.sidebar.selectbox(
            "Choose Evolution Task:",
            avail_evos,
            format_func=lambda x: EVO_LABELS.get(x, x),
            index=0
        )
        active_single_task = load_evolution_task(sel_domain, sel_evo)
        if active_single_task:
            hist_count = len(active_single_task.baseline_benchmark_problems or [])
            st.sidebar.info(
                f"**Evolution Category**: `{sel_evo}`\n\n"
                f"**Historical Regression Suite**: `{hist_count} problem instances`"
            )

        selected_single_agent = st.sidebar.selectbox(
            "Select Architecture:",
            ARCHITECTURES,
            format_func=lambda x: ARCH_DESCRIPTIONS.get(x, x),
            index=0
        )
        max_iterations = st.sidebar.slider("Max Iterations (k):", 1, 10, value=5)
        csv_output_filename = st.sidebar.text_input("CSV Run / Output Filename:", value="evolution_run.csv")

    else: # Batch Run
        st.sidebar.markdown("#### 📦 Batch Evolution Selection")
        selected_batch_domains = st.sidebar.multiselect(
            "Select Evolution Domains:",
            all_domains,
            default=[d for d in ["blocksworld", "logistics", "pipesworld-notankage04-bfs", "depot", "satellite", "gripper"] if d in all_domains]
        )
        all_evo_keys = list(EVO_LABELS.keys())
        selected_batch_evos = st.sidebar.multiselect(
            "Select Evolution Tasks:",
            all_evo_keys,
            default=all_evo_keys[:1],
            format_func=lambda x: EVO_LABELS.get(x, x)
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
            for e in selected_batch_evos:
                t = load_evolution_task(d, e)
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
            st.caption(f"Domain Family: **`{active_single_task.domain_family}`** | Task Type: **`{active_single_task.task_type.value}`** | Architecture: **`{selected_single_agent}`**")
        else:
            st.warning("No active task loaded. Please select a valid domain and task from the sidebar.")
    else:
        st.markdown(f"### 📦 Batch Benchmark: `{len(batch_tasks_to_run)} Tasks` × `{len(batch_agents_to_run)} Architectures` = `{len(batch_tasks_to_run) * len(batch_agents_to_run)} Total Runs`")
        st.caption(f"Operating Modality: **{selected_mode}** | Output File: **`{csv_output_filename}`**")

with col_trigger:
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    if exec_scope == "🎯 Single Task Run":
        btn_label = f"🚀 Run {selected_single_agent}"
        run_single = st.button(btn_label, type="primary", use_container_width=True, disabled=(active_single_task is None))
        run_batch = False
    else:
        btn_label = f"🚀 Execute Batch Benchmark"
        run_batch = st.button(btn_label, type="primary", use_container_width=True, disabled=(len(batch_tasks_to_run) == 0 or len(batch_agents_to_run) == 0))
        run_single = False


# ==============================================================================
# EXECUTION ROUTINES (SINGLE & BATCH)
# ==============================================================================
def execute_task_with_telemetry(task: BenchmarkTask, agent_type: str, max_iters: int) -> Tuple[EvaluationMetrics, dict]:
    """Executes a single benchmark task, captures telemetry, evaluates formal metrics, and saves artifacts."""
    start_time = time.time()
    
    # 1. Closed-Loop AST Agent & Ablation No-Triage
    if agent_type in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
        is_flaw = (task.task_type == LifecycleTaskType.SYNTHETIC_FAULT_REPAIR)
        is_evolve = (task.task_type == LifecycleTaskType.DOMAIN_EVOLUTION)
        
        bench_probs = getattr(task, "baseline_benchmark_problems", []) or getattr(task, "historical_regression_problems", []) or []

        initial_state = {
            "requirements": task.natural_language_requirements,
            "pddl_domain_blueprint": {},
            "initial_domain_pddl": task.initial_domain_pddl or "",
            "initial_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "is_evolution_task": is_evolve,
            "is_synthetic_repair": is_flaw,
            "skip_elicitation": is_flaw,
            "generated_domain_pddl": task.initial_domain_pddl or "",
            "generated_problem_pddl": task.initial_problem_pddl or task.ground_truth_problem_pddl or "",
            "evolution_target_problem_pddl": task.evolution_target_problem_pddl if is_evolve else None,
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

        final_state = pddl_lifecycle_graph.invoke(initial_state)
        exec_time = time.time() - start_time
        
        dom_pddl = final_state.get("generated_domain_pddl", "")
        prob_pddl = final_state.get("generated_problem_pddl", "")
        iters_used = max(1, final_state.get("iteration_count", 1))
        tot_tok = final_state.get("total_tokens", 0)
        est_cost = final_state.get("estimated_cost_usd", 0.0)
        diag_reps = final_state.get("diagnostic_reports", []) or final_state.get("historical_diagnostic_reports", [])
        err_sum = " ".join(final_state.get("verification_errors", [])) if final_state.get("verification_errors") else None

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
        return metrics, final_state

    # 2. Baselines (Unstructured Retry, Ablation No-AST, Zero-Shot)
    else:
        if agent_type == "UNSTRUCTURED_RETRY":
            base_res = run_unstructured_retry_baseline(task, max_retries=max_iters)
        elif agent_type == "ABLATION_NO_AST":
            base_res = run_no_ast_ablation(task, max_retries=max_iters)
        elif agent_type == "ZERO_SHOT":
            base_res = run_zero_shot_baseline(task)
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
        }

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
        return metrics, current_state


def metrics_to_row_dict(m: EvaluationMetrics, task: Optional[BenchmarkTask] = None, diag_reports: Optional[List[Any]] = None) -> dict:
    """Converts EvaluationMetrics into a flat dictionary covering all formal metrics."""
    fla_top1 = None
    if task and task.gold_fault_element and diag_reports:
        top1, _, _ = compute_fault_localization_metrics(task.gold_fault_element, diag_reports)
        fla_top1 = top1

    return {
        "Task ID": m.task_id,
        "Domain": m.domain_family,
        "Task Type": m.task_type,
        "Architecture": m.agent_type,
        "Status": "Verified ✅" if m.e2e_success else "Unverified ⚠️",
        "Behavioral Code": m.behavioral_code or ("S.1" if m.e2e_success else "S.T"),
        "SVR": round(m.svr_syntax_valid_rate, 2),
        "TPV": "PASS" if m.tpv_target_plan_valid else "FAIL",
        "PTS": "Certified" if m.executability_valid else ("FAIL" if m.is_syntax_valid else "N/A"),
        "FLA Top-1": ("PASS" if fla_top1 else "FAIL") if fla_top1 is not None else "N/A",
        "Macro F1": round(m.macro_structural_f1, 4) if m.macro_structural_f1 is not None else "N/A",
        "Pre F1": round(m.precondition_f1, 4) if m.precondition_f1 is not None else "N/A",
        "Add F1": round(m.add_effect_f1, 4) if m.add_effect_f1 is not None else "N/A",
        "Del F1": round(m.delete_effect_f1, 4) if m.delete_effect_f1 is not None else "N/A",
        "Cov_ref (%)": f"{m.cov_ref_coverage_rate:.1f}%" if m.cov_ref_coverage_rate is not None else "N/A",
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
        metrics, final_state = execute_task_with_telemetry(active_single_task, selected_single_agent, max_iterations)
        
        # Save output to disk
        saved_info = save_output_to_disk(final_state, active_single_task)
        st.session_state["last_saved_info"] = saved_info
        st.session_state["active_result"] = metrics
        st.session_state["active_state"] = final_state
        
        # Record into results history
        diag_reps = final_state.get("diagnostic_reports", [])
        row = metrics_to_row_dict(metrics, active_single_task, diag_reps)
        st.session_state["results_history"].append(row)
        
        # Auto-save to CSV
        save_metrics_to_csv_file(csv_output_filename, st.session_state["results_history"])
        
        if metrics.e2e_success:
            status_container.update(label=f"✅ Verified Lifecycle Success! (Plan Length: {metrics.plan_length or 'N/A'}, Iters: {metrics.iterations_used})", state="complete")
        else:
            status_container.update(label=f"⚠️ Model Unverified: {metrics.error_summary or 'Oracle checks did not fully pass.'}", state="error")

    except Exception as e:
        status_container.update(label=f"❌ Execution Error: {str(e)}", state="error")
        st.error(f"Execution Error: {str(e)}")


# ------------------------------------------------------------------------------
# TRIGGER 2: RUN BATCH BENCHMARK
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
            progress_frac = run_idx / total_runs
            batch_status.markdown(f"**Run [{run_idx}/{total_runs}]**: Evaluating `{agent}` on `{task.task_id}`...")
            progress_bar.progress(progress_frac)
            
            try:
                metrics, final_state = execute_task_with_telemetry(task, agent, max_iterations)
                save_output_to_disk(final_state, task)
                
                diag_reps = final_state.get("diagnostic_reports", [])
                row = metrics_to_row_dict(metrics, task, diag_reps)
                st.session_state["results_history"].append(row)
                st.session_state["active_result"] = metrics
                st.session_state["active_state"] = final_state
                
                # Write after each run
                save_metrics_to_csv_file(csv_output_filename, st.session_state["results_history"])
            except Exception as e:
                st.error(f"Run failed on '{task.task_id}' with '{agent}': {e}")
                
    progress_bar.progress(1.0)
    batch_status.success(f"🎉 Batch Benchmark Complete! Evaluated {total_runs} instances. Saved to `results/{csv_output_filename}`.")


# ==============================================================================
# MAIN DISPLAY TABS (STRICT ORDER: TAB 1 MUST BE RESULTS & METRICS)
# ==============================================================================
tab_results, tab_pddl, tab_fault_loc, tab_maintenance, tab_telemetry = st.tabs([
    "📊 Evaluation Results & Metrics",
    "📄 Generated PDDL & AST Blueprint",
    "🔍 Layered Model-Based Fault Localization",
    "🛡️ Historical Regression Suite (Phase 4)",
    "⏱️ Telemetry & Cost Analytics"
])


# ==============================================================================
# TAB 1: 📊 EVALUATION RESULTS & METRICS TABLE (MANDATORY FIRST TAB)
# ==============================================================================
with tab_results:
    st.markdown("### 📊 Benchmark Evaluation Scorecard & Quantitative Metrics")
    st.caption("Standardized classical automated planning evaluation metrics grounded in VAL and Fast Downward symbolic oracles.")
    
    results_list = st.session_state.get("results_history", [])
    
    if not results_list:
        st.info("👈 **No benchmark runs executed yet in this session.** Select a task in the sidebar and click **'🚀 Run Selected Task'** or execute a **Batch Benchmark** to populate this table.")
        
        # Architectural Reference Overview
        st.markdown("#### 📐 Supported Quantitative Metrics Reference")
        st.markdown("""
        - **SVR (Syntax Validity Rate)**: Fox & Long (2003) VAL parse rate (100% iff domain and problem parse without syntax or typing errors).
        - **TPV (Target Plan Validity)**: Howey, Long, & Fox (2004) plan validity certified by VAL on target task instance.
        - **PTS (Plan Transfer Solvability)**: Non-circular semantic soundness certificate under reference ground-truth domain (D_gt).
        - **FLA (Fault Localization Accuracy Top-1)**: Top-1 localization accuracy of the faulty AST element by the Diagnostic LLM Agent.
        - **Macro Structural F1**: Oswald et al. (ICAPS 2024) Kuhn-Munkres optimal bipartite matching score against reference STRIPS operators.
        - **Pre / Add / Del F1**: Aineto et al. (JAIR 2022) decoupled STRIPS transition relation precision/recall harmonic means.
        - **Cov_ref (Solvability Preservation Rate)**: Percentage of canonical historical benchmark problem instances (P_1, ..., P_k) that remain solvable under the evolved domain model.
        """)

    else:
        # 1. Summary KPI Cards
        df_results = pd.DataFrame(results_list)
        total_runs = len(df_results)
        passed_runs = len(df_results[df_results["Status"] == "Verified ✅"])
        pass_rate = (passed_runs / total_runs) * 100.0 if total_runs > 0 else 0.0

        numeric_f1 = pd.to_numeric(df_results["Macro F1"], errors="coerce")
        mean_f1 = numeric_f1.dropna().mean() if not numeric_f1.dropna().empty else 0.0

        numeric_iters = pd.to_numeric(df_results["Iterations (k)"], errors="coerce")
        avg_iters = numeric_iters.dropna().mean() if not numeric_iters.dropna().empty else 1.0

        fla_passes = len(df_results[df_results["FLA Top-1"] == "PASS"])
        fla_evals = len(df_results[df_results["FLA Top-1"].isin(["PASS", "FAIL"])])
        fla_rate = (fla_passes / fla_evals * 100.0) if fla_evals > 0 else None

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
                <div class="kpi-title">Mean Macro F1</div>
                <div class="kpi-value">{mean_f1:.4f}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">FLA Top-1 Rate</div>
                <div class="kpi-value">{f"{fla_rate:.1f}%" if fla_rate is not None else "N/A"}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Avg Iterations (k)</div>
                <div class="kpi-value">{avg_iters:.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Comprehensive Metrics Interactive Table
        st.markdown("#### 📋 Empirical Results Data Table")
        st.dataframe(df_results, use_container_width=True)

        # 3. CSV Download & Action Buttons
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
                st.rerun()


# ==============================================================================
# TAB 2: 📄 GENERATED DOMAIN FILE & EXPANDABLE AST BLUEPRINT
# ==============================================================================
with tab_pddl:
    st.markdown("### 📄 Generated PDDL Models & AST Blueprint")
    st.caption("Clean compiled classical PDDL 2.1 code (domain and problem), with expandable domain AST blueprint below.")
    
    active_state = st.session_state.get("active_state")
    saved_info = st.session_state.get("last_saved_info")
    
    if active_state:
        dom_pddl = active_state.get("generated_domain_pddl", "")
        prob_pddl = active_state.get("generated_problem_pddl", "")
        domain_bp = active_state.get("pddl_domain_blueprint", {})
        has_errors = bool(active_state.get("verification_errors", []))
        
        # Status Badge & Filepath
        if has_errors:
            st.warning("⚠️ **Candidate Model (Unverified)**: Oracle verification did not fully pass. Intermediate model snapshot shown below.")
        else:
            st.success("✅ **Verified Domain Model**: 100% syntactically valid and certified solvable by VAL & Fast Downward.")
            
        if saved_info:
            s_name, s_idx, s_dom, s_prob = saved_info[:4]
            clean_dom_path = os.path.relpath(s_dom).replace("\\", "/")
            st.caption(f"💾 Auto-Saved to local disk: `{clean_dom_path}`")

        # 1. Generated Domain PDDL Code
        st.markdown("#### `domain.pddl` (Generated / Repaired / Evolved)")
        st.code(dom_pddl, language="lisp")

        # 2. EXPANDABLE AST DOMAIN FILE (DEFAULT: FALSE) - STRICTLY AS REQUESTED
        with st.expander("Domain Blueprint AST (JSON)", expanded=False):
            st.caption("Structured Pydantic AST schema representation used by the Closed-Loop Agent for surgical modification.")
            st.json(domain_bp if domain_bp else {"info": "Blueprint empty or generated via direct text ablation."})

        # 3. Generated Problem PDDL Code
        st.markdown("#### `problem.pddl`")
        st.code(prob_pddl, language="lisp")

        # 4. Classical Plan Output (if generated)
        plan_res = active_state.get("generated_plan_result")
        if plan_res and plan_res.get("is_solvable") and plan_res.get("plan_steps"):
            st.markdown("---")
            st.markdown("#### 📋 Synthesized Classical Plan (`sas_plan`)")
            p_len = plan_res.get("plan_length", len(plan_res["plan_steps"]))
            p_time = plan_res.get("search_time", 0.0)
            st.caption(f"Plan Length: **{p_len} steps** | Fast Downward Search Time: **{p_time:.4f}s** | VAL Certificate: **Valid 🛡️**")
            
            steps = plan_res["plan_steps"]
            formatted_steps = [{"Step": i, "Action Schema & Grounded Parameters": s} for i, s in enumerate(steps, 1)]
            st.dataframe(formatted_steps, use_container_width=True)

    else:
        st.info("👈 Run a task or benchmark to view the generated domain PDDL and AST blueprint here.")


# ==============================================================================
# TAB 3: 🔍 LAYERED MODEL-BASED FAULT LOCALIZATION
# ==============================================================================
with tab_fault_loc:
    st.markdown("### 🔍 Layered Model-Based Fault Localization & Causal Diagnostics")
    st.caption("Root-cause categorization, causal invariants analysis, and surgical repair recommendations from the Diagnostic LLM Agent.")

    active_state = st.session_state.get("active_state")
    if active_state:
        init_errors = active_state.get("initial_verification_errors", []) or active_state.get("verification_errors", [])
        reports = active_state.get("historical_diagnostic_reports", []) or active_state.get("diagnostic_reports", [])
        
        # 1. Classical Causal Graph Diagnostics
        from tools.causal_fault_analyzer import run_causal_fault_analysis
        d_bp = active_state.get("pddl_domain_blueprint") or {}
        p_pddl = active_state.get("initial_problem_pddl") or active_state.get("generated_problem_pddl") or ""
        causal_data = active_state.get("causal_graph_analysis")
        if not causal_data and d_bp and d_bp.get("actions"):
            causal_data = run_causal_fault_analysis(d_bp, p_pddl, init_errors)

        if causal_data and causal_data.get("diagnostic_summary"):
            with st.expander("🕸️ Causal Graph & DTG Structural Diagnostics (Torralba & Hoffmann Invariants)", expanded=True):
                st.code(causal_data.get("diagnostic_summary"), language="text")

        # 2. Raw Oracle Error Output
        if init_errors:
            st.markdown("#### 🚨 Captured Oracle Diagnostic Error Output (Prior to Repair)")
            for err_idx, err_text in enumerate(init_errors, 1):
                first_line = err_text.strip().split("\n")[0][:120]
                with st.expander(f"⚠️ Raw Oracle Error #{err_idx}: {first_line}...", expanded=False):
                    st.code(err_text, language="text")

        # 3. Structured Diagnostic Reports
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
# TAB 4: 🛡️ HISTORICAL REGRESSION SUITE (PHASE 4 MAINTENANCE)
# ==============================================================================
with tab_maintenance:
    st.markdown("### 🛡️ Phase 4 Maintenance & Historical Regression Suite")
    st.caption("Solvability Preservation verification across reference benchmark problem instances (P_1, ..., P_k).")

    active_state = st.session_state.get("active_state")
    if active_state:
        hist_plans = active_state.get("historical_plan_results", [])
        if hist_plans:
            st.markdown(f"#### 📁 Solvability Preservation Proof ({len(hist_plans)} Historical Instances)")
            for hp in hist_plans:
                cid = hp.get("case_id", "historical_instance")
                h_res = hp.get("plan_result", {})
                h_solv = h_res.get("is_solvable", False)
                h_len = h_res.get("plan_length", 0)
                h_time = h_res.get("search_time", 0.0)
                
                if h_solv:
                    st.success(f"**Instance `{cid}`**: Solvable ✅ | Plan Length: {h_len} steps | Search Time: {h_time:.4f}s")
                else:
                    st.error(f"**Instance `{cid}`**: Regression Breakage ❌ | Solver Unsolvable")
        else:
            st.info("No historical regression problems were evaluated in the current run.")
    else:
        st.info("👈 Run a task with Domain Evolution or Maintenance enabled to inspect regression suite verification.")


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
                {"Node": "Node 6: Phase 4 Maintenance Suite", "Latency (s)": f"{node_lat.get('maintenance', 0.0):.3f}s"},
            ], use_container_width=True)
    else:
        st.info("👈 Run a task or benchmark to view telemetry metrics.")
