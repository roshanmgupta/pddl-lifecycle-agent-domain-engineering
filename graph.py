"""
graph.py
Canonical LangGraph Closed-Loop Lifecycle Workflow for PDDL Engineering.
Focuses strictly on Formulation (H1) and Layered Fault Repair (H2).
"""

import os
from typing import TypedDict, List, Any, Dict, Optional
from langgraph.graph import StateGraph, END

from nodes.elicitation import run_elicitation_node
from nodes.langgraph_compilation import run_compilation_node
from nodes.validation import run_validation_node
from nodes.fault_localization import FaultLocalizationNode
from nodes.repair import run_repair_node


# 1. Shared Memory AgentState Contract
class AgentState(TypedDict, total=False):
    requirements: str
    pddl_domain_representation: dict
    initial_pddl_domain_representation: dict
    oracle_trace: dict
    repair_feedback_log: List[dict]
    generated_domain_pddl: str
    generated_problem_pddl: str
    initial_domain_pddl: str
    initial_problem_pddl: str
    reference_domain_pddl: str
    reference_problems: List[str]
    reference_gold_plans: List[str]
    reference_problem_names: List[str]
    gold_reference_plan_file: str
    is_synthetic_repair: bool
    skip_elicitation: bool
    skip_fault_localization: bool
    system_type: str
    verification_errors: List[str]
    initial_verification_errors: List[str]
    diagnostic_reports: List[dict]
    historical_diagnostic_reports: List[dict]
    formatted_diagnostic_feedback: str
    iteration_count: int
    max_iterations: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    node_latencies: dict
    generated_plan_result: dict
    causal_graph_analysis: dict


MAX_ITERATIONS_DEFAULT = 5


# 2. Router Functions for Closed Loop Workflow
def route_after_validation(state: AgentState) -> str:
    """If primary validation fails, route directly to fault_localization (or END if ZERO_SHOT).
    If validation passes, complete at END."""
    errors = state.get("verification_errors", [])
    if errors:
        if state.get("system_type") == "ZERO_SHOT":
            print("[ZERO_SHOT]: Target validation failed. Halting workflow immediately (single-pass baseline).", flush=True)
            return END
        return "fault_localization"
    print("[SUCCESS]: Model successfully verified by Oracles (VAL & Fast Downward)!", flush=True)
    return END


def route_after_fault_localization(state: AgentState) -> str:
    """Routing logic after FaultLocalizationNode."""
    errors = state.get("verification_errors", [])
    reports = state.get("diagnostic_reports", [])
    
    if not errors and not reports:
        print("[SUCCESS]: Model successfully verified by Oracles (VAL & Fast Downward)!", flush=True)
        return END           # Validation passed!

    if state.get("system_type") == "ZERO_SHOT":
        print("[ZERO_SHOT]: Single-pass baseline guard. Terminating at END without repair.", flush=True)
        return END

    # Guard: Halt only if the oracle binary itself is missing on the host OS
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
        print("[CRITICAL HALT]: System Oracle executable binary missing on host. Halting repair loop.", flush=True)
        return END
        
    current_iteration = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", MAX_ITERATIONS_DEFAULT)
    
    if current_iteration >= max_iters:
        print(f"[WARNING]: Max repair iterations ({max_iters}) reached ({current_iteration}/{max_iters}). Terminating repair loop.", flush=True)
        return END           # Max iteration guard triggered
        
    print(f"[ROUTER]: Routing to repair node (Next Repair Iteration: {current_iteration + 1}/{max_iters})", flush=True)
    return "repair"          # Loop to repair node for targeted AST modification


def route_initial_entry(state: AgentState) -> str:
    """Routes initial entry point based on task configuration."""
    if (
        state.get("is_synthetic_repair")
        or state.get("skip_elicitation")
        or (
            state.get("generated_domain_pddl")
            and (state.get("verification_errors") or not state.get("requirements"))
        )
        or (state.get("generated_domain_pddl") and state.get("pddl_domain_representation"))
    ):
        print("[GRAPH ROUTER]: Pre-loaded domain detected for Repair. Bypassing Phase 1 Elicitation -> Starting at Validation.", flush=True)
        return "validate"
    return "elicit"


# 3. Construct Canonical LangGraph Workflow
builder = StateGraph(AgentState)

builder.add_node("elicit", run_elicitation_node)
builder.add_node("compile", run_compilation_node)
builder.add_node("validate", run_validation_node)
builder.add_node("fault_localization", FaultLocalizationNode)
builder.add_node("repair", run_repair_node)

builder.set_conditional_entry_point(
    route_initial_entry,
    {
        "elicit": "elicit",
        "validate": "validate"
    }
)
builder.add_edge("elicit", "compile")
builder.add_edge("compile", "validate")
builder.add_conditional_edges("validate", route_after_validation)
builder.add_conditional_edges("fault_localization", route_after_fault_localization)
builder.add_edge("repair", "compile")

pddl_lifecycle_graph = builder.compile()
