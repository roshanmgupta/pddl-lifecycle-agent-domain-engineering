import os
from typing import TypedDict, List, Any, Dict, Optional
from langgraph.graph import StateGraph, END
from nodes.elicitation import run_elicitation_node
from nodes.evolution import run_evolution_node
from nodes.generation import run_generation_node
from nodes.fault_localization import FaultLocalizationNode
from nodes.repair import run_repair_node
from nodes.maintenance import run_maintenance_node
from tools.symbolic_oracles import run_val_validator, run_fast_downward

# 1. Shared Memory AgentState Contract
class AgentState(TypedDict, total=False):
    requirements: str
    pddl_domain_blueprint: dict
    initial_pddl_domain_blueprint: dict
    generated_domain_pddl: str
    generated_problem_pddl: str
    initial_domain_pddl: str
    initial_problem_pddl: str
    reference_domain_pddl: str
    gold_reference_plan_file: str
    is_evolution_task: bool
    is_synthetic_repair: bool
    skip_elicitation: bool
    skip_fault_localization: bool
    system_type: str
    verification_errors: List[str]
    initial_verification_errors: List[str]
    diagnostic_reports: List[dict]
    historical_diagnostic_reports: List[dict]
    formatted_diagnostic_feedback: str
    historical_regression_suite: List[dict]
    baseline_benchmark_problems: List[Any]
    benchmark_problem_distribution: List[Any]
    evolution_target_problem_pddl: str
    evolution_iteration_count: int
    iteration_count: int
    max_iterations: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    node_latencies: dict
    generated_plan_result: dict
    historical_plan_results: List[dict]
    causal_graph_analysis: dict

