import sys
import os
import re
import time
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Callable, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.schema import BenchmarkTask, LifecycleTaskType
from config.model_config import invoke_raw_llm_with_telemetry
from config.paths import get_eval_output_dir


def _emit(on_event: Optional[Callable[[Dict[str, Any]], None]], **event: Any) -> None:
    """Forwards an observability event to an optional callback. Never alters baseline behavior."""
    if on_event is None:
        return
    try:
        on_event(event)
    except Exception as cb_err:
        print(f"[Baseline Trace Callback Warning]: {cb_err}")


def _emit_oracle_check(on_event, iteration: int, verif: Dict[str, Any]) -> None:
    """Emits a standardized VAL / Fast Downward oracle event."""
    _emit(
        on_event,
        phase="validate",
        iteration=iteration,
        val_ok=bool(verif.get("is_syntax_valid")),
        val_log=verif.get("syntax_log", ""),
        fd_ran=bool(verif.get("is_syntax_valid")),
        fd_ok=bool(verif.get("is_solvable")) if verif.get("is_syntax_valid") else None,
        fd_timed_out=bool(verif.get("planner_timeout", False)),
        fd_log=verif.get("raw_fd_log", ""),
        plan_steps=list(verif.get("plan_steps", [])),
        executability_valid=verif.get("executability_valid"),
        feasibility_valid=verif.get("feasibility_valid"),
        interpretability_valid=verif.get("interpretability_valid"),
    )


def extract_pddl_blocks(raw_text: str) -> Tuple[str, str]:
    """Extracts domain.pddl and problem.pddl code blocks from raw LLM output text."""
    domain_pddl = ""
    problem_pddl = ""

    domain_match = re.search(r'\(define\s*\(domain.*?\n\)', raw_text, re.DOTALL | re.IGNORECASE)
    if not domain_match:
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


def _build_fixed_skeleton_block(task: BenchmarkTask) -> Optional[str]:
    """Builds the ground-truth domain skeleton string (types, predicates, action signatures)."""
    gt_dom = getattr(task, "ground_truth_domain_pddl", "")
    if not gt_dom or not gt_dom.strip():
        return None
    from nodes.pddl_to_ast_parser import parse_pddl_domain_to_representation
    ref_bp = parse_pddl_domain_to_representation(gt_dom)
    action_headers = []
    for a in ref_bp.get("actions", []):
        param_str = " ".join([f"{var} - {t}" if t and t != "object" else var for var, t in a.get("parameters", {}).items()])
        action_headers.append(f"(:action {a['action_name']}\n    :parameters ({param_str})\n    :precondition ...\n    :effect ...\n  )")

    actions_str = "\n  ".join(action_headers)
    reqs_str = " ".join(ref_bp.get("requirements", [":strips", ":typing"]))
    types_str = ""
    if ref_bp.get("types"):
        types_str = "\n  (:types " + " ".join([f"{k} - {v}" if v and v != "object" else k for k, v in ref_bp["types"].items()]) + ")"
    consts_str = ""
    if ref_bp.get("constants"):
        consts_str = "\n  (:constants " + " ".join([f"{k} - {v}" if v and v != "object" else k for k, v in ref_bp["constants"].items()]) + ")"
    preds_str = "\n  (:predicates\n    " + "\n    ".join(ref_bp.get("predicates", [])) + "\n  )"

    return (
        f"(define (domain {ref_bp.get('domain_name', 'domain')})\n"
        f"  (:requirements {reqs_str}){types_str}{consts_str}{preds_str}\n"
        f"  {actions_str}\n"
        f")"
    )


