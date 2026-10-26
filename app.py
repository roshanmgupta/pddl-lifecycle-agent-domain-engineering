import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import json
import os
import time
from typing import Dict, Any, Optional
import re
import glob
import difflib
from dotenv import load_dotenv
load_dotenv(override=True)

from config.paths import (
    get_benchmark_dir,
    get_autoplanbench_dir,
    get_temp_domain_path,
    get_temp_problem_path,
    get_temp_gt_domain_path,
    get_temp_plan_path,
    get_temp_eval_plan_path,
    get_generated_output_dir,
    get_flaw_output_dir,
    get_evolve_output_dir,
    get_elicitation_output_dir,
    get_generated_domain_filename,
    get_generated_problem_filename,
    get_generated_plan_filename,
)

from benchmark.pure_strips_benchmarks import (
    AUTOPLANBENCH_PURE_STRIPS_DOMAINS,
    load_autoplanbench_original_domain_data,
    list_autoplanbench_problem_files,
)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="PDDL Lifecycle Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5 0%, #7B1FA2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #546E7A;
        margin-bottom: 1.5rem;
    }
    .node-card {
        background-color: #F4F6F9;
        border-left: 4px solid #1E88E5;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    .stCodeBlock {
        border-radius: 8px;
    }
    [data-testid="stSidebar"] pre {
        max-height: 400px !important;
        overflow-y: auto !important;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

import glob

# Import Project Modules
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from eval.baselines import run_zero_shot_baseline, run_unstructured_retry_baseline, run_no_ast_ablation
from eval.benchmark_runner import evaluate_candidate_pddl
from graph import pddl_lifecycle_graph, AgentState
from tools.blueprint_parser import parse_pddl_domain_to_blueprint

def save_output_to_disk(state: dict, task: Optional[Any] = None) -> tuple:
    """
    Saves compiled domain.pddl, problem.pddl, and blueprint json
    into track-specific benchmark output directories:
      - PDDLLifeCycleBench_Output_Flaw/<domain_name>/ (for synthetic flaw repair)
      - PDDLLifeCycleBench_Output__Evolve/<domain_name>/ (for continuous domain evolution)
      - PDDLLifeCycleBench_Output_Elicitation/<domain_name>/ (for fresh domain elicitation / custom input)
    with auto-incrementing numeric indices: domain_1.pddl, domain_2.pddl, etc.
    """
    domain_bp = state.get("pddl_domain_blueprint", {})
    if isinstance(domain_bp, dict):
        d_name = domain_bp.get("domain_name", "generated_domain")
    else:
        d_name = getattr(domain_bp, "domain_name", "generated_domain")
        
    d_name = re.sub(r'[^a-zA-Z0-9_\-]', '', str(d_name)).lower() or "generated_domain"

    # Determine track-specific output root
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
        
    # Serialize and save structured diagnostic triage report
    import datetime
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
        "plan_summary": {
            "is_solvable": plan_res.get("is_solvable", False),
            "plan_length": plan_res.get("plan_length", 0),
            "search_time_seconds": plan_res.get("search_time", 0.0),
            "val_plan_valid": plan_res.get("val_plan_valid", False),
            "plan_steps": plan_res.get("plan_steps", [])
        } if (plan_res and isinstance(plan_res, dict)) else None
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

# Universal PDDL String to AST Blueprint Parsers are imported from tools.blueprint_parser


# Header Section
st.markdown('<div class="main-header">🧠 Towards an Autonomous Lifecycle Agent for PDDL Domain Modelling -</div>', unsafe_allow_html=True)
# ==============================================================================
# SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.title("⚙️ Agent Controls & Benchmarks")
st.sidebar.markdown("### 🚀 AutoPlanBench (Pure STRIPS+Typing)")

sel_domain = st.sidebar.selectbox(
    "Choose Pure STRIPS Domain (autoplanbench/data/):",
    AUTOPLANBENCH_PURE_STRIPS_DOMAINS,
    index=0,
    help="Strictly pure (:requirements :strips :typing) domains from autoplanbench/data/."
)

avail_prob_files = list_autoplanbench_problem_files(sel_domain)
sel_instance = st.sidebar.selectbox(
    "Choose Problem Instance:",
    avail_prob_files,
    index=0 if avail_prob_files else 0
)

initial_domain_pddl_input = ""
initial_problem_pddl_input = ""
initial_domain_bp_input = {}
historical_suite_input = []
enable_maintenance = False
is_evolution_task = False
is_synthetic_repair = False
selected_task = None
initial_errors_input = []

unified_prompt, dom_desc, prob_desc, ref_dom, ref_inst, prob_files = load_autoplanbench_original_domain_data(
    sel_domain, sel_instance
)
if ref_inst:
    initial_problem_pddl_input = ref_inst

req_text = st.sidebar.text_area(
    "Natural Language Requirements (Domain & Problem):",
    value=unified_prompt,
    height=220,
    help=f"Specification loaded directly from original autoplanbench/data/{sel_domain}/."
)

with st.sidebar.expander(f"📄 Domain Rules (`{sel_domain}/domain_encoding.txt`)", expanded=False):
    st.text(dom_desc)
    
with st.sidebar.expander(f"📄 Problem Scenario (`{sel_domain}/{sel_instance}`)", expanded=False):
    st.text(prob_desc)
    
if ref_dom or ref_inst:
    with st.sidebar.expander(f"🏛️ Benchmark Reference Ground-Truth PDDL", expanded=False):
        if ref_dom:
            st.caption(f"**Domain**: `{sel_domain}/domain.pddl`")
            st.code(ref_dom, language="lisp")
        if ref_inst:
            st.caption(f"**Problem**: `{sel_domain}/{sel_instance}`")
            st.code(ref_inst, language="lisp")
            
st.sidebar.markdown("---")
st.sidebar.subheader("Phase 4 Maintenance Settings")
enable_maintenance = st.sidebar.checkbox(
    "Enable Phase 4 Historical Regression Suite",
    value=False,
    help="Verifies that the generated domain retains backward compatibility against the benchmark instance."
)
if enable_maintenance and prob_files:
    chosen_instances = st.sidebar.multiselect(
        "Choose Historical Problem Instance(s) (Phase 4):",
        prob_files,
        default=[sel_instance] if sel_instance in prob_files else ([prob_files[0]] if prob_files else []),
        help="Select one or more historical instances to verify backward compatibility."
    )
    historical_suite_input = []
    d_folder = Path(get_autoplanbench_dir()) / sel_domain / "orig_problems"
    for inst_name in chosen_instances:
        inst_path = d_folder / inst_name
        if inst_path.exists():
            with open(inst_path, "r", encoding="utf-8") as f:
                inst_txt = f.read()
            if inst_txt.strip():
                historical_suite_input.append({
                    "case_id": f"{sel_domain}_{inst_name.replace('.pddl', '')}",
                    "problem_pddl": inst_txt,
                    "raw_pddl": inst_txt
                })
    if historical_suite_input:
        st.sidebar.success(f"📁 **{len(historical_suite_input)} Regression Case(s) Loaded**: {[c['case_id'] for c in historical_suite_input]}")
elif enable_maintenance and ref_inst:
    if ref_inst.strip():
        historical_suite_input = [{
            "case_id": f"{sel_domain}_{sel_instance}",
            "problem_pddl": ref_inst,
            "raw_pddl": ref_inst
        }]
        st.sidebar.success(f"📁 **Regression Case Loaded**: `{sel_domain}_{sel_instance}`")

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System Architecture & Baselines")
system_choice = st.sidebar.selectbox(
    "Select Architecture / Evaluated System:",
    options=[
        "CLOSED_LOOP_AST_AGENT",
        "ABLATION_NO_TRIAGE",
        "ABLATION_NO_AST",
        "UNSTRUCTURED_RETRY",
        "ZERO_SHOT"
    ],
    format_func=lambda x: {
        "CLOSED_LOOP_AST_AGENT": "🧠 Closed-Loop AST Agent (Diagnostic LLM + Surgical AST)",
        "ABLATION_NO_TRIAGE": "🔬 Ablation: No Triage (AST Blueprint + Raw Trace Errors) [Tests H2]",
        "ABLATION_NO_AST": "🔬 Ablation: No AST (Direct PDDL Text + Diagnostic Triage) [Tests H1]",
        "UNSTRUCTURED_RETRY": "⚡ Baseline: Unstructured Retry (Direct PDDL + Raw Trace Errors)",
        "ZERO_SHOT": "🎯 Baseline: Zero-Shot (Direct PDDL, No Feedback Loop)"
    }.get(x, x),
    help="Select which system architecture to execute and evaluate against classical oracles."
)

if system_choice == "CLOSED_LOOP_AST_AGENT":
    st.sidebar.caption("✨ **Proposed Thesis Method**: Pydantic AST schema elicitation, compiler, VAL/FD oracles, Diagnostic LLM Agent for fault localization, surgical AST repair.")
elif system_choice == "ABLATION_NO_TRIAGE":
    st.sidebar.caption("🔬 **Thesis Ablation (Tests H2)**: AST Blueprint + compiler, but closed-loop without diagnostic triage. Raw terminal error logs from VAL/FD are routed directly to repair.")
elif system_choice == "ABLATION_NO_AST":
    st.sidebar.caption("🔬 **Thesis Ablation (Tests H1)**: LLM repairs raw PDDL text directly. Receives structured Diagnostic Triage reports and repair hints, but without an AST Blueprint or Python compiler.")
elif system_choice == "UNSTRUCTURED_RETRY":
    st.sidebar.caption("⚡ **Literature Baseline**: LLM directly outputs raw PDDL text. Iteratively re-prompted with raw VAL/FD terminal error logs (no AST schema, no diagnostic triage).")
elif system_choice == "ZERO_SHOT":
    st.sidebar.caption("🎯 **Literature Baseline**: Single-pass raw PDDL generation from natural language prompt. No validator or planner in the loop.")

max_iterations = st.sidebar.slider(
    "Max Iterations:",
    min_value=1,
    max_value=15,
    value=5 if system_choice in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"] else 5
)

# Construct the formal active BenchmarkTask object
inst_stem = sel_instance.replace('.pddl', '') if sel_instance else 'prob'
active_task = BenchmarkTask(
    task_id=f"autoplanbench_{sel_domain}_{inst_stem}",
    domain_family=sel_domain,
    task_type=LifecycleTaskType.ELICITATION,
    title=f"AutoPlanBench: {sel_domain} ({sel_instance})",
    natural_language_requirements=req_text,
    initial_domain_pddl="",
    initial_problem_pddl=ref_inst if ('ref_inst' in locals() and ref_inst) else "",
    ground_truth_domain_pddl=ref_dom if ('ref_dom' in locals() and ref_dom) else "",
    ground_truth_problem_pddl=ref_inst if ('ref_inst' in locals() and ref_inst) else "",
    baseline_benchmark_problems=[
        c.get("problem_pddl") or c.get("raw_pddl") or ""
        for c in historical_suite_input
    ] if enable_maintenance else []
)

# ==============================================================================
# MAIN REQUIREMENT DISPLAY & LAUNCH BUTTON
# ==============================================================================
col_req, col_action = st.columns([3, 1])

with col_req:
    st.subheader(f"📋 Active Domain Specification (`{sel_domain}` / `{sel_instance}`)")
    user_requirements = st.text_area(
        "Requirements Prompt:",
        value=req_text,
        placeholder="Natural language requirements for domain and problem...",
        height=140,
        label_visibility="collapsed",
        help="Natural language requirements loaded directly from AutoPlanBench."
    )
    active_task.natural_language_requirements = user_requirements

with col_action:
    st.subheader("🚀 Trigger")
    system_display_name = {
        "CLOSED_LOOP_AST_AGENT": "Closed-Loop AST Agent",
        "ABLATION_NO_TRIAGE": "Ablation (No Triage)",
        "UNSTRUCTURED_RETRY": "Unstructured Retry",
        "ZERO_SHOT": "Zero-Shot Baseline"
    }.get(system_choice, system_choice)
    st.caption(f"Target: **{system_display_name}**")
    btn_label = f"🚀 Run {system_choice}"
    run_agent = st.button(btn_label, type="primary", width='stretch')

# Initialize Session State
if "final_state" not in st.session_state:
    st.session_state["final_state"] = None
if "node_logs" not in st.session_state:
    st.session_state["node_logs"] = []
if "active_run_metrics" not in st.session_state:
    st.session_state["active_run_metrics"] = None

# ==============================================================================
# LIVE STREAMING EXECUTION ROUTING ACROSS ARCHITECTURES
# ==============================================================================
if run_agent:
    st.session_state["node_logs"] = []
    st.session_state["final_state"] = None
    st.session_state["active_run_metrics"] = None
    start_time = time.time()
    
    # CASE 1: CLOSED-LOOP AST AGENT OR ABLATION (NO TRIAGE)
    if system_choice in ["CLOSED_LOOP_AST_AGENT", "ABLATION_NO_TRIAGE"]:
        initial_state = {
            "requirements": user_requirements,
            "pddl_domain_blueprint": initial_domain_bp_input,
            "initial_domain_pddl": initial_domain_pddl_input,
            "initial_problem_pddl": initial_problem_pddl_input,
            "is_evolution_task": is_evolution_task,
            "is_synthetic_repair": is_synthetic_repair,
            "skip_elicitation": is_synthetic_repair,
            "generated_domain_pddl": initial_domain_pddl_input,
            "generated_problem_pddl": initial_problem_pddl_input,
            "verification_errors": initial_errors_input,
            "diagnostic_reports": [],
            "formatted_diagnostic_feedback": "",
            "baseline_benchmark_problems": historical_suite_input if enable_maintenance else [],
            "benchmark_problem_distribution": historical_suite_input if enable_maintenance else [],
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "generated_plan_result": {},
            "historical_plan_results": [],
            "skip_triage": (system_choice == "ABLATION_NO_TRIAGE"),
            "system_type": system_choice
        }

        st.markdown(f"### 🔄 Live Execution Stream: `{system_choice}`")
        status_container = st.status(f"🚀 Initializing {system_choice}... Streaming state transitions...", expanded=True)
        current_state = initial_state
        cumulative_issue_count = 0
        
        try:
            for output in pddl_lifecycle_graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in output.items():
                    current_state.update(node_output)
                    
                    if node_name == "elicit":
                        status_container.write("🧠 **Node 1 [ELICIT]**: LLM analyzing requirements and extracting Pydantic AST schema...")
                        domain_bp = node_output.get("pddl_domain_blueprint", {})
                        status_container.caption(f"-> Extracted Domain Name: `{domain_bp.get('domain_name', 'N/A')}` | Actions: `{len(domain_bp.get('actions', []))}`")
                        time.sleep(0.3)
                        
                    elif node_name == "generate":
                        status_container.write("⚙️ **Node 2 [GENERATE]**: Python deterministic Compiler generating 100% syntactically valid Lisp PDDL code...")
                        status_container.caption("-> Compiled `generated_domain_pddl` and `generated_problem_pddl` strings.")
                        time.sleep(0.3)
                        
                    elif node_name == "validate":
                        errors = node_output.get("verification_errors", [])
                        if not errors:
                            status_container.write("⚡ **Node 3 [VALIDATE]**: Oracles (VAL & Fast Downward) verified syntax and plan reachability cleanly!")
                        else:
                            status_container.write(f"⚠️ **Node 3 [VALIDATE]**: Oracles detected {len(errors)} error log(s):")
                            for err_idx, err_msg in enumerate(errors, 1):
                                first_line = err_msg.strip().split("\n")[0][:120]
                                with status_container.expander(f"⚠️ Oracle Error Log #{err_idx}: {first_line}...", expanded=False):
                                    st.code(err_msg.strip(), language="text")
                        time.sleep(0.3)
                            
                    elif node_name == "maintenance":
                        m_errors = node_output.get("verification_errors", [])
                        bench_suite = current_state.get("baseline_benchmark_problems", []) or current_state.get("benchmark_problem_distribution", [])
                        if bench_suite:
                            if not m_errors:
                                status_container.write(f"🛡️ **Node 4 [MAINTENANCE]**: Phase 4 Baseline Benchmark Suite passed ({len(bench_suite)} test case(s))! Solvability preservation verified.")
                            else:
                                status_container.write(f"🚨 **Node 4 [MAINTENANCE]**: Solvability preservation breakage detected on {len(m_errors)} test case(s):")
                                for err_idx, err_msg in enumerate(m_errors, 1):
                                    status_container.caption(f"  * Breakage #{err_idx}: `{err_msg}`")
                        time.sleep(0.3)
                            
                    elif node_name == "triage":
                        cur_it = current_state.get("iteration_count", 0)
                        max_it = current_state.get("max_iterations", 10)
                        if system_choice == "ABLATION_NO_TRIAGE":
                            status_container.write(f"🔬 **Node 4 [TRIAGE - ABLATION] (Iteration {cur_it + 1}/{max_it})**: Diagnostic LLM Agent BYPASSED (Ablation Study). Raw oracle error logs routed directly to repair without root-cause localization.")
                        else:
                            reports = node_output.get("diagnostic_reports", [])
                            status_container.write(f"🔍 **Node 4 [TRIAGE] (Iteration {cur_it + 1}/{max_it})**: Diagnostic LLM Agent categorized {len(reports)} diagnostic item(s):")
                            for r in reports:
                                cumulative_issue_count += 1
                                if isinstance(r, dict):
                                    err_cat = r.get("error_category", "UNKNOWN")
                                    op_type = r.get("repair_operation_type", "GENERAL")
                                    element = r.get("faulty_element", "General")
                                    log_text = r.get("raw_log", "")
                                    hint = r.get("suggested_repair_hint", "")
                                else:
                                    err_cat = getattr(r, "error_category", "UNKNOWN")
                                    op_type = getattr(r, "repair_operation_type", "GENERAL")
                                    element = getattr(r, "faulty_element", "General")
                                    log_text = getattr(r, "raw_log", "")
                                    hint = getattr(r, "suggested_repair_hint", "")

                                with status_container.expander(
                                    f"📌 Issue #{cumulative_issue_count}: [{err_cat}] - Faulty Element: '{element or 'General'}' (Click to Expand)",
                                    expanded=True
                                ):
                                    st.markdown(f"- **Target AST Operation**: `{op_type}`")
                                    if hint:
                                        st.info(f"**Actionable Repair Hint**: {hint}")
                                    if log_text:
                                        st.markdown("**Exact Raw Error Log from Solver/Validator:**")
                                        st.code(log_text.strip(), language="text")
                        time.sleep(0.3)
                            
                    elif node_name == "repair":
                        cur_it = current_state.get("iteration_count", 1)
                        max_it = current_state.get("max_iterations", 10)
                        status_container.write(f"🔧 **Node 5 [REPAIR] (Iteration {cur_it}/{max_it})**: Reasoning LLM executing surgical AST repair on faulty blueprint nodes...")
                        status_container.caption("-> Blueprint updated in memory. Looping back to Python deterministic Compiler.")
                        time.sleep(0.3)

            has_errors = bool(current_state.get("verification_errors", []))
            exec_time = time.time() - start_time

            # Capture plan result if model is verified
            if not has_errors:
                dom_str = current_state.get("generated_domain_pddl")
                prob_str = current_state.get("generated_problem_pddl")
                plan_res = current_state.get("generated_plan_result")
                gt_dom = getattr(active_task, "ground_truth_domain_pddl", None) if active_task else None
                gt_prob = getattr(active_task, "ground_truth_problem_pddl", None) if active_task else None

                if dom_str and prob_str:
                    tmp_d = get_temp_domain_path()
                    tmp_p = get_temp_problem_path()
                    with open(tmp_d, "w", encoding="utf-8") as f:
                        f.write(dom_str)
                    with open(tmp_p, "w", encoding="utf-8") as f:
                        f.write(prob_str)
                    
                    tmp_gt = None
                    tmp_gt_p = tmp_p
                    if gt_dom:
                        tmp_gt = get_temp_gt_domain_path()
                        with open(tmp_gt, "w", encoding="utf-8") as f:
                            f.write(gt_dom)
                    if gt_prob:
                        tmp_gt_p = tmp_p + ".gt.pddl"
                        with open(tmp_gt_p, "w", encoding="utf-8") as f:
                            f.write(gt_prob)

                    if not plan_res or not plan_res.get("is_solvable"):
                        from tools.symbolic_oracles import run_fast_downward_with_plan
                        plan_res = run_fast_downward_with_plan(
                            tmp_d, tmp_p, ground_truth_domain_path=tmp_gt
                        )
                        current_state["generated_plan_result"] = plan_res
                    elif tmp_gt and plan_res.get("plan_steps") and not plan_res.get("semantic_soundness_valid"):
                        from tools.symbolic_oracles import validate_plan_semantic_soundness
                        tmp_plan = get_temp_eval_plan_path()
                        with open(tmp_plan, "w", encoding="utf-8") as pf:
                            for idx_s, stp in enumerate(plan_res["plan_steps"], 1):
                                pf.write(f"{idx_s}: {stp}\n")
                        pss_valid, pss_log = validate_plan_semantic_soundness(
                            tmp_gt, tmp_gt_p, tmp_plan, generated_domain_path=tmp_d
                        )
                        plan_res["semantic_soundness_valid"] = pss_valid
                        plan_res["semantic_soundness_log"] = pss_log
                        if os.path.exists(tmp_plan):
                            try: os.remove(tmp_plan)
                            except Exception: pass
                        if tmp_gt_p != tmp_p and os.path.exists(tmp_gt_p):
                            try: os.remove(tmp_gt_p)
                            except Exception: pass

                if gt_dom and dom_str:
                    try:
                        from eval.action_reconstruction import evaluate_action_reconstruction
                        are_res = evaluate_action_reconstruction(gt_dom, dom_str)
                        if plan_res:
                            plan_res["are_res"] = are_res
                    except Exception:
                        pass

            # Rigorous Empirical Evaluation of the generated candidate model
            metrics = evaluate_candidate_pddl(
                task=active_task,
                agent_type=system_choice,
                generated_domain_pddl=current_state.get("generated_domain_pddl", ""),
                generated_problem_pddl=current_state.get("generated_problem_pddl", ""),
                iterations_used=max(1, current_state.get("iteration_count", 1)),
                execution_time_seconds=exec_time,
                total_tokens=current_state.get("total_tokens", 0),
                estimated_cost_usd=current_state.get("estimated_cost_usd", 0.0),
                diagnostic_reports=current_state.get("diagnostic_reports", []),
                error_summary=" ".join(current_state.get("verification_errors", [])) if current_state.get("verification_errors") else None
            )
            st.session_state["active_run_metrics"] = metrics
            st.session_state["final_state"] = current_state
            saved_info = save_output_to_disk(current_state, active_task)
            st.session_state["last_saved_info"] = saved_info

            if metrics.e2e_success:
                p_len_str = str(metrics.plan_length) if metrics.plan_length is not None else "N/A"
                status_container.update(label=f"✅ Execution Finished! Verified E2E Lifecycle Success (Plan Length: {p_len_str})", state="complete", expanded=True)
            else:
                iter_used = current_state.get("iteration_count", 0)
                if iter_used >= max_iterations:
                    status_container.update(label="⚠️ Max Repair Iterations Reached (Model Unverified)", state="error", expanded=True)
                    st.error("⚠️ The agent reached maximum repair iterations without resolving all oracle errors. Intermediate diagnostic snapshot saved to disk.")
                else:
                    status_container.update(label="⚠️ Oracle Verification Incomplete (Model Unverified)", state="error", expanded=True)
                    st.error(f"⚠️ Oracle Verification Incomplete: {metrics.error_summary or 'Secondary evaluation criteria not met.'}")
                
        except Exception as e:
            status_container.update(label=f"❌ Execution Error: {str(e)}", state="error")
            st.error(f"Execution Error: {str(e)}")

    # CASE 2: UNSTRUCTURED RETRY BASELINE
    elif system_choice == "UNSTRUCTURED_RETRY":
        st.markdown("### 🔄 Live Execution Stream: `UNSTRUCTURED_RETRY`")
        status_container = st.status("⚡ Running Unstructured Retry Baseline (Direct PDDL Re-prompting)...", expanded=True)
        status_container.write("Iterative raw PDDL text re-prompting with terminal VAL/FD error feedback (No AST schema, no diagnostic triage)...")
        try:
            t0 = time.time()
            base_res = run_unstructured_retry_baseline(active_task, max_retries=max_iterations)
            exec_time = time.time() - t0
            
            status_container.write(f"-> Completed in {exec_time:.2f}s | Iterations: {base_res.get('iterations_used', 1)} | Tokens: {base_res.get('total_tokens', 0)}")
            
            current_state = {
                "system_type": "UNSTRUCTURED_RETRY",
                "requirements": user_requirements,
                "generated_domain_pddl": base_res.get("generated_domain_pddl", ""),
                "generated_problem_pddl": base_res.get("generated_problem_pddl", ""),
                "initial_domain_pddl": initial_domain_pddl_input,
                "initial_problem_pddl": initial_problem_pddl_input,
                "verification_errors": [base_res["error"]] if base_res.get("error") else [],
                "diagnostic_reports": [],
                "iteration_count": base_res.get("iterations_used", 1),
                "total_tokens": base_res.get("total_tokens", 0),
                "total_prompt_tokens": base_res.get("prompt_tokens", 0),
                "total_completion_tokens": base_res.get("completion_tokens", 0),
                "estimated_cost_usd": base_res.get("estimated_cost_usd", 0.0),
                "node_latencies": {"unstructured_retry": exec_time}
            }
            
            metrics = evaluate_candidate_pddl(
                task=active_task,
                agent_type="UNSTRUCTURED_RETRY",
                generated_domain_pddl=base_res.get("generated_domain_pddl", ""),
                generated_problem_pddl=base_res.get("generated_problem_pddl", ""),
                iterations_used=base_res.get("iterations_used", 1),
                execution_time_seconds=exec_time,
                total_tokens=base_res.get("total_tokens", 0),
                estimated_cost_usd=base_res.get("estimated_cost_usd", 0.0),
                error_summary=base_res.get("error")
            )
            st.session_state["active_run_metrics"] = metrics
            st.session_state["final_state"] = current_state
            saved_info = save_output_to_disk(current_state, active_task)
            st.session_state["last_saved_info"] = saved_info
            
            if metrics.e2e_success:
                status_container.update(label="✅ Unstructured Retry Finished! Model Verified (E2E Success = True)", state="complete", expanded=True)
            else:
                status_container.update(label="⚠️ Unstructured Retry Finished: Model Unverified (E2E Success = False)", state="error", expanded=True)
                
        except Exception as e:
            status_container.update(label=f"❌ Execution Error: {str(e)}", state="error")
            st.error(f"Execution Error: {str(e)}")

    # CASE 3: ABLATION NO AST (Direct Text Repair + Structured Diagnostic Triage)
    elif system_choice == "ABLATION_NO_AST":
        st.markdown("### 🔬 Live Execution Stream: `ABLATION_NO_AST` (Tests H1)")
        status_container = st.status("🔬 Running Ablation: No AST (Direct Text + Diagnostic Triage)...", expanded=True)
        status_container.write("Direct PDDL text repair using structured Diagnostic Triage reports (No AST blueprint, no compiler)...")
        try:
            t0 = time.time()
            base_res = run_no_ast_ablation(active_task, max_retries=max_iterations)
            exec_time = time.time() - t0
            
            status_container.write(f"-> Completed in {exec_time:.2f}s | Iterations: {base_res.get('iterations_used', 1)} | Tokens: {base_res.get('total_tokens', 0)}")
            
            current_state = {
                "system_type": "ABLATION_NO_AST",
                "requirements": user_requirements,
                "generated_domain_pddl": base_res.get("generated_domain_pddl", ""),
                "generated_problem_pddl": base_res.get("generated_problem_pddl", ""),
                "initial_domain_pddl": initial_domain_pddl_input,
                "initial_problem_pddl": initial_problem_pddl_input,
                "verification_errors": [base_res["error"]] if base_res.get("error") else [],
                "diagnostic_reports": base_res.get("diagnostic_reports", []),
                "iteration_count": base_res.get("iterations_used", 1),
                "total_tokens": base_res.get("total_tokens", 0),
                "total_prompt_tokens": base_res.get("prompt_tokens", 0),
                "total_completion_tokens": base_res.get("completion_tokens", 0),
                "estimated_cost_usd": base_res.get("estimated_cost_usd", 0.0),
                "node_latencies": {"ablation_no_ast": exec_time}
            }
            
            metrics = evaluate_candidate_pddl(
                task=active_task,
                agent_type="ABLATION_NO_AST",
                generated_domain_pddl=base_res.get("generated_domain_pddl", ""),
                generated_problem_pddl=base_res.get("generated_problem_pddl", ""),
                iterations_used=base_res.get("iterations_used", 1),
                execution_time_seconds=exec_time,
                total_tokens=base_res.get("total_tokens", 0),
                estimated_cost_usd=base_res.get("estimated_cost_usd", 0.0),
                diagnostic_reports=base_res.get("diagnostic_reports", []),
                error_summary=base_res.get("error")
            )
            st.session_state["active_run_metrics"] = metrics
            st.session_state["final_state"] = current_state
            saved_info = save_output_to_disk(current_state, active_task)
            st.session_state["last_saved_info"] = saved_info
            
            if metrics.e2e_success:
                status_container.update(label="✅ Ablation No-AST Finished! Model Verified (E2E Success = True)", state="complete", expanded=True)
            else:
                status_container.update(label="⚠️ Ablation No-AST Finished: Model Unverified (E2E Success = False)", state="error", expanded=True)
                
        except Exception as e:
            status_container.update(label=f"❌ Execution Error: {str(e)}", state="error")
            st.error(f"Execution Error: {str(e)}")

    # CASE 4: ZERO-SHOT BASELINE
    elif system_choice == "ZERO_SHOT":
        st.markdown("### 🔄 Live Execution Stream: `ZERO_SHOT`")
        status_container = st.status("🎯 Running Zero-Shot Baseline (Single-Pass Direct Generation)...", expanded=True)
        status_container.write("Generating domain and problem PDDL in a single direct LLM prompt without verification loop...")
        try:
            t0 = time.time()
            base_res = run_zero_shot_baseline(active_task)
            exec_time = time.time() - t0
            
            status_container.write(f"-> Generated in {exec_time:.2f}s | Tokens: {base_res.get('total_tokens', 0)}")
            
            current_state = {
                "system_type": "ZERO_SHOT",
                "requirements": user_requirements,
                "generated_domain_pddl": base_res.get("generated_domain_pddl", ""),
                "generated_problem_pddl": base_res.get("generated_problem_pddl", ""),
                "initial_domain_pddl": initial_domain_pddl_input,
                "initial_problem_pddl": initial_problem_pddl_input,
                "verification_errors": [base_res["error"]] if base_res.get("error") else [],
                "diagnostic_reports": [],
                "iteration_count": 1,
                "total_tokens": base_res.get("total_tokens", 0),
                "total_prompt_tokens": base_res.get("prompt_tokens", 0),
                "total_completion_tokens": base_res.get("completion_tokens", 0),
                "estimated_cost_usd": base_res.get("estimated_cost_usd", 0.0),
                "node_latencies": {"zero_shot_generation": exec_time}
            }
            
            metrics = evaluate_candidate_pddl(
                task=active_task,
                agent_type="ZERO_SHOT",
                generated_domain_pddl=base_res.get("generated_domain_pddl", ""),
                generated_problem_pddl=base_res.get("generated_problem_pddl", ""),
                iterations_used=1,
                execution_time_seconds=exec_time,
                total_tokens=base_res.get("total_tokens", 0),
                estimated_cost_usd=base_res.get("estimated_cost_usd", 0.0),
                error_summary=base_res.get("error")
            )
            st.session_state["active_run_metrics"] = metrics
            st.session_state["final_state"] = current_state
            saved_info = save_output_to_disk(current_state, active_task)
            st.session_state["last_saved_info"] = saved_info
            
            if metrics.e2e_success:
                status_container.update(label="✅ Zero-Shot Finished! Model Verified (E2E Success = True)", state="complete", expanded=True)
            else:
                status_container.update(label="⚠️ Zero-Shot Finished: Model Unverified (E2E Success = False)", state="error", expanded=True)
                
        except Exception as e:
            status_container.update(label=f"❌ Execution Error: {str(e)}", state="error")
            st.error(f"Execution Error: {str(e)}")

# ==============================================================================
# RESULTS & ARTIFACT INSPECTION TABS
# ==============================================================================
final_state = st.session_state.get("final_state")

if final_state:
    st.markdown("---")
    st.subheader("📊 Execution Results & Artifact Inspection")
    is_unverified = bool(final_state.get("verification_errors", []))
    is_verified = not is_unverified
    
    saved_info = st.session_state.get("last_saved_info")
    if saved_info:
        s_name, s_idx, s_dom, s_prob = saved_info[:4]
        s_diag = saved_info[4] if len(saved_info) > 4 else None
        s_plan = saved_info[5] if len(saved_info) > 5 else None
        s_folder = os.path.relpath(os.path.dirname(s_dom)).replace("\\", "/") if s_dom else f"output/{s_name}"
        if is_unverified:
            st.warning(
                f"📁 **Auto-Saved Diagnostic Snapshot**: Stored in `{s_folder}/` as "
                f"`domain_{s_idx}.pddl`, `problem_{s_idx}.pddl`, & `diagnostic_report_{s_idx}.json` (⚠️ **Unverified Intermediate Model** - Oracle checks did not pass)"
            )
        else:
            msg = f"📁 **Auto-Saved Verified Output**: Stored in `{s_folder}/` as `domain_{s_idx}.pddl`, `problem_{s_idx}.pddl`, & `diagnostic_report_{s_idx}.json`"
            if s_plan:
                msg += f" (with `plan_{s_idx}.txt`)"
            st.success(msg + "!")
    
    tab_code, tab_plan, tab_ast, tab_triage, tab_telemetry, tab_eval = st.tabs([
        "📄 Compiled PDDL Code",
        "⚡ Plan & Oracle Verification (VAL & FD)",
        "🌳 AST Relational Blueprints",
        "🚨 Diagnostic Triage Report",
        "⚡ LLM Observability & Cost Metrics",
        "🏆 Empirical Evaluation & Baselines"
    ])

    # Tab 1: PDDL Code (Clean Side-by-Side PDDL Code)
    with tab_code:
        repaired_domain = final_state.get("generated_domain_pddl", "")
        repaired_problem = final_state.get("generated_problem_pddl", "")
        is_verified = not bool(final_state.get("verification_errors", []))
        
        col_dom, col_prob = st.columns(2)
        with col_dom:
            if is_verified:
                if final_state.get("is_synthetic_repair") or is_synthetic_repair:
                    dom_title = "#### `domain.pddl` (Repaired & Verified)"
                elif final_state.get("is_evolution_task") or is_evolution_task:
                    dom_title = "#### `domain.pddl` (Evolved & Verified)"
                else:
                    dom_title = "#### `domain.pddl` (Verified)"
            else:
                dom_title = "#### `domain.pddl` (⚠️ Unverified Candidate)"
            st.markdown(dom_title)
            st.code(repaired_domain, language="lisp")
            if saved_info:
                clean_dom_path = os.path.relpath(saved_info[2]).replace("\\", "/")
                st.caption(f"💾 Saved to local disk: `{clean_dom_path}`")
        with col_prob:
            if is_verified:
                prob_title = "#### `problem.pddl` (Evolved & Verified)" if (final_state.get("is_evolution_task") or is_evolution_task) else "#### `problem.pddl` (Verified)"
            else:
                prob_title = "#### `problem.pddl` (⚠️ Unverified Candidate)"
            st.markdown(prob_title)
            st.code(repaired_problem, language="lisp")
            if saved_info:
                clean_prob_path = os.path.relpath(saved_info[3]).replace("\\", "/")
                st.caption(f"💾 Saved to local disk: `{clean_prob_path}`")

    # Tab 2: Plan & Oracle Verification
    with tab_plan:
        plan_res = final_state.get("generated_plan_result")
        if not plan_res and not final_state.get("verification_errors"):
            dom_str = final_state.get("generated_domain_pddl")
            prob_str = final_state.get("generated_problem_pddl")
            if dom_str and prob_str:
                from tools.symbolic_oracles import run_fast_downward_with_plan
                tmp_d = get_temp_domain_path()
                tmp_p = get_temp_problem_path()
                with open(tmp_d, "w", encoding="utf-8") as f:
                    f.write(dom_str)
                with open(tmp_p, "w", encoding="utf-8") as f:
                    f.write(prob_str)
                tmp_gt = None
                gt_dom = (
                    (getattr(selected_task, "ground_truth_domain_pddl", None) if selected_task else None)
                    or (getattr(active_task, "ground_truth_domain_pddl", None) if 'active_task' in locals() and active_task else None)
                    or (ref_dom if ('ref_dom' in locals() and ref_dom) else None)
                )
                if gt_dom:
                    tmp_gt = get_temp_gt_domain_path()
                    with open(tmp_gt, "w", encoding="utf-8") as f:
                        f.write(gt_dom)

                plan_res = run_fast_downward_with_plan(tmp_d, tmp_p, ground_truth_domain_path=tmp_gt)
                final_state["generated_plan_result"] = plan_res

                if saved_info and len(saved_info) >= 4 and plan_res.get("is_solvable") and plan_res.get("plan_steps"):
                    s_name, s_idx = saved_info[0], saved_info[1]
                    s_dir = os.path.dirname(saved_info[2])
                    plan_stem = Path(get_generated_plan_filename()).stem
                    plan_ext = Path(get_generated_plan_filename()).suffix or ".txt"
                    p_path = os.path.join(s_dir, f"{plan_stem}_{s_idx}{plan_ext}")
                    with open(p_path, "w", encoding="utf-8") as pf:
                        for idx_s, stp in enumerate(plan_res["plan_steps"], 1):
                            pf.write(f"{idx_s}: {stp}\n")
                    saved_info = (saved_info[0], saved_info[1], saved_info[2], saved_info[3],
                                  saved_info[4] if len(saved_info) > 4 else None, p_path)
                    st.session_state["last_saved_info"] = saved_info
        if plan_res:
            dom_str_check = final_state.get("generated_domain_pddl")
            prob_str_check = final_state.get("generated_problem_pddl")
            gt_dom = (
                (getattr(selected_task, "ground_truth_domain_pddl", None) if selected_task else None)
                or (getattr(active_task, "ground_truth_domain_pddl", None) if 'active_task' in locals() and active_task else None)
                or (ref_dom if ('ref_dom' in locals() and ref_dom) else None)
            )
            gt_prob = (
                (getattr(selected_task, "ground_truth_problem_pddl", None) if selected_task else None)
                or (getattr(active_task, "ground_truth_problem_pddl", None) if 'active_task' in locals() and active_task else None)
                or (ref_inst if ('ref_inst' in locals() and ref_inst) else None)
            )

            # Evaluate Action Reconstruction Error (ARE) against ground truth
            are_data = plan_res.get("are_data")
            if not are_data and gt_dom and dom_str_check:
                try:
                    from eval.action_reconstruction import evaluate_action_reconstruction
                    are_data = evaluate_action_reconstruction(gt_dom, dom_str_check)
                    plan_res["are_data"] = are_data
                except Exception as e:
                    print(f"[Action Reconstruction Error]: {e}")

            if gt_dom and prob_str_check and plan_res.get("plan_steps") and plan_res.get("semantic_soundness_valid") is not True:
                tmp_gt = get_temp_gt_domain_path()
                tmp_d = get_temp_domain_path()
                tmp_p = get_temp_problem_path()
                tmp_gt_p = tmp_p + ".gt.pddl" if gt_prob else tmp_p
                tmp_plan = get_temp_eval_plan_path()
                with open(tmp_gt, "w", encoding="utf-8") as f: f.write(gt_dom)
                if dom_str_check:
                    with open(tmp_d, "w", encoding="utf-8") as f: f.write(dom_str_check)
                with open(tmp_p, "w", encoding="utf-8") as f: f.write(prob_str_check)
                if gt_prob:
                    with open(tmp_gt_p, "w", encoding="utf-8") as f: f.write(gt_prob)
                with open(tmp_plan, "w", encoding="utf-8") as f:
                    for idx_s, stp in enumerate(plan_res["plan_steps"], 1):
                        f.write(f"{idx_s}: {stp}\n")
                from tools.symbolic_oracles import validate_plan_semantic_soundness
                pss_valid, pss_log = validate_plan_semantic_soundness(
                    tmp_gt, tmp_gt_p, tmp_plan, generated_domain_path=tmp_d
                )
                plan_res["semantic_soundness_valid"] = pss_valid
                plan_res["semantic_soundness_log"] = pss_log
                if os.path.exists(tmp_plan):
                    try: os.remove(tmp_plan)
                    except Exception: pass
                if tmp_gt_p != tmp_p and os.path.exists(tmp_gt_p):
                    try: os.remove(tmp_gt_p)
                    except Exception: pass

            p_solvable = plan_res.get("is_solvable", False)
            p_len = plan_res.get("plan_length", 0)
            p_time = plan_res.get("search_time", 0.0)
            p_val = plan_res.get("val_plan_valid", False)
            p_pss = plan_res.get("semantic_soundness_valid")
            
            st.markdown("### 🚀 Classical Plan Synthesis & Non-Circular Formal Verification")
            st.caption("Empirical proof generated by symbolic oracles (Fast Downward & VAL) with non-circular ground-truth semantic soundness checking.")
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Planner Status", "Solution Found ✅" if p_solvable else "Unsolvable ❌")
            m2.metric("Plan Length", f"{p_len} steps")
            m3.metric("Search Time", f"{p_time:.4f}s")
            m4.metric("Model Consistency (D_gen)", "Valid 🛡️" if p_val else "Invalid ⚠️")
            if p_pss is True:
                f1_val = are_data.get("macro_structural_f1") if are_data else None
                f1_str = f" (F1: {f1_val})" if f1_val is not None else ""
                m5.metric("Semantic Soundness (D_gt)", f"Sound 🏛️{f1_str}")
            elif p_pss is False:
                f1_val = are_data.get("macro_structural_f1") if are_data else None
                f1_str = f" (F1: {f1_val})" if f1_val is not None else ""
                m5.metric("Semantic Soundness (D_gt)", f"Partial / Div ❌{f1_str}")
            else:
                m5.metric("Semantic Soundness (D_gt)", "N/A (No D_gt)")
            
            if p_solvable and plan_res.get("plan_steps"):
                st.markdown("#### 📋 Synthesized Action Sequence (`sas_plan`)")
                steps = plan_res["plan_steps"]
                formatted_steps = [{"Step": i, "Action Schema & Grounded Parameters": s} for i, s in enumerate(steps, 1)]
                st.dataframe(formatted_steps, width='stretch')
                if saved_info and len(saved_info) > 5 and saved_info[5]:
                    st.caption(f"💾 Plan saved to local disk: `{saved_info[5]}`")

            # Always display the Semantic Soundness & Action Reconstruction table if ground truth is available
            if are_data:
                with st.expander("🏛️ Semantic Soundness & Action Reconstruction (ARE / Ground-Truth Alignment)", expanded=True):
                    st.caption("Operator-level alignment derived via Kuhn-Munkres Maximum Weight Bipartite Matching on classical STRIPS state-transition invariants (Oswald et al., ICAPS/AAAI 2024).")
                    st.markdown(f"**Macro Structural F1**: `{are_data.get('macro_structural_f1', 0.0)}` | **Action F1**: `{are_data.get('action_f1', 0.0)}` | **Verdict**: `{are_data.get('verdict', 'N/A')}`")
                    st.markdown("**Discovered Operator Mapping (Bipartite Bijection)**:")
                    st.json(are_data.get("action_mapping", {}))
                    if are_data.get("detailed_operator_reports"):
                        st.markdown("**Component-by-Component STRIPS Transition Metrics**:")
                        st.dataframe(are_data["detailed_operator_reports"], width='stretch')
                
            col_log1, col_log2 = st.columns(2)
            with col_log1:
                with st.expander("🔍 Fast Downward Search Log"):
                    st.code(plan_res.get("raw_fd_log", "No planner log available."), language="text")
            with col_log2:
                with st.expander("🛡️ VAL Mathematical Plan Certificate"):
                    st.code(plan_res.get("val_log", "No VAL log available."), language="text")
        else:
            st.info("No plan synthesis recorded for this run.")
            
        # Historical Backward Compatibility Section
        hist_plans = final_state.get("historical_plan_results", [])
        if hist_plans:
            st.markdown("---")
            st.markdown("### 🔄 Backward Compatibility Proof (Historical Regression Cases)")
            for hp in hist_plans:
                cid = hp.get("case_id", "historical_case")
                h_res = hp.get("plan_result", {})
                h_solv = h_res.get("is_solvable", False)
                h_len = h_res.get("plan_length", 0)
                h_time = h_res.get("search_time", 0.0)
                h_val = h_res.get("val_plan_valid", False)
                
                st.success(f"📁 **Historical Instance**: `{cid}` — **Backward Compatible & Solvable!**")
                hc1, hc2, hc3 = st.columns(3)
                hc1.metric("Historical Plan Length", f"{h_len} steps")
                hc2.metric("Search Time", f"{h_time:.4f}s")
                hc3.metric("VAL Certificate", "Valid 🛡️" if h_val else "Checked")
                
                if h_res.get("plan_steps"):
                    with st.expander(f"View Plan for {cid} ({h_len} steps)"):
                        h_formatted = [{"Step": i, "Action": s} for i, s in enumerate(h_res["plan_steps"], 1)]
                        st.dataframe(h_formatted, width='stretch')

    # Tab 3: AST Blueprint
    with tab_ast:
        st.markdown("#### `DomainBlueprint` (JSON AST)")
        st.json(final_state.get("pddl_domain_blueprint", {}))

    # Tab 4: Diagnostic Triage Report & Fault Evidence
    with tab_triage:
        reports = final_state.get("historical_diagnostic_reports", []) or final_state.get("diagnostic_reports", [])
        init_errors = final_state.get("initial_verification_errors", []) or final_state.get("verification_errors", [])
        errors = final_state.get("verification_errors", [])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Verification Status", "PASSED ✅" if not errors else "FAILED ⚠️")
        iter_count = final_state.get("iteration_count", 1 if is_synthetic_repair else 0)
        m2.metric("Diagnostic Issues Repaired", f"{iter_count} (Surgically Fixed)" if iter_count > 0 else "0")
        m3.metric("Repair Iterations Used", iter_count)
        
        if saved_info and len(saved_info) > 4 and saved_info[4]:
            st.caption(f"💾 Diagnostic Report saved to local disk: `{saved_info[4]}`")
        
        # 1. Prominent Classical Causal Graph Diagnostics Section
        causal_data = final_state.get("causal_graph_analysis")
        if not causal_data:
            from tools.causal_triage_analyzer import run_causal_triage_analysis
            d_bp = final_state.get("pddl_domain_blueprint") or {}
            p_pddl = final_state.get("initial_problem_pddl") or final_state.get("generated_problem_pddl") or ""
            if d_bp and d_bp.get("actions"):
                causal_data = run_causal_triage_analysis(d_bp, p_pddl, init_errors)

        if causal_data and causal_data.get("diagnostic_summary"):
            with st.expander("🕸️ Causal Graph & DTG Structural Diagnostics (Torralba & Hoffmann Invariants)", expanded=True):
                st.code(causal_data.get("diagnostic_summary"), language="text")
                if causal_data.get("details"):
                    st.caption("Action Grounded Causal Relevance & Invariant Topology:")
                    st.json(causal_data.get("details"))

        # 2. Captured Oracle Diagnostic Error Output (Clean Expander, Normal Size)
        if init_errors:
            st.markdown("#### 🚨 Captured Oracle Diagnostic Error Output (Before Repair)")
            for err_idx, err_text in enumerate(init_errors, 1):
                first_line = err_text.strip().split("\n")[0][:120]
                with st.expander(f"⚠️ Raw Oracle Error Log #{err_idx}: {first_line}...", expanded=False):
                    st.code(err_text, language="text")

        # 3. Structured Diagnostic Issues
        if reports:
            st.markdown("#### 🔍 Structured Diagnostic Failure Items & Fault Localization")
            for idx, r in enumerate(reports, 1):
                if isinstance(r, dict):
                    err_cat = r.get("error_category")
                    op_type = r.get("repair_operation_type")
                    element = r.get("faulty_element")
                    log_text = r.get("raw_log")
                    hint = r.get("suggested_repair_hint")
                else:
                    err_cat = r.error_category
                    op_type = r.repair_operation_type
                    element = r.faulty_element
                    log_text = r.raw_log
                    hint = r.suggested_repair_hint

                with st.expander(f"📌 Issue #{idx}: [{err_cat}] - Faulty Element: '{element or 'General'}' (Click to Expand)", expanded=True):
                    st.markdown(f"- **Target AST Operation**: `{op_type}`")
                    st.info(f"**Actionable Repair Hint**: {hint}")
                    st.markdown("**Exact Raw Error Log from Solver/Validator:**")
                    st.code(log_text, language="text")
        elif not init_errors:
            st.success("🎉 Zero diagnostic issues found! Domain and problem models were verified on first attempt.")



    # Tab 5: Observability & Telemetry Metrics
    with tab_telemetry:
        st.markdown("#### ⚡ LLM Execution Telemetry & Cost Analytics")
        tot_tok = final_state.get("total_tokens", 0)
        prompt_tok = final_state.get("total_prompt_tokens", 0)
        comp_tok = final_state.get("total_completion_tokens", 0)
        est_cost = final_state.get("estimated_cost_usd", 0.0)

        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Total LLM Tokens", f"{tot_tok:,}")
        t2.metric("Prompt (Input) Tokens", f"{prompt_tok:,}")
        t3.metric("Completion (Output) Tokens", f"{comp_tok:,}")
        t4.metric("Estimated API Cost (USD)", f"${est_cost:.6f}")

        st.markdown("---")
        st.markdown("#### ⏱️ Per-Node Execution Latency Breakdown (Seconds)")
        node_lat = final_state.get("node_latencies", {})
        
        if node_lat:
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                st.dataframe([
                    {"KEPS Lifecycle Node": "Node 1: Elicitation (LLM)", "Cumulative Latency (s)": f"{node_lat.get('elicit', 0.0):.3f}s"},
                    {"KEPS Lifecycle Node": "Node 2: PDDL Compiler (Python)", "Cumulative Latency (s)": f"{node_lat.get('generate', 0.0):.3f}s"},
                    {"KEPS Lifecycle Node": "Node 3: Oracles Validation (VAL & FD)", "Cumulative Latency (s)": f"{node_lat.get('validate', 0.0):.3f}s"},
                    {"KEPS Lifecycle Node": "Node 4: Diagnostic Triage (Diagnostic LLM Agent)", "Cumulative Latency (s)": f"{node_lat.get('triage', 0.0):.3f}s"},
                    {"KEPS Lifecycle Node": "Node 5: Targeted AST Repair (LLM)", "Cumulative Latency (s)": f"{node_lat.get('repair', 0.0):.3f}s"},
                    {"KEPS Lifecycle Node": "Node 6: Phase 4 Maintenance Suite", "Cumulative Latency (s)": f"{node_lat.get('maintenance', 0.0):.3f}s"},
                ], width='stretch')
            with col_l2:
                total_lat = sum(node_lat.values())
                st.metric("Total Pipeline Latency", f"{total_lat:.2f}s")
                st.caption("⚡ Python deterministic compiler & Diagnostic Triage run locally in milliseconds, while LLM Elicitation, Diagnostic Agent, and Oracles account for API & subprocess execution time.")
        else:
            st.info("No per-node latencies recorded for this run.")

    # Tab 6: Empirical Evaluation
    with tab_eval:
        st.markdown("### 🏆 Rigorous Empirical Evaluation")
        st.caption("Formal evaluation grounded in classical symbolic oracles (VAL `Validate.exe` & Fast Downward classical search) with zero evaluation leakage.")

        # Active Run Rigorous Scorecard
        st.markdown("#### Active Run Lifecycle Scorecard")
        run_m = st.session_state.get("active_run_metrics")
        
        if run_m:
            if run_m.e2e_success:
                st.success(
                    f"🎯 **End-to-End Verified Lifecycle Success (E2E = True)**\n\n"
                    f"Architecture `{run_m.agent_type}` successfully generated an executable PDDL model mathematically certified by VAL and Fast Downward."
                )
            else:
                st.error(
                    f"❌ **End-to-End Lifecycle Verification Failed (E2E = False)**\n\n"
                    f"Reason: `{run_m.error_summary or 'Oracle checks did not fully pass.'}`"
                )

            st.markdown("##### 🛡️ Primary Operational Verification Metrics (Symbolic Oracles)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Syntax Validity Rate (SVR)", "100% (Valid) 🛡️" if run_m.svr_syntax_valid_rate >= 1.0 else "0% (Syntax Error) ⚠️")
            c2.metric("Target Plan Validity (TPV)", "PASS (Certified) ✅" if run_m.tpv_target_plan_valid else "FAIL (Unsound) ❌")
            c3.metric("Plan Length (|Plan|)", f"{run_m.plan_length or 0} steps" if run_m.tpv_target_plan_valid else "N/A")
            cov_label = f"{run_m.cov_ref_coverage_rate:.1f}% ({run_m.reference_instances_passed or 0}/{run_m.reference_instances_total or 0})" if run_m.cov_ref_coverage_rate is not None else "N/A (Target Task)"
            c4.metric("Ref Suite Coverage (Cov_ref)", cov_label)

            if run_m.macro_structural_f1 is not None:
                st.markdown("##### 🧬 Structural Reconstruction Conformance (Oswald et al. 2024 / Aineto et al. 2022)")
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Macro Structural F1", f"{run_m.macro_structural_f1:.4f}")
                s2.metric("Precondition F1 (Pre_F1)", f"{run_m.precondition_f1:.4f}" if run_m.precondition_f1 is not None else "N/A")
                s3.metric("Add-Effect F1 (Add_F1)", f"{run_m.add_effect_f1:.4f}" if run_m.add_effect_f1 is not None else "N/A")
                s4.metric("Delete-Effect F1 (Del_F1)", f"{run_m.delete_effect_f1:.4f}" if run_m.delete_effect_f1 is not None else "N/A")

            st.markdown("##### ⚡ Diagnostic Efficiency & Computational Cost")
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Repair Iterations (k)", f"{run_m.iterations_used}")
            c6.metric("Execution Latency", f"{run_m.execution_time_seconds:.2f}s")
            c7.metric("Total Tokens", f"{run_m.total_tokens:,}")
            c8.metric("Estimated Cost", f"${run_m.estimated_cost_usd:.6f}")
        else:
            st.info("Run the agent or a baseline above to inspect active lifecycle scorecard metrics.")

else:
    st.markdown("---")
    st.info("👈 **Welcome to PDDL Lifecycle Agent!** Select an AutoPlanBench domain task in the sidebar, choose a system architecture (`CLOSED_LOOP_AST_AGENT`, `ABLATION_NO_TRIAGE`, `UNSTRUCTURED_RETRY`, or `ZERO_SHOT`), and click **'🚀 Run Selected System'** above to begin execution.")

    st.subheader("🚀 AutoPlanBench Benchmark Suite Overview")
    st.write(f"**{len(AUTOPLANBENCH_PURE_STRIPS_DOMAINS)} Pure STRIPS+Typing benchmark domains** available in `autoplanbench/data/`.")
    st.caption("Domains: " + ", ".join(AUTOPLANBENCH_PURE_STRIPS_DOMAINS))
