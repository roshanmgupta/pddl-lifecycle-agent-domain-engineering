"""
run_evaluation_new_constraints.py
Parallel Empirical Evaluation of the 17 Pure PDDL 2.1 AutoPlanBench Domains
Testing the Impact of the Three New Formal Constraints:
- Constraint 1: Operator Add-Precondition Disjointness & Delete Groundedness (Yang et al. ARMS 2007 A.1 & A.2)
- Constraint 2: Mutual-Exclusion State-Variable Invariant (SAS+ Frame Transition / Anti-Cloning)
- Constraint 3: Causal Producer-Consumer Type Signature Compatibility

Runs domains in parallel using ThreadPoolExecutor with process-isolated plan files.
Generates a side-by-side comparative analysis against previous baseline metrics.
"""

import sys
import os
import csv
import time
import json
import re
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.pure_strips_benchmarks import (
    AUTOPLANBENCH_PURE_STRIPS_DOMAINS,
    load_autoplanbench_original_domain_data
)
from benchmark.schema import BenchmarkTask, LifecycleTaskType
from eval.action_reconstruction import evaluate_action_reconstruction
from tools.symbolic_oracles import (
    run_val_validator,
    run_fast_downward_with_plan,
    validate_plan_semantic_soundness
)
from graph import pddl_lifecycle_graph

PRICE_PROMPT_PER_M = 0.15
PRICE_COMPLETION_PER_M = 0.60

def calculate_llm_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round(
        (prompt_tokens * PRICE_PROMPT_PER_M / 1_000_000) +
        (completion_tokens * PRICE_COMPLETION_PER_M / 1_000_000), 
        6
    )

def classify_behavioral_outcome(
    is_syntax_valid: bool,
    is_plan_valid: bool,
    val_plan_valid: bool,
    semantic_soundness_valid: bool,
    macro_f1: float,
    iters: int
) -> Tuple[str, str]:
    is_sound = (semantic_soundness_valid is True) or (macro_f1 >= 0.85)
    e2e_ok = is_syntax_valid and is_plan_valid and val_plan_valid and is_sound

    if e2e_ok:
        if iters == 1:
            return "A.1: First-Attempt Direct Success", "NONE"
        else:
            return "A.2: Refined Success via Feedback Loops", "RECOVERED"

    if not is_syntax_valid:
        return "B: Unparseable PDDL Syntax Failure", "SYNTAX_PARSE_ERROR"

    if is_syntax_valid and not is_plan_valid:
        return "C: Syntactically Valid but Planner Deadlock (Unsolvable)", "CAUSAL_REACHABILITY_DEADLOCK"

    if is_plan_valid and not val_plan_valid:
        return "D: Plan Generated but Fails VAL Self-Certification", "ACTION_EFFECT_CONTRADICTION"

    if not is_sound:
        return "E: Plan Execution Rejection on Standard Domain", "PRECONDITION_MISALIGNMENT"

    if iters >= 5:
        return "F: Iteration Budget Exhausted (Oscillation)", "UNRESOLVED_CONTRADICTION"

    return "G: Diagnostic Anomaly", "OTHER"

