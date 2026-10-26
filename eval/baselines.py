import sys
import os
import re
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.schema import BenchmarkTask, LifecycleTaskType
from config.model_config import invoke_raw_llm_with_telemetry
from tools.symbolic_oracles import run_val_validator, run_fast_downward_with_plan
from config.paths import get_eval_output_dir

def extract_pddl_blocks(raw_text: str) -> Tuple[str, str]:
    """Extracts domain.pddl and problem.pddl code blocks from raw LLM output text."""
    domain_pddl = ""
    problem_pddl = ""

    # Match (define (domain ...) ...) blocks
    domain_match = re.search(r'\(define\s*\(domain.*?\n\)', raw_text, re.DOTALL | re.IGNORECASE)
    if not domain_match:
        # Fallback: extract code block tagged as pddl or lisp
        code_blocks = re.findall(r'```(?:pddl|lisp)?\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
        for block in code_blocks:
            if "(domain" in block.lower():
                domain_pddl = block.strip()
            elif "(problem" in block.lower():
                problem_pddl = block.strip()
    else:
        domain_pddl = domain_match.group(0).strip()

    problem_match = re.search(r'\(define\s*\(problem.*?\n\)', raw_text, re.DOTALL | re.IGNORECASE)
    if problem_match:
        problem_pddl = problem_match.group(0).strip()

    return domain_pddl, problem_pddl

def run_zero_shot_baseline(task: BenchmarkTask) -> Dict[str, Any]:
    """
    Baseline 1: Zero-Shot Direct LLM Generation / Single-Pass Repair.
    Requests raw PDDL domain code (D_gen) directly from natural language prompt without Pydantic AST or validation loops,
    holding the ground-truth problem instance (P_gold) fixed.
    Strictly NO fallback to ground truth domain.
    """
    if getattr(task, "initial_domain_pddl", None):
        prompt = f"""You are an automated PDDL domain debugger and repair system.
Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

Target Problem PDDL:
```pddl
{task.ground_truth_problem_pddl.strip()}
```

Current Flawed Domain PDDL (contains bugs):
```pddl
{task.initial_domain_pddl.strip()}
```

Diagnose and repair the flawed domain file so that it is syntactically valid and solves the target problem.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the repaired PDDL domain code block.
"""
    else:
        prompt = f"""You are an automated PDDL domain generator.
Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

Fixed Ground-Truth Problem PDDL (P_gold):
```pddl
{task.ground_truth_problem_pddl.strip()}
```

Generate a single, syntactically valid PDDL domain file (define (domain ...) ...) that satisfies the requirements and is fully compatible with the fixed problem PDDL above.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
    try:
        raw_response, telemetry = invoke_raw_llm_with_telemetry(prompt)
    except Exception as e:
        print(f"[Baseline Zero-Shot Error]: LLM call failed: {e}")
        return {
            "generated_domain_pddl": "",
            "generated_problem_pddl": task.ground_truth_problem_pddl,
            "iterations_used": 1,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "raw_response": str(e),
            "error": str(e)
        }

    domain_pddl, _ = extract_pddl_blocks(raw_response)

    if not domain_pddl and "(define (domain" in raw_response.lower():
        domain_pddl = raw_response
    problem_pddl = task.ground_truth_problem_pddl

    return {
        "generated_domain_pddl": domain_pddl,
        "generated_problem_pddl": problem_pddl,
        "iterations_used": 1,
        "prompt_tokens": telemetry.get("prompt_tokens", 0),
        "completion_tokens": telemetry.get("completion_tokens", 0),
        "total_tokens": telemetry.get("total_tokens", 0),
        "estimated_cost_usd": telemetry.get("estimated_cost_usd", 0.0),
        "raw_response": raw_response
    }

def run_unstructured_retry_baseline(task: BenchmarkTask, max_retries: int = 5) -> Dict[str, Any]:
    """
    Baseline 2: Direct LLM Generation + Raw Unstructured Error Feedback Retry.
    Passes raw validator compiler logs directly back to the LLM without Pydantic AST,
    triage fault localization, or causal analysis, holding P_gold fixed and repairing only D_gen.
    Strictly NO fallback to ground truth domain.
    """
    is_repair_task = bool(getattr(task, "initial_domain_pddl", None))
    last_domain = task.initial_domain_pddl if is_repair_task else ""
    last_problem = task.ground_truth_problem_pddl
    cumulative_prompt_tokens = 0
    cumulative_completion_tokens = 0
    cumulative_tokens = 0
    cumulative_cost = 0.0
    last_raw_response = ""
    error_history = []

    eval_dir = str(get_eval_output_dir())
    os.makedirs(eval_dir, exist_ok=True)
    dom_file = os.path.join(eval_dir, f"temp_baseline_unstructured_dom_{task.task_id}.pddl")
    prob_file = os.path.join(eval_dir, f"temp_baseline_unstructured_prob_{task.task_id}.pddl")

    # If synthesis task with no starting domain, generate initial domain
    if not last_domain:
        base_prompt = f"""You are an automated PDDL domain generator.
Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

Fixed Ground-Truth Problem PDDL (P_gold):
```pddl
{task.ground_truth_problem_pddl.strip()}
```

Generate a single, syntactically valid PDDL domain file (define (domain ...) ...) that satisfies the requirements and is fully compatible with the fixed problem PDDL above.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
        try:
            raw_response, telemetry = invoke_raw_llm_with_telemetry(base_prompt)
            cumulative_prompt_tokens += telemetry.get("prompt_tokens", 0)
            cumulative_completion_tokens += telemetry.get("completion_tokens", 0)
            cumulative_tokens += telemetry.get("total_tokens", 0)
            cumulative_cost += telemetry.get("estimated_cost_usd", 0.0)
            last_raw_response = raw_response
            d_pddl, _ = extract_pddl_blocks(raw_response)
            if not d_pddl and "(define (domain" in raw_response.lower():
                d_pddl = raw_response
            last_domain = d_pddl
        except Exception as e:
            print(f"[Baseline Unstructured Retry Error]: Initial LLM call failed: {e}")
            return {
                "generated_domain_pddl": "",
                "generated_problem_pddl": last_problem,
                "iterations_used": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "error": str(e)
            }

    repair_attempts = 0
    for iteration in range(1, max_retries + 1):
        if not last_domain:
            break

        with open(dom_file, "w", encoding="utf-8") as f:
            f.write(last_domain)
        with open(prob_file, "w", encoding="utf-8") as f:
            f.write(last_problem)

        is_valid, val_log = run_val_validator(dom_file, prob_file)
        if is_valid:
            # Check solvability
            fd_res = run_fast_downward_with_plan(dom_file, prob_file)
            if fd_res["is_solvable"]:
                return {
                    "generated_domain_pddl": last_domain,
                    "generated_problem_pddl": last_problem,
                    "iterations_used": max(1, repair_attempts),
                    "prompt_tokens": cumulative_prompt_tokens,
                    "completion_tokens": cumulative_completion_tokens,
                    "total_tokens": cumulative_tokens,
                    "estimated_cost_usd": cumulative_cost,
                    "validation_passed": True,
                    "is_solvable": True,
                    "val_plan_valid": fd_res.get("val_plan_valid", False),
                    "error_history": error_history,
                    "raw_response": last_raw_response
                }

            # If syntax valid but unsolvable, pass raw Fast Downward output
            raw_error = fd_res.get("raw_fd_log", "Fast Downward found no plan.")
        else:
            raw_error = val_log

        repair_attempts += 1

        # Feed raw unparsed error string directly back into prompt
        clean_err = raw_error.encode("ascii", "ignore").decode("ascii")[:1500]
        # print("\n" + "=" * 75)
        # print(f"[UNSTRUCTURED_RETRY Iteration {iteration}]: Raw Oracle Feedback Received:")
        # print(clean_err.strip()[:1500])
        # print("=" * 75 + "\n", flush=True)
        error_history.append(f"[Iter {iteration} Raw Oracle Error]: {re.sub(r'\\s+', ' ', clean_err).strip()[:400]}")
        retry_prompt = f"""You are an automated PDDL domain debugger and repair system.
Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

FIXED READ-ONLY PROBLEM PDDL (P_gold — DO NOT MODIFY):
```pddl
{last_problem.strip()}
```

CURRENT FLAWED DOMAIN PDDL:
```pddl
{last_domain.strip()}
```

PREVIOUS ATTEMPT FAILED WITH THE FOLLOWING RAW ORACLE ERROR:
{clean_err}

Please revise and correct the PDDL domain definition so that it compiles and solves the target problem.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
        try:
            raw_response, telemetry = invoke_raw_llm_with_telemetry(retry_prompt)
            cumulative_prompt_tokens += telemetry.get("prompt_tokens", 0)
            cumulative_completion_tokens += telemetry.get("completion_tokens", 0)
            cumulative_tokens += telemetry.get("total_tokens", 0)
            cumulative_cost += telemetry.get("estimated_cost_usd", 0.0)
            last_raw_response = raw_response
            d_pddl, _ = extract_pddl_blocks(raw_response)
            if d_pddl:
                last_domain = d_pddl
        except Exception as e:
            print(f"[Baseline Unstructured Retry Error]: LLM call failed on iter {iteration}: {e}")
            break

    return {
        "generated_domain_pddl": last_domain,
        "generated_problem_pddl": last_problem,
        "iterations_used": max_retries,
        "prompt_tokens": cumulative_prompt_tokens,
        "completion_tokens": cumulative_completion_tokens,
        "total_tokens": cumulative_tokens,
        "estimated_cost_usd": cumulative_cost,
        "validation_passed": False,
        "is_solvable": False,
        "error_history": error_history,
        "raw_response": last_raw_response
    }


def run_no_ast_ablation(task: BenchmarkTask, max_retries: int = 5) -> Dict[str, Any]:
    """
    Ablation 1 (Tests H1): Direct PDDL Text Repair + Layered Diagnostic Triage.
    The agent receives structured diagnostic triage reports (error categories, faulty elements, actionable hints),
    but must repair and output concrete PDDL text directly WITHOUT an AST Blueprint or Python compiler.
    Isolates the effect of AST Blueprint decoupling on syntax validity and plan reachability.
    """
    from nodes.triage import run_triage_node

    base_prompt = f"""You are an automated PDDL domain generator.
Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

Fixed Ground-Truth Problem PDDL (P_gold):
```pddl
{task.ground_truth_problem_pddl.strip()}
```

Generate a single, syntactically valid PDDL domain file (define (domain ...) ...) that satisfies the requirements and is fully compatible with the fixed problem PDDL above.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
    last_domain = getattr(task, "initial_domain_pddl", "") or ""
    last_problem = task.ground_truth_problem_pddl
    cumulative_prompt_tokens = 0
    cumulative_completion_tokens = 0
    cumulative_tokens = 0
    cumulative_cost = 0.0
    last_raw_response = ""
    error_history = []
    diagnostic_reports = []

    eval_dir = str(get_eval_output_dir())
    os.makedirs(eval_dir, exist_ok=True)
    dom_file = os.path.join(eval_dir, f"temp_ablation_no_ast_dom_{task.task_id}.pddl")
    prob_file = os.path.join(eval_dir, f"temp_ablation_no_ast_prob_{task.task_id}.pddl")

    # Initial generation if no starting domain provided
    if not last_domain:
        try:
            raw_response, telemetry = invoke_raw_llm_with_telemetry(base_prompt)
            cumulative_prompt_tokens += telemetry.get("prompt_tokens", 0)
            cumulative_completion_tokens += telemetry.get("completion_tokens", 0)
            cumulative_tokens += telemetry.get("total_tokens", 0)
            cumulative_cost += telemetry.get("estimated_cost_usd", 0.0)
            last_raw_response = raw_response
            d_pddl, _ = extract_pddl_blocks(raw_response)
            if not d_pddl and "(define (domain" in raw_response.lower():
                d_pddl = raw_response
            last_domain = d_pddl
        except Exception as e:
            print(f"[Ablation No-AST Error]: Initial LLM call failed: {e}")
            return {
                "generated_domain_pddl": "",
                "generated_problem_pddl": last_problem,
                "iterations_used": 1,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "error": str(e)
            }

    repair_attempts = 0
    for iteration in range(1, max_retries + 1):
        if not last_domain:
            break

        with open(dom_file, "w", encoding="utf-8") as f:
            f.write(last_domain)
        with open(prob_file, "w", encoding="utf-8") as f:
            f.write(last_problem)

        is_valid, val_log = run_val_validator(dom_file, prob_file)
        if is_valid:
            fd_res = run_fast_downward_with_plan(dom_file, prob_file)
            if fd_res["is_solvable"]:
                return {
                    "generated_domain_pddl": last_domain,
                    "generated_problem_pddl": last_problem,
                    "iterations_used": max(1, repair_attempts),
                    "prompt_tokens": cumulative_prompt_tokens,
                    "completion_tokens": cumulative_completion_tokens,
                    "total_tokens": cumulative_tokens,
                    "estimated_cost_usd": cumulative_cost,
                    "validation_passed": True,
                    "is_solvable": True,
                    "val_plan_valid": fd_res.get("val_plan_valid", False),
                    "diagnostic_reports": diagnostic_reports,
                    "error_history": error_history,
                    "raw_response": last_raw_response
                }
            raw_error = fd_res.get("raw_fd_log", "Planner Error: Fast Downward found no plan.")
        else:
            raw_error = "VAL Error: " + val_log

        repair_attempts += 1

        # Invoke Structured Diagnostic Triage Node on raw error
        triage_state = {
            "requirements": task.natural_language_requirements,
            "generated_domain_pddl": last_domain,
            "initial_problem_pddl": last_problem,
            "verification_errors": [raw_error],
            "skip_triage": False,
            "pddl_domain_blueprint": {}
        }
        try:
            t_res = run_triage_node(triage_state)
            diag_feedback = t_res.get("formatted_diagnostic_feedback", raw_error)
            diagnostic_reports = t_res.get("diagnostic_reports", [])
        except Exception as te:
            diag_feedback = f"Verification Error:\n{raw_error}"
            diagnostic_reports = []

        error_history.append(f"[Iter {iteration} Triage Feedback]: {diag_feedback[:300]}")

        # Construct repair prompt with Structured Diagnostic Triage, but targeting raw PDDL code output
        repair_prompt = f"""You are an expert PDDL Knowledge Engineer specializing in formal domain model repair.
Your task is to repair the existing PDDL Domain (D_gen) to resolve the diagnostic errors reported by symbolic oracles against the fixed ground-truth problem instance (P_gold).
Because the problem instance (P_gold) is held fixed for formal verification, you must ONLY repair and output the PDDL domain definition.

Requirements & Fixed Target Problem Contract:
{task.natural_language_requirements}

CURRENT RAW PDDL DOMAIN CODE (TO REPAIR):
```pddl
{last_domain}
```

FIXED READ-ONLY PROBLEM PDDL (P_gold — DO NOT MODIFY):
```pddl
{last_problem.strip()}
```

STRUCTURED DIAGNOSTIC TRIAGE FEEDBACK:
{diag_feedback}

Produce ONLY the updated valid PDDL domain file (define (domain ...) ...) enclosed in a ```pddl ... ``` markdown code block.
"""
        try:
            raw_response, telemetry = invoke_raw_llm_with_telemetry(repair_prompt)
            cumulative_prompt_tokens += telemetry.get("prompt_tokens", 0)
            cumulative_completion_tokens += telemetry.get("completion_tokens", 0)
            cumulative_tokens += telemetry.get("total_tokens", 0)
            cumulative_cost += telemetry.get("estimated_cost_usd", 0.0)
            last_raw_response = raw_response
            d_pddl, _ = extract_pddl_blocks(raw_response)
            if d_pddl:
                last_domain = d_pddl
        except Exception as e:
            print(f"[Ablation No-AST Error]: Repair LLM call failed on iter {iteration}: {e}")
            break

    return {
        "generated_domain_pddl": last_domain,
        "generated_problem_pddl": last_problem,
        "iterations_used": max_retries,
        "prompt_tokens": cumulative_prompt_tokens,
        "completion_tokens": cumulative_completion_tokens,
        "total_tokens": cumulative_tokens,
        "estimated_cost_usd": cumulative_cost,
        "validation_passed": False,
        "is_solvable": False,
        "diagnostic_reports": diagnostic_reports,
        "error_history": error_history,
        "raw_response": last_raw_response
    }