def build_fixed_signature_prompt(task: BenchmarkTask) -> Optional[str]:
    """Builds prompt giving reference types, predicates, and action signatures."""
    skeleton = _build_fixed_skeleton_block(task)
    if not skeleton:
        return None

    prompt = f"""You are an automated PDDL domain model generator.
Your task is to generate a complete, valid PDDL domain file by generating ONLY the :precondition and :effect expressions for the given actions.

THE DOMAIN SKELETON IS FIXED TO MATCH THE GROUND TRUTH:
{skeleton}

Domain Requirements:
{task.natural_language_requirements}

Generate the complete PDDL domain file where you preserve the exact domain name, requirements, types, predicates, and action headers (names and parameters), and fill in the :precondition and :effect for every action.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
    return prompt


def _verify_baseline_candidate_across_problems(
    task: BenchmarkTask,
    domain_pddl: str,
    eval_dir: str,
    tag_prefix: str
) -> Tuple[List[str], Dict[str, Any], str]:
    """
    Verifies a baseline candidate domain across all ground-truth problem instances
    for Syntax, Solvability, Soundness, and Completeness.
    Returns (errors, active_verif_dict, active_problem_pddl).
    """
    from nodes.validation import verify_pddl_candidate, _collect_verification_errors

    gt_dom = getattr(task, "ground_truth_domain_pddl", None) or None
    gt_problems: List[str] = list(getattr(task, "ground_truth_problems", None) or [])
    gt_gold_plans: List[str] = list(getattr(task, "ground_truth_gold_plans", None) or [])
    gt_prob_names: List[str] = list(getattr(task, "ground_truth_problem_names", None) or [])

    fallback_prob = getattr(task, "ground_truth_problem_pddl", "") or getattr(task, "initial_problem_pddl", "") or ""
    if not gt_problems and fallback_prob:
        gt_problems = [fallback_prob]

    last_verif: Dict[str, Any] = {}
    active_prob = gt_problems[0] if gt_problems else fallback_prob

    for idx, prob_str in enumerate(gt_problems):
        gp_path = gt_gold_plans[idx] if idx < len(gt_gold_plans) and gt_gold_plans[idx] else None
        p_label = gt_prob_names[idx] if (len(gt_problems) > 1 and idx < len(gt_prob_names)) else ""
        verif = verify_pddl_candidate(
            generated_domain_pddl=domain_pddl,
            generated_problem_pddl=prob_str,
            ground_truth_domain_pddl=gt_dom,
            ground_truth_problem_pddl=prob_str,
            ground_truth_plan_path=gp_path,
            temp_dir=Path(eval_dir),
            tag=f"{tag_prefix}_p{idx + 1}"
        )
        last_verif = verif
        errors = _collect_verification_errors(verif, gt_dom, prob_label=p_label)
        if errors:
            return errors, verif, prob_str

    return [], last_verif, active_prob


def run_zero_shot_baseline(task: BenchmarkTask, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """
    Baseline 1: Zero-Shot Direct LLM Generation / Single-Pass Repair.
    Requests raw PDDL domain code (D_gen) directly from natural language prompt without Pydantic AST or validation loops,
    holding the ground-truth problem instance(s) fixed.
    Strictly NO fallback to ground truth domain.
    """
    if getattr(task, "initial_domain_pddl", None):
        prompt = f"""You are an automated PDDL domain debugger and repair system.
Domain Requirements:
{task.natural_language_requirements}

Current Flawed Domain PDDL (contains bugs):
```pddl
{task.initial_domain_pddl.strip()}
```

Diagnose and repair the flawed domain file so that it is syntactically valid and strictly satisfies the domain requirements.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the repaired PDDL domain code block.
"""
    else:
        fixed_prompt = build_fixed_signature_prompt(task)
        if fixed_prompt:
            prompt = fixed_prompt
        else:
            prompt = f"""You are an automated PDDL domain model generator.
Domain Requirements:
{task.natural_language_requirements}

Generate a single, syntactically valid classical PDDL 2.1 (:strips :typing) domain file (define (domain ...) ...) that strictly satisfies the requirements above.
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
    _emit(on_event, phase="llm_generation", iteration=0, prompt=prompt,
          raw_response=raw_response, output_domain=domain_pddl,
          note="Single LLM call. No oracle feedback is returned to the model.")

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


