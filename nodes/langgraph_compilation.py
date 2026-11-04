"""
nodes/langgraph_compilation.py
LangGraph lifecycle node for compiling the DomainBlueprint AST into concrete PDDL domain text.
Manages state synchronization, domain naming alignment, and node latency tracking.
The pure deterministic compilation engine lives in nodes/ast_to_pddl_compiler.py.
"""

import time
from typing import Dict, Any
from nodes.pddl_to_ast_parser import extract_pddl_problem_metadata
from nodes.ast_to_pddl_compiler import compile_pddl_programmatically, synchronize_ast_predicate_symbols


def run_compilation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Programmatically compiles the DomainBlueprint into PDDL domain code within the LangGraph workflow."""
    start_t = time.time()
    blueprint_data = state.get("pddl_domain_blueprint", {})
    if hasattr(blueprint_data, "model_dump"):
        blueprint_data = blueprint_data.model_dump()
    elif hasattr(blueprint_data, "dict"):
        blueprint_data = blueprint_data.dict()

    problem_pddl = state.get("initial_problem_pddl") or state.get("generated_problem_pddl") or ""
    if problem_pddl:
        prob_meta = extract_pddl_problem_metadata(problem_pddl)
        if prob_meta.get("domain_name") and isinstance(blueprint_data, dict):
            blueprint_data["domain_name"] = prob_meta["domain_name"]
            state["pddl_domain_blueprint"] = blueprint_data
        state["generated_problem_pddl"] = problem_pddl
        if "initial_problem_pddl" not in state or not state["initial_problem_pddl"]:
            state["initial_problem_pddl"] = problem_pddl

    compiled_pddl = compile_pddl_programmatically(blueprint_data, problem_pddl=problem_pddl)
    state["generated_domain_pddl"] = compiled_pddl
    if "initial_domain_pddl" not in state or not state["initial_domain_pddl"]:
        state["initial_domain_pddl"] = compiled_pddl
    if "initial_pddl_domain_blueprint" not in state or not state["initial_pddl_domain_blueprint"]:
        state["initial_pddl_domain_blueprint"] = blueprint_data

    latencies = state.get("node_latencies", {})
    latencies["compile"] = round(latencies.get("compile", 0.0) + (time.time() - start_t), 3)
    state["node_latencies"] = latencies
    return state