# 2. Validation Oracle Execution Node
def run_full_validation_node(state: AgentState) -> AgentState:
    import time
    start_t = time.time()
    pddl_code = state.get("generated_domain_pddl", "")
    if not pddl_code and state.get("initial_domain_pddl"):
        pddl_code = state.get("initial_domain_pddl", "")
        state["generated_domain_pddl"] = pddl_code

    problem_pddl_code = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    if problem_pddl_code:
        state["generated_problem_pddl"] = problem_pddl_code

    # Ensure Domain AST blueprint exists for fault localization & repair
    if not state.get("pddl_domain_blueprint") and pddl_code:
        from tools.blueprint_parser import parse_pddl_domain_to_blueprint
        state["pddl_domain_blueprint"] = parse_pddl_domain_to_blueprint(pddl_code)

    # Save temporary domain file to disk
    from config.paths import get_temp_domain_path, get_temp_problem_path
    temp_domain_file = get_temp_domain_path()
    with open(temp_domain_file, "w", encoding="utf-8") as f:
        f.write(pddl_code)
        
    temp_problem_file = None
    if problem_pddl_code:
        temp_problem_file = get_temp_problem_path()
        with open(temp_problem_file, "w", encoding="utf-8") as f:
            f.write(problem_pddl_code)

    # -- Oracle 1: VAL for Syntax/Semantic Check --
    is_valid_syntax, val_log = run_val_validator(temp_domain_file, temp_problem_file)
    
    if not is_valid_syntax:
        err_msg = "VAL Error: " + val_log
        state["verification_errors"] = [err_msg]
        if not state.get("initial_verification_errors"):
            state["initial_verification_errors"] = [err_msg]
        latencies = state.get("node_latencies", {})
        latencies["validate"] = round(latencies.get("validate", 0.0) + (time.time() - start_t), 3)
        state["node_latencies"] = latencies
        return state

    # -- Oracle 2 & 3: Fast Downward for Solvability Check & Closed-Loop Plan Transfer Soundness --
    if temp_problem_file:
        from tools.symbolic_oracles import run_fast_downward_with_plan
        from config.paths import get_temp_domain_path
        ref_dom_code = state.get("reference_domain_pddl")
        ref_dom_file = None
        if ref_dom_code:
            ref_dom_file = get_temp_domain_path().replace(".pddl", "_ref.pddl")
            with open(ref_dom_file, "w", encoding="utf-8") as rf:
                rf.write(ref_dom_code)

        plan_res = run_fast_downward_with_plan(temp_domain_file, temp_problem_file, ground_truth_domain_path=ref_dom_file)
        state["generated_plan_result"] = plan_res
        
        if not plan_res["is_solvable"]:
            fd_log = plan_res.get("raw_fd_log", "")
            is_translate_crash = any(k in fd_log.lower() for k in ["translate exit code: 30", "translate exit code: 31", "undefined variable", "parsing error", "syntax error:"])
            if plan_res.get("timed_out"):
                # Search budget exhausted: NOT a proof of unsolvability, so it must not be
                # reported as "Could not find a plan" (which fault localization treats as a proven deadlock).
                err_msg = "Planner Error: " + fd_log
            elif is_translate_crash:
                err_msg = "Translator Syntax Error: " + fd_log
            else:
                err_msg = "Planner Error: Could not find a plan. " + fd_log
            state["verification_errors"] = [err_msg]
            if not state.get("initial_verification_errors"):
                state["initial_verification_errors"] = [err_msg]
            latencies = state.get("node_latencies", {})
            latencies["validate"] = round(latencies.get("validate", 0.0) + (time.time() - start_t), 3)
            state["node_latencies"] = latencies
            return state

        def _extract_val_failure_trace(raw_log: str) -> str:
            import re
            stripped = re.sub(
                r"Type-checking\s+[a-zA-Z0-9_\-]+\s*\.\.\.action passes type checking\.",
                "",
                raw_log or ""
            )
            collapsed = re.sub(r"\s+", " ", stripped).strip()
            for marker in ("Plan failed", "Goal not satisfied", "The goal was not achieved", "Plan Repair Advice", "Plan Transfer Arity Mismatch"):
                idx = collapsed.find(marker)
                if idx != -1:
                    start_idx = max(0, idx - 300)
                    return collapsed[start_idx:start_idx + 1800]
            return collapsed[-1500:] if len(collapsed) > 1500 else collapsed

        transfer_errors = []

        # -- Oracle 3: Plan Feasibility (Soundness) Check on Reference Domain --
        if ref_dom_file and not plan_res.get("feasibility_valid"):
            clean_val_log = _extract_val_failure_trace(plan_res.get("feasibility_log", ""))
            err_msg = (
                f"Plan Feasibility Rejection on Standard Domain: The synthesized plan solved generated domain D_gen, "
                f"but failed execution when transferred to reference domain D_gold on problem P_gold! "
                f"VAL Oracle Diagnostic Trace: {clean_val_log}\n"
                f"Action schemas in D_gen are likely missing necessary preconditions (trivial model trap) "
                f"or producing effects that violate physical domain invariants."
            )
            transfer_errors.append(err_msg)

        # -- Oracle 4: Plan Interpretability (Completeness) Check on Generated Domain --
        gold_plan_file = state.get("gold_reference_plan_file")
        if ref_dom_file and (not gold_plan_file or not os.path.exists(gold_plan_file)):
            from config.paths import get_temp_domain_path
            cached_gold_plan = get_temp_domain_path().replace(".pddl", "_gold_plan.txt")
            gold_fd = run_fast_downward_with_plan(ref_dom_file, temp_problem_file, plan_path=cached_gold_plan)
            raw_sas = gold_fd.get("raw_sas_plan_text", "")
            steps = gold_fd.get("plan_steps", [])
            if raw_sas:
                with open(cached_gold_plan, "w", encoding="utf-8") as gpf:
                    gpf.write(raw_sas)
            elif steps:
                with open(cached_gold_plan, "w", encoding="utf-8") as gpf:
                    for stp in steps:
                        gpf.write(stp + "\n")
            if os.path.exists(cached_gold_plan):
                gold_plan_file = cached_gold_plan
                state["gold_reference_plan_file"] = gold_plan_file

        if ref_dom_file and gold_plan_file and os.path.exists(gold_plan_file):
            from tools.symbolic_oracles import validate_plan_semantic_soundness
            interp_ok, interp_log = validate_plan_semantic_soundness(
                ground_truth_domain_path=temp_domain_file,
                problem_path=temp_problem_file,
                plan_path=gold_plan_file,
                generated_domain_path=ref_dom_file
            )
            if not interp_ok:
                clean_interp_log = _extract_val_failure_trace(interp_log)
                err_msg = (
                    f"Plan Interpretability Rejection on Generated Domain: The standard reference plan pi_gold "
                    f"failed execution on the generated domain D_gen! "
                    f"VAL Oracle Diagnostic Trace: {clean_interp_log}\n"
                    f"Action schemas in D_gen are likely over-constrained with extraneous preconditions (completeness failure) "
                    f"or parameter arities/names do not preserve reference plan operations."
                )
                transfer_errors.append(err_msg)

        if transfer_errors:
            state["verification_errors"] = transfer_errors
            if not state.get("initial_verification_errors"):
                state["initial_verification_errors"] = list(transfer_errors)
            latencies = state.get("node_latencies", {})
            latencies["validate"] = round(latencies.get("validate", 0.0) + (time.time() - start_t), 3)
            state["node_latencies"] = latencies
            return state

    # If both oracles pass, clear current active errors and diagnostic reports (historical reports remain preserved in historical_diagnostic_reports)
    state["verification_errors"] = []
    state["diagnostic_reports"] = []
    state["formatted_diagnostic_feedback"] = ""
    latencies = state.get("node_latencies", {})
    latencies["validate"] = round(latencies.get("validate", 0.0) + (time.time() - start_t), 3)
    state["node_latencies"] = latencies
    return state

MAX_ITERATIONS_DEFAULT = 5