def run_unstructured_retry_baseline(task: BenchmarkTask, max_retries: int = 5, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """
    Baseline 2: Direct LLM Generation + Raw Unstructured Error Feedback Retry.
    Passes raw validator and planner logs directly back to the LLM without Pydantic AST,
    model-based fault localization, or causal analysis, holding ground-truth problem(s) fixed.
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
    fixed_skeleton = _build_fixed_skeleton_block(task)

    if not last_domain:
        fixed_p = build_fixed_signature_prompt(task)
        if fixed_p:
            base_prompt = fixed_p
        else:
            base_prompt = f"""You are an automated PDDL domain model generator.
Domain Requirements:
{task.natural_language_requirements}

Generate a single, syntactically valid classical PDDL 2.1 (:strips :typing) domain file (define (domain ...) ...) that strictly satisfies the requirements above.
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
            _emit(on_event, phase="llm_generation", iteration=0, prompt=base_prompt,
                  raw_response=raw_response, output_domain=d_pddl)
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

    fixed_sig_clause = ""
    if fixed_skeleton:
        fixed_sig_clause = (
            f"\nFIXED DOMAIN SKELETON (preserve exact domain name, requirements, types, predicates, and action headers; "
            f"modify ONLY :precondition and :effect expressions):\n{fixed_skeleton}\n"
        )

    repair_attempts = 0
    for iteration in range(1, max_retries + 1):
        if not last_domain:
            break

        errors, verif, active_prob = _verify_baseline_candidate_across_problems(
            task=task,
            domain_pddl=last_domain,
            eval_dir=eval_dir,
            tag_prefix=f"unstructured_{task.task_id}_it{iteration}"
        )
        _emit_oracle_check(on_event, iteration=iteration, verif=verif)

        if not errors:
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
                "val_plan_valid": verif.get("executability_valid", False),
                "error_history": error_history,
                "raw_response": last_raw_response
            }

        repair_attempts += 1
        raw_error = "\n\n".join(errors)
        clean_err = raw_error.encode("ascii", "ignore").decode("ascii")[:1500]
        error_history.append(f"[Iter {iteration} Raw Oracle Error]: {re.sub(r'\\s+', ' ', clean_err).strip()[:400]}")

        retry_prompt = f"""You are an automated PDDL domain debugger and repair system.
Domain Requirements:
{task.natural_language_requirements}
{fixed_sig_clause}
CURRENT FLAWED DOMAIN PDDL:
```pddl
{last_domain.strip()}
```

PREVIOUS ATTEMPT FAILED WITH THE FOLLOWING RAW ORACLE ERROR:
{clean_err}

Please revise and correct the PDDL domain definition so that it compiles and strictly satisfies the domain requirements while resolving the oracle error.
Format your output using a markdown code fence:
```pddl
(define (domain ...) ...)
```
Respond ONLY with the PDDL domain code block.
"""
        _emit(
            on_event,
            phase="fault_feedback_passed_to_llm",
            iteration=iteration,
            feedback_type="raw_oracle_trace",
            feedback_payload=clean_err,
            prompt=retry_prompt,
            model_target="pddl_text",
            note="Unstructured retry passes raw unparsed compiler/solver logs back to the LLM without AST or triage."
        )
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
            _emit(
                on_event,
                phase="repair_response",
                iteration=iteration,
                raw_response=raw_response,
                output_domain=d_pddl,
                telemetry=telemetry
            )
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


