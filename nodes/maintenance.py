import os
import re
import tempfile
from typing import Dict, Any, List
from schemas.pddl_blueprint import (
    DiagnosticReport,
    ErrorCategory,
    RepairOperationType,
    HistoricalProblemCase
)
from nodes.generation import compile_pddl_programmatically
from tools.symbolic_oracles import run_val_validator, run_fast_downward

def run_maintenance_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 4: Domain Model Evolution & Solvability Preservation Node.
    
    In Classical Automated Planning (Fox & Long 2003; Haslum et al. 2019; McCluskey et al. 2017),
    this node verifies Domain Subsumption: checking that an evolved domain Sigma' preserves plan reachability
    (solvability) across the distribution of canonical benchmark problem instances Pi_ref = {P_1, ..., P_k}.
    """
    import time
    start_t = time.time()
    domain_blueprint = state.get("pddl_domain_blueprint")
    domain_pddl = state.get("generated_domain_pddl")
    baseline_suite = (
        state.get("baseline_benchmark_problems")
        or state.get("benchmark_problem_distribution")
        or []
    )

    if not baseline_suite:
        print("[Solvability Preservation]: No baseline benchmark problem instances provided. Skipping solvability preservation check.")
        return state

    print(f"[Solvability Preservation Check]: Verifying plan reachability across {len(baseline_suite)} canonical baseline benchmark problem instance(s)...")

    # Ensure domain_blueprint is a dictionary if passed as a Pydantic model
    if hasattr(domain_blueprint, "model_dump"):
        domain_blueprint = domain_blueprint.model_dump()
    elif hasattr(domain_blueprint, "dict"):
        domain_blueprint = domain_blueprint.dict()

    # Ensure domain PDDL is compiled
    if not domain_pddl and domain_blueprint:
        domain_pddl = compile_pddl_programmatically(domain_blueprint)

    if not domain_pddl:
        print("[Solvability Preservation Warning]: No compiled domain PDDL available for solvability verification.")
        return state

    # Isolate Phase 4 error collectors to prevent inheriting stale errors
    verification_errors = []
    diagnostic_reports = []
    has_regression_failure = False

    with tempfile.TemporaryDirectory() as temp_dir:
        domain_file_path = os.path.join(temp_dir, "domain.pddl")
        with open(domain_file_path, "w", encoding="utf-8") as f:
            f.write(domain_pddl)

        for case_idx, case_data in enumerate(baseline_suite):
            if isinstance(case_data, dict):
                case_id = case_data.get("case_id", f"benchmark_instance_{case_idx+1}")
                hist_prob_pddl = case_data.get("problem_pddl") or case_data.get("raw_pddl") or ""
            elif isinstance(case_data, str):
                # Raw PDDL problem string
                # Extract problem name if available
                prob_name_m = re.search(r"\(\s*problem\s+([a-zA-Z0-9_\-]+)\s*\)", case_data, re.IGNORECASE)
                case_id = prob_name_m.group(1) if prob_name_m else f"benchmark_instance_{case_idx+1}"
                hist_prob_pddl = case_data
            elif hasattr(case_data, "problem_pddl"):
                case_id = getattr(case_data, "case_id", f"benchmark_instance_{case_idx+1}")
                hist_prob_pddl = getattr(case_data, "problem_pddl", "")
            else:
                continue

            if not hist_prob_pddl:
                continue

            # Ensure problem (:domain ...) strictly matches active domain_blueprint domain_name
            if domain_blueprint and "domain_name" in domain_blueprint:
                hist_prob_pddl = re.sub(
                    r"\(\s*:domain\s+[a-zA-Z0-9_\-]+\s*\)",
                    f"(:domain {domain_blueprint['domain_name']})",
                    hist_prob_pddl,
                    count=1,
                    flags=re.IGNORECASE
                )

            problem_file_path = os.path.join(temp_dir, f"problem_{case_id}.pddl")
            with open(problem_file_path, "w", encoding="utf-8") as f:
                f.write(hist_prob_pddl)

            # Step 1: Check Syntax & Types with VAL Oracle
            val_ok, val_log = run_val_validator(domain_file_path, problem_file_path)
            if not val_ok:
                err_text = f"[SOLVABILITY_PRESERVATION_BREAKAGE]: Benchmark instance '{case_id}' failed VAL syntax/type validation under evolved domain.\nLog: {val_log}"
                print(f"  [FAIL] {err_text}")
                missing_pred_m = re.search(r"Predicate\s+(\w+)\s+not found", val_log)
                hint = f"Benchmark instance '{case_id}' failed validation with evolved domain. Check for broken predicate definitions or arities."
                if missing_pred_m:
                    pname = missing_pred_m.group(1)
                    hint = f"Benchmark instance '{case_id}' failed because predicate '{pname}' is missing in the evolved domain. Declare '({pname} ...)' in domain 'predicates' with matching argument types to preserve backward solvability."

                verification_errors.append(err_text)
                diagnostic_reports.append(
                    DiagnosticReport(
                        error_category=ErrorCategory.HISTORICAL_REGRESSION,
                        repair_operation_type=RepairOperationType.REGRESSION_BACKWARD_COMPATIBILITY,
                        faulty_element=case_id,
                        raw_log=val_log,
                        suggested_repair_hint=hint
                    )
                )
                has_regression_failure = True
                continue

            # Step 2: Check Plan Reachability with Fast Downward Planning Oracle
            from tools.symbolic_oracles import run_fast_downward_with_plan
            plan_res = run_fast_downward_with_plan(domain_file_path, problem_file_path)
            fd_ok = plan_res["is_solvable"]
            fd_log = plan_res.get("raw_fd_log", "")
            
            if not fd_ok:
                err_text = f"[SOLVABILITY_PRESERVATION_BREAKAGE]: Benchmark instance '{case_id}' became unsolvable under evolved domain (Causal Reachability Deadlock).\nLog: {fd_log}"
                print(f"  [FAIL] {err_text}")
                verification_errors.append(err_text)
                diagnostic_reports.append(
                    DiagnosticReport(
                        error_category=ErrorCategory.HISTORICAL_REGRESSION,
                        repair_operation_type=RepairOperationType.REGRESSION_BACKWARD_COMPATIBILITY,
                        faulty_element=case_id,
                        raw_log=fd_log,
                        suggested_repair_hint=f"Benchmark instance '{case_id}' became unsolvable with evolved domain. Ensure newly added action preconditions do not over-constrain baseline state transitions (separate new capability into a dedicated specialized action schema)."
                    )
                )
                has_regression_failure = True
            else:
                print(f"  [PASS] Benchmark instance '{case_id}' plan reachability preserved (Solvable=True)!")
                hist_plans = list(state.get("historical_plan_results", []))
                hist_plans.append({
                    "case_id": case_id,
                    "plan_result": plan_res
                })
                state["historical_plan_results"] = hist_plans

    if has_regression_failure:
        state["verification_errors"] = verification_errors
        state["diagnostic_reports"] = diagnostic_reports
    else:
        state["verification_errors"] = []
        state["diagnostic_reports"] = []
        print("[Solvability Preservation Certified]: All benchmark problem instances remain solvable under evolved domain!")
        
    latencies = state.get("node_latencies", {})
    latencies["maintenance"] = round(latencies.get("maintenance", 0.0) + (time.time() - start_t), 3)
    state["node_latencies"] = latencies
    return state