def load_previous_baseline_metrics() -> Dict[str, Dict[str, Any]]:
    baseline_file = "autoplanbench_master_metrics.csv"
    baseline = {}
    if not os.path.exists(baseline_file):
        return baseline

    try:
        with open(baseline_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("agent_type") == "CLOSED_LOOP_AST_AGENT":
                    d_name = row.get("domain", "").strip()
                    baseline[d_name] = {
                        "is_syntax_valid": row.get("is_syntax_valid") == "True",
                        "is_plan_valid": row.get("is_plan_valid") == "True",
                        "val_plan_valid": row.get("val_plan_valid") == "True",
                        "semantic_soundness_valid": row.get("semantic_soundness_valid") == "True",
                        "iterations_used": int(row.get("iterations_used", 1)),
                        "macro_structural_f1": float(row.get("macro_structural_f1", 0.0)),
                        "behavioral_code": row.get("behavioral_code", "")
                    }
    except Exception as e:
        print(f"[Warning] Failed to load baseline metrics: {e}")
    return baseline

def evaluate_single_domain(domain_name: str, max_iterations: int = 5) -> Dict[str, Any]:
    print(f"[{domain_name.upper()}] Starting autonomous elicitation & validation...", flush=True)
    start_t = time.time()
    
    out_dir = Path("eval_new_constraints_outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    eval_dom_file = str(out_dir / f"dom_{domain_name}.pddl")
    eval_prob_file = str(out_dir / f"prob_{domain_name}.pddl")
    eval_plan_file = str(out_dir / f"plan_{domain_name}.txt")
    ref_dom_file = str(out_dir / f"ref_dom_{domain_name}.pddl")
    ref_prob_file = str(out_dir / f"ref_prob_{domain_name}.pddl")

    # Load problem data
    domain_desc, instance_desc, req_text, ref_dom, ref_inst, hist_cases = load_autoplanbench_original_domain_data(domain_name)
    if not req_text or not ref_dom or not ref_inst:
        return {
            "domain": domain_name,
            "error": "Missing domain data",
            "is_syntax_valid": False,
            "is_plan_valid": False,
            "val_plan_valid": False,
            "semantic_soundness_valid": False
        }

    with open(ref_dom_file, "w", encoding="utf-8") as f:
        f.write(ref_dom)
    with open(ref_prob_file, "w", encoding="utf-8") as f:
        f.write(ref_inst)

    init_state = {
        "requirements": req_text,
        "pddl_domain_blueprint": {},
        "pddl_problem_blueprint": {},
        "generated_domain_pddl": "",
        "generated_problem_pddl": "",
        "verification_errors": [],
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "skip_triage": False,
        "historical_regression_suite": []
    }

    try:
        final_state = pddl_lifecycle_graph.invoke(init_state)
        gen_dom = final_state.get("generated_domain_pddl", "")
        gen_prob = final_state.get("generated_problem_pddl", "")
        iters = max(1, final_state.get("iteration_count", 1))
        p_tokens = final_state.get("total_prompt_tokens", 0)
        c_tokens = final_state.get("total_completion_tokens", 0)
        diag_reports = final_state.get("historical_diagnostic_reports", []) or final_state.get("diagnostic_reports", [])
        
        # Audit final domain and problem blueprint for remaining formal constraint violations
        from tools.causal_triage_analyzer import (
            detect_add_precondition_clashes_and_ungrounded_dels,
            detect_unbalanced_frame_transitions,
            detect_causal_type_mismatches
        )
        from tools.blueprint_parser import parse_pddl_domain_to_blueprint, parse_pddl_problem_to_blueprint
        try:
            dbp = parse_pddl_domain_to_blueprint(gen_dom)
            pbp = parse_pddl_problem_to_blueprint(gen_prob)
            c1_issues = detect_add_precondition_clashes_and_ungrounded_dels(dbp)
            c2_issues = detect_unbalanced_frame_transitions(dbp)
            c3_issues = detect_causal_type_mismatches(dbp, pbp)
            c1_count = len(c1_issues)
            c2_count = len(c2_issues)
            c3_count = len(c3_issues)
        except Exception:
            c1_count, c2_count, c3_count = 0, 0, 0

    except Exception as e:
        print(f"[{domain_name.upper()}] Crash: {e}", flush=True)
        return {
            "domain": domain_name,
            "error": str(e),
            "is_syntax_valid": False,
            "is_plan_valid": False,
            "val_plan_valid": False,
            "semantic_soundness_valid": False,
            "iterations_used": max_iterations,
            "macro_structural_f1": 0.0
        }

    # Save generated PDDL
    with open(eval_dom_file, "w", encoding="utf-8") as f:
        f.write(gen_dom)
    with open(eval_prob_file, "w", encoding="utf-8") as f:
        f.write(gen_prob)

    # 1. VAL Syntax Validation
    is_syntax_valid, val_syntax_log = run_val_validator(eval_dom_file, eval_prob_file)

    # 2. Fast Downward Plan Solvability with isolated plan file
    plan_res = run_fast_downward_with_plan(
        eval_dom_file,
        eval_prob_file,
        ground_truth_domain_path=None,
        plan_path=eval_plan_file
    )
    is_plan_valid = plan_res.get("is_solvable", False) or plan_res.get("plan_found", False)
    val_plan_valid = plan_res.get("val_plan_valid", False) or plan_res.get("val_valid", False)
    plan_steps = plan_res.get("plan_steps", [])
    plan_len = len(plan_steps)
    plan_cost = plan_res.get("plan_cost", 0)

    # 3. Semantic Soundness / Plan Transferability
    semantic_soundness_valid = False
    if is_plan_valid and os.path.exists(eval_plan_file):
        ss_valid, ss_log = validate_plan_semantic_soundness(
            ground_truth_domain_path=ref_dom_file,
            problem_path=ref_prob_file,
            plan_path=eval_plan_file,
            generated_domain_path=eval_dom_file
        )
        semantic_soundness_valid = ss_valid

    # 4. Action Reconstruction Metrics
    are_res = evaluate_action_reconstruction(ref_dom, gen_dom)
    macro_f1 = are_res.get("macro_structural_f1", 0.0)
    pre_f1 = are_res.get("mean_precondition_f1", 0.0)
    add_f1 = are_res.get("mean_add_effect_f1", 0.0)
    del_f1 = are_res.get("mean_delete_effect_f1", 0.0)
    act_f1 = are_res.get("action_f1", 0.0)

    # 5. Behavioral Classification
    beh_code, def_class = classify_behavioral_outcome(
        is_syntax_valid, is_plan_valid, val_plan_valid, semantic_soundness_valid, macro_f1, iters
    )

    elapsed = round(time.time() - start_t, 2)
    e2e_success = is_syntax_valid and is_plan_valid and val_plan_valid and (semantic_soundness_valid or macro_f1 >= 0.85)

    print(f"[{domain_name.upper()}] DONE ({elapsed}s) | Syntax: {is_syntax_valid} | Solved: {is_plan_valid} | VAL: {val_plan_valid} | Transfer: {semantic_soundness_valid} | F1: {macro_f1} | Iters: {iters} | C1/C2/C3: {c1_count}/{c2_count}/{c3_count}", flush=True)

    return {
        "domain": domain_name,
        "is_syntax_valid": is_syntax_valid,
        "is_plan_valid": is_plan_valid,
        "val_plan_valid": val_plan_valid,
        "semantic_soundness_valid": semantic_soundness_valid,
        "e2e_success": e2e_success,
        "iterations_used": iters,
        "macro_structural_f1": macro_f1,
        "precondition_f1": pre_f1,
        "add_effect_f1": add_f1,
        "delete_effect_f1": del_f1,
        "action_f1": act_f1,
        "plan_length": plan_len,
        "plan_cost": plan_cost,
        "c1_violations_caught": c1_count,
        "c2_violations_caught": c2_count,
        "c3_violations_caught": c3_count,
        "prompt_tokens": p_tokens,
        "completion_tokens": c_tokens,
        "total_tokens": p_tokens + c_tokens,
        "estimated_cost_usd": calculate_llm_cost(p_tokens, c_tokens),
        "execution_time_sec": elapsed,
        "behavioral_code": beh_code,
        "defect_class": def_class
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate updated agent with 3 new formal constraints.")
    parser.add_argument("--workers", type=int, default=3, help="Number of concurrent domain evaluation threads.")
    parser.add_argument("--domains", nargs="*", default=AUTOPLANBENCH_PURE_STRIPS_DOMAINS, help="Subset of domains to run.")
    parser.add_argument("--max_iters", type=int, default=5, help="Maximum repair iterations.")
    args = parser.parse_args()

    target_domains = [d for d in args.domains if d in AUTOPLANBENCH_PURE_STRIPS_DOMAINS]
    print("=" * 80)
    print(" AUTONOMOUS EMPIRICAL BENCHMARK: 17 PURE PDDL 2.1 DOMAINS (UPDATED CONSTRAINTS)")
    print(f" Workers: {args.workers} | Target Domains: {len(target_domains)}")
    print(f" Constraints: Constraint 1 (Yang A.1/A.2), Constraint 2 (SAS+ Frame), Constraint 3 (Causal Types)")
    print("=" * 80)

    baseline_metrics = load_previous_baseline_metrics()
    results = []

    start_all = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_domain = {
            executor.submit(evaluate_single_domain, d, args.max_iters): d 
            for d in target_domains
        }
        for future in as_completed(future_to_domain):
            d_name = future_to_domain[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"[FATAL] Domain {d_name} thread raised: {e}")

    total_time = round(time.time() - start_all, 2)
    results.sort(key=lambda x: target_domains.index(x["domain"]) if x["domain"] in target_domains else 999)

    # Write Master Metrics CSV
    out_csv = "eval_new_constraints_master_metrics.csv"
    fieldnames = [
        "domain", "is_syntax_valid", "is_plan_valid", "val_plan_valid", "semantic_soundness_valid",
        "e2e_success", "iterations_used", "macro_structural_f1", "precondition_f1", "add_effect_f1",
        "delete_effect_f1", "action_f1", "plan_length", "plan_cost", "c1_violations_caught",
        "c2_violations_caught", "c3_violations_caught", "prompt_tokens", "completion_tokens",
        "total_tokens", "estimated_cost_usd", "execution_time_sec", "behavioral_code", "defect_class"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            filtered = {k: r.get(k, "") for k in fieldnames}
            writer.writerow(filtered)

    # Write Comparison CSV
    comp_csv = "eval_new_constraints_comparison.csv"
    comp_fields = [
        "domain", "old_syntax", "new_syntax", "old_solved", "new_solved",
        "old_val_valid", "new_val_valid", "old_transfer", "new_transfer",
        "old_iters", "new_iters", "old_macro_f1", "new_macro_f1",
        "c1_caught", "c2_caught", "c3_caught", "status"
    ]
    
    comp_rows = []
    for r in results:
        d = r["domain"]
        old = baseline_metrics.get(d, {})
        old_solved = old.get("is_plan_valid", False)
        new_solved = r.get("is_plan_valid", False)
        old_f1 = old.get("macro_structural_f1", 0.0)
        new_f1 = r.get("macro_structural_f1", 0.0)
        
        status = "STABLE"
        if not old_solved and new_solved:
            status = "IMPROVED (NOW SOLVABLE)"
        elif new_f1 > old_f1 + 0.05:
            status = "IMPROVED (HIGHER F1)"
        elif old_solved and not new_solved:
            status = "REGRESSED"

        comp_rows.append({
            "domain": d,
            "old_syntax": old.get("is_syntax_valid", False),
            "new_syntax": r.get("is_syntax_valid", False),
            "old_solved": old_solved,
            "new_solved": new_solved,
            "old_val_valid": old.get("val_plan_valid", False),
            "new_val_valid": r.get("val_plan_valid", False),
            "old_transfer": old.get("semantic_soundness_valid", False),
            "new_transfer": r.get("semantic_soundness_valid", False),
            "old_iters": old.get("iterations_used", 1),
            "new_iters": r.get("iterations_used", 1),
            "old_macro_f1": round(old_f1, 4),
            "new_macro_f1": round(new_f1, 4),
            "c1_caught": r.get("c1_violations_caught", 0),
            "c2_caught": r.get("c2_violations_caught", 0),
            "c3_caught": r.get("c3_violations_caught", 0),
            "status": status
        })

    with open(comp_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=comp_fields)
        writer.writeheader()
        for cr in comp_rows:
            writer.writerow(cr)

    # Print Formatted Comparison Summary Table
    print("\n" + "=" * 90)
    print(" EMPIRICAL EVALUATION REPORT: IMPACT OF NEW CONSTRAINTS ON 17 BENCHMARK DOMAINS")
    print("=" * 90)
    print(f"{'DOMAIN':<22} | {'SOLVED':<12} | {'ITERS':<10} | {'STRUCT F1':<16} | {'C1/C2/C3':<10} | {'STATUS'}")
    print("-" * 90)

    old_total_solved = sum(1 for cr in comp_rows if cr["old_solved"])
    new_total_solved = sum(1 for cr in comp_rows if cr["new_solved"])
    old_avg_iters = round(sum(cr["old_iters"] for cr in comp_rows) / len(comp_rows), 2) if comp_rows else 0
    new_avg_iters = round(sum(cr["new_iters"] for cr in comp_rows) / len(comp_rows), 2) if comp_rows else 0
    old_avg_f1 = round(sum(cr["old_macro_f1"] for cr in comp_rows) / len(comp_rows), 4) if comp_rows else 0
    new_avg_f1 = round(sum(cr["new_macro_f1"] for cr in comp_rows) / len(comp_rows), 4) if comp_rows else 0
    total_c1 = sum(cr["c1_caught"] for cr in comp_rows)
    total_c2 = sum(cr["c2_caught"] for cr in comp_rows)
    total_c3 = sum(cr["c3_caught"] for cr in comp_rows)

    for cr in comp_rows:
        d = cr["domain"]
        s_str = f"{cr['old_solved']} -> {cr['new_solved']}"
        i_str = f"{cr['old_iters']} -> {cr['new_iters']}"
        f_str = f"{cr['old_macro_f1']:.2f} -> {cr['new_macro_f1']:.2f}"
        c_str = f"{cr['c1_caught']}/{cr['c2_caught']}/{cr['c3_caught']}"
        print(f"{d:<22} | {s_str:<12} | {i_str:<10} | {f_str:<16} | {c_str:<10} | {cr['status']}")

    print("-" * 90)
    total_d = len(comp_rows) if len(comp_rows) > 0 else 1
    print(f"SUMMARY AGGREGATES across {len(comp_rows)} domains:")
    print(f"  - Plan Solvability Rate (PSR) : {old_total_solved}/{len(comp_rows)} ({old_total_solved/total_d*100:.1f}%) -> {new_total_solved}/{len(comp_rows)} ({new_total_solved/total_d*100:.1f}%)")
    print(f"  - Average Iterations Used    : {old_avg_iters} -> {new_avg_iters}")
    print(f"  - Macro Structural F1        : {old_avg_f1:.4f} -> {new_avg_f1:.4f}")
    print(f"  - Total Constraint Violations: C1 (Add Overlap)={total_c1} | C2 (Frame/Cloning)={total_c2} | C3 (Causal Types)={total_c3}")
    print(f"  - Total Runtime (Parallel)   : {total_time}s")
    print(f"Outputs written to: '{out_csv}' and '{comp_csv}'.")
    print("=" * 90)

if __name__ == "__main__":
    main()