def run_no_ast_ablation(task: BenchmarkTask, max_retries: int = 5, on_event: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """Ablation 1: Direct PDDL text generation and repair with layered fault localization."""
    from nodes.fault_localization import FaultLocalizationNode

    base_prompt = f"""You are an automated PDDL domain model generator.
Domain Requirements:
{task.natural_language_requirements}

Generate a single, syntactically valid classical PDDL 2.1 (:strips :typing) domain file (define (domain ...) ...) that strictly satisfies the requirements above.
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
    fixed_skeleton = _build_fixed_skeleton_block(task)

    if not last_domain:
        initial_gen_prompt = build_fixed_signature_prompt(task) or base_prompt
        try:
            raw_response, telemetry = invoke_raw_llm_with_telemetry(initial_gen_prompt)
            cumulative_prompt_tokens += telemetry.get("prompt_tokens", 0)
            cumulative_completion_tokens += telemetry.get("completion_tokens", 0)
            cumulative_tokens += telemetry.get("total_tokens", 0)
            cumulative_cost += telemetry.get("estimated_cost_usd", 0.0)
            last_raw_response = raw_response
            d_pddl, _ = extract_pddl_blocks(raw_response)
            if not d_pddl and "(define (domain" in raw_response.lower():
                d_pddl = raw_response
            last_domain = d_pddl
            _emit(on_event, phase="llm_generation", iteration=0, prompt=initial_gen_prompt,
                  raw_response=raw_response, output_domain=d_pddl)
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

    fixed_sig_clause = ""
    if fixed_skeleton:
        fixed_sig_clause = (
            f"\nFIXED DOMAIN SKELETON (preserve exact domain name, requirements, types, predicates, and action headers; "
            f"modify ONLY :precondition and :effect expressions):\n{fixed_skeleton}\n"
        )

    repair_attempts = 0
    for iteration in range(1, max_retries + 1):
        if not last_domain:
            break

        errors, verif, active_prob = _verify_baseline_candidate_across_problems(
            task=task,
            domain_pddl=last_domain,
            eval_dir=eval_dir,
            tag_prefix=f"no_ast_{task.task_id}_it{iteration}"
        )
        _emit_oracle_check(on_event, iteration=iteration, verif=verif)

        if not errors:
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
                "val_plan_valid": verif.get("executability_valid", False),
                "diagnostic_reports": diagnostic_reports,
                "error_history": error_history,
                "raw_response": last_raw_response
            }

        repair_attempts += 1

        fault_loc_state = {
            "requirements": task.natural_language_requirements,
            "generated_domain_pddl": last_domain,
            "initial_problem_pddl": active_prob,
            "verification_errors": errors,
            "skip_fault_localization": False,
            "pddl_domain_representation": {}
        }
        try:
            t_res = FaultLocalizationNode(fault_loc_state)
            diag_feedback = t_res.get("formatted_diagnostic_feedback", "\n".join(errors))
            diagnostic_reports = t_res.get("diagnostic_reports", [])
            cumulative_prompt_tokens += t_res.get("total_prompt_tokens", 0)
            cumulative_completion_tokens += t_res.get("total_completion_tokens", 0)
            cumulative_tokens += t_res.get("total_tokens", 0)
            cumulative_cost += t_res.get("estimated_cost_usd", 0.0)
        except Exception:
            diag_feedback = "Verification Error:\n" + "\n".join(errors)
            diagnostic_reports = []

        error_history.append(f"[Iter {iteration} Fault Localization Feedback]: {diag_feedback[:300]}")

        repair_prompt = f"""You are an expert PDDL Knowledge Engineer specializing in formal domain model repair.
Your task is to repair the existing PDDL Domain (D_gen) to resolve the diagnostic errors reported by symbolic oracles.
You must ONLY repair and output the PDDL domain definition.

Domain Requirements:
{task.natural_language_requirements}
{fixed_sig_clause}
CURRENT RAW PDDL DOMAIN CODE (TO REPAIR):
```pddl
{last_domain}
```

LAYERED MODEL-BASED FAULT LOCALIZATION FEEDBACK:
{diag_feedback}

Produce ONLY the updated valid PDDL domain file (define (domain ...) ...) enclosed in a ```pddl ... ``` markdown code block.
"""
        _emit(
            on_event,
            phase="fault_feedback_passed_to_llm",
            iteration=iteration,
            feedback_type="model_based_fault_localization",
            feedback_payload=diag_feedback,
            diagnostic_reports=diagnostic_reports,
            prompt=repair_prompt,
            model_target="pddl_text",
            note="Ablation No-AST passes structured fault localization triage to direct PDDL text repair without Pydantic AST."
        )
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
            _emit(
                on_event,
                phase="repair_response",
                iteration=iteration,
                raw_response=raw_response,
                output_domain=d_pddl,
                telemetry=telemetry
            )
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