# 3. Router Functions for Closed Loop Workflow
def route_after_validation(state: AgentState) -> str:
    """If primary validation fails, route directly to fault_localization (or END if ZERO_SHOT).
    If validation passes and baseline benchmark suite is present, route to maintenance; else complete at END."""
    errors = state.get("verification_errors", [])
    if errors:
        if state.get("system_type") == "ZERO_SHOT":
            print("[ZERO_SHOT]: Target validation failed. Halting workflow immediately (single-pass baseline).")
            return END
        return "fault_localization"
    suite = (
        state.get("baseline_benchmark_problems")
        or state.get("benchmark_problem_distribution")
        or state.get("historical_regression_suite")
        or []
    )
    if suite:
        return "maintenance"
    print("[SUCCESS]: Model successfully verified by Oracles (VAL & Fast Downward)!")
    return END

def route_after_maintenance(state: AgentState) -> str:
    """If Phase 4 maintenance detected regression breakages, route to fault_localization (or END if ZERO_SHOT).
    Otherwise, complete successfully."""
    errors = state.get("verification_errors", [])
    if errors:
        if state.get("system_type") == "ZERO_SHOT":
            print("[ZERO_SHOT]: Phase 4 maintenance regression detected. Halting workflow immediately (single-pass baseline).")
            return END
        return "fault_localization"
    print("[SUCCESS]: Model successfully verified by Oracles & Phase 4 Maintenance Suite!")
    return END

def route_after_fault_localization(state: AgentState) -> str:
    """Routing logic after FaultLocalizationNode."""
    errors = state.get("verification_errors", [])
    reports = state.get("diagnostic_reports", [])
    
    if not errors and not reports:
        print("[SUCCESS]: Model successfully verified by Oracles & Phase 4 Maintenance Suite!")
        return END           # Validation & Maintenance passed!

    if state.get("system_type") == "ZERO_SHOT":
        print("[ZERO_SHOT]: Single-pass baseline guard. Terminating at END without repair.")
        return END

    # Guard: Halt only if the oracle binary itself is missing on the host OS (not an AST issue miscategorized by LLM)
    is_true_binary_failure = any(
        isinstance(r, dict)
        and (r.get("error_category") == "SYSTEM_ORACLE_ERROR" or str(r.get("error_category")).endswith("SYSTEM_ORACLE_ERROR"))
        and (
            r.get("faulty_element") in ["VAL Oracle Binary", "Fast Downward Binary"]
            or any(k in str(r.get("raw_log", "")).lower() for k in ["binary not found", "executable not found", "cannot find the file specified", "failed to execute val binary", "failed to execute fast downward"])
        )
        for r in reports
    )
    if is_true_binary_failure:
        print("[CRITICAL HALT]: System Oracle executable binary missing on host. Halting repair loop.")
        return END
        
    current_iteration = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", MAX_ITERATIONS_DEFAULT)
    
    if current_iteration >= max_iters:
        print(f"[WARNING]: Max repair iterations ({max_iters}) reached ({current_iteration}/{max_iters}). Terminating repair loop.")
        return END           # Max iteration guard triggered
        
    print(f"[ROUTER]: Routing to repair node (Next Repair Iteration: {current_iteration + 1}/{max_iters})")
    return "repair"          # Loop to repair node for targeted AST modification

def route_initial_entry(state: AgentState) -> str:
    """
    Routes the workflow based on task type:
    1. Phase 4 Domain Evolution tasks route to 'evolve' (Action Model Delta Synthesis).
    2. Category B Synthetic Fault Repair tasks with pre-loaded flawed domains route to 'validate'.
    3. Category A Elicitation tasks route to 'elicit'.
    """
    if state.get("is_evolution_task"):
        print("[GRAPH ROUTER]: Phase 4 Evolution task detected. Routing to Action Model Evolution node.")
        return "evolve"
    if (
        state.get("is_synthetic_repair")
        or state.get("skip_elicitation")
        or (
            state.get("generated_domain_pddl")
            and (state.get("verification_errors") or not state.get("requirements"))
        )
        or (state.get("generated_domain_pddl") and state.get("pddl_domain_blueprint"))
    ):
        print("[GRAPH ROUTER]: Pre-loaded domain detected for Repair. Bypassing Phase 1 Elicitation -> Starting at Validation.")
        return "validate"
    return "elicit"

# 4. Construct LangGraph Workflow
builder = StateGraph(AgentState)

builder.add_node("elicit", run_elicitation_node)
builder.add_node("evolve", run_evolution_node)
builder.add_node("generate", run_generation_node)
builder.add_node("validate", run_full_validation_node)
builder.add_node("maintenance", run_maintenance_node)
builder.add_node("fault_localization", FaultLocalizationNode)
builder.add_node("repair", run_repair_node)

builder.set_conditional_entry_point(
    route_initial_entry,
    {
        "elicit": "elicit",
        "evolve": "evolve",
        "validate": "validate"
    }
)
builder.add_edge("elicit", "generate")
builder.add_edge("evolve", "generate")
builder.add_edge("generate", "validate")
builder.add_conditional_edges("validate", route_after_validation)
builder.add_conditional_edges("maintenance", route_after_maintenance)
builder.add_conditional_edges("fault_localization", route_after_fault_localization)
builder.add_edge("repair", "generate")

pddl_lifecycle_graph = builder.compile()