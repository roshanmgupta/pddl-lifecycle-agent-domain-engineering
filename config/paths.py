"""
config/paths.py
Centralized Path & Environment Configuration for PDDL Lifecycle Agent.

Allows configuring all project paths via environment variables (.env file)
with robust resolution relative to the repository root.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
load_dotenv(override=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_path(env_var_name: str, default_rel_path: str) -> Path:
    """
    Resolves a path from an environment variable.
    If the path is relative, it is resolved relative to PROJECT_ROOT.
    If the environment variable is unset or empty, default_rel_path is used.
    """
    raw_val = os.getenv(env_var_name)
    if raw_val:
        raw_val = raw_val.strip().strip('"').strip("'")
    if not raw_val:
        raw_val = default_rel_path

    p = Path(raw_val)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


# ==============================================================================
# 1. Reference Benchmark Repositories & Datasets
# ==============================================================================

def get_benchmark_dir() -> Path:
    """
    Active canonical benchmark dataset directory (default: PDDLLifeCycleBench).
    Configurable via PDDLLIFECYCLEBENCH_DIR or BENCHMARK_DIR in .env.
    """
    env_key = "PDDLLIFECYCLEBENCH_DIR" if os.getenv("PDDLLIFECYCLEBENCH_DIR") else "BENCHMARK_DIR"
    return resolve_path(env_key, "PDDLLifeCycleBench")


def get_autoplanbench_dir() -> Path:
    """
    AutoPlanBench dataset directory (default: autoplanbench/data).
    Configurable via AUTOPLANBENCH_DIR in .env.
    """
    return resolve_path("AUTOPLANBENCH_DIR", "autoplanbench/data")


def get_autoplanbench_prompts_dir() -> Path:
    """
    Extracted AutoPlanBench natural language prompts directory (default: prompt_autoplanbench).
    Configurable via AUTOPLANBENCH_PROMPTS_DIR in .env.
    """
    return resolve_path("AUTOPLANBENCH_PROMPTS_DIR", "prompt_autoplanbench")


def get_nl2pddl_dir() -> Path:
    """
    NL2PDDL benchmark test directory (default: NL2PDDL/test).
    Configurable via NL2PDDL_DIR in .env.
    """
    return resolve_path("NL2PDDL_DIR", "NL2PDDL/test")


def get_nl2pddl_prompts_dir() -> Path:
    """
    Extracted NL2PDDL prompts directory (default: prompt_NL2PDDL).
    Configurable via NL2PDDL_PROMPTS_DIR in .env.
    """
    return resolve_path("NL2PDDL_PROMPTS_DIR", "prompt_NL2PDDL")


# ==============================================================================
# 2. Results, Temporary Working & Solver Files
# ==============================================================================

def get_results_dir() -> Path:
    """Master results directory (default: results)."""
    p = resolve_path("RESULTS_DIR", "results")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_temp_dir() -> Path:
    """Isolated scratch/working directory for temporary solver artifacts (default: results/temp)."""
    p = get_results_dir() / "temp"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_runs_dir() -> Path:
    """Dedicated directory housing per-run isolated output folders (default: results/runs)."""
    p = get_results_dir() / "runs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_run_directory(tag: str = "run") -> Path:
    """
    Creates an isolated, timestamped run directory for an experiment or execution pass.
    Directory structure: results/runs/<tag>_<YYYYMMDD_HHMMSS>/
    Contains an 'artifacts/' subdirectory for intermediate solver/oracle files.
    """
    import time
    clean_tag = tag.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = get_runs_dir() / f"{clean_tag}_{timestamp}"
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    return run_dir


def get_temp_domain_path() -> str:
    """Temporary domain PDDL file path inside results/temp/."""
    return str(get_temp_dir() / "temp_domain.pddl")


def get_temp_problem_path() -> str:
    """Temporary problem PDDL file path inside results/temp/."""
    return str(get_temp_dir() / "temp_problem.pddl")


def get_temp_gt_domain_path() -> str:
    """Temporary ground-truth domain PDDL file path for cross-validation inside results/temp/."""
    return str(get_temp_dir() / "temp_domain_gt.pddl")


def get_temp_plan_path() -> str:
    """Temporary planner output SAS plan path inside results/temp/."""
    return str(get_temp_dir() / "sas_plan")


def get_temp_eval_plan_path() -> str:
    """Temporary evaluation plan text path inside results/temp/."""
    return str(get_temp_dir() / "temp_eval_plan.txt")


# ==============================================================================
# 3. Generated Domain, Problem, and Plan Output Directories
# ==============================================================================

def get_eval_output_dir() -> Path:
    """Evaluation experiment artifacts scratch directory (default: results/eval_artifacts)."""
    p = resolve_path("OUTPUT_DIR_EVAL", "results/eval_artifacts")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_generated_output_dir() -> Path:
    """General generated outputs directory (default: results/generated)."""
    p = resolve_path("GENERATED_OUTPUT_DIR", "results/generated")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_flaw_output_dir() -> Path:
    """Curated Flaw Repair outputs directory (default: results/generated/repair)."""
    p = resolve_path("OUTPUT_DIR_FLAW", "results/generated/repair")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_evolve_output_dir() -> Path:
    """Continuous Evolution outputs directory (default: results/generated/evolution)."""
    p = resolve_path("OUTPUT_DIR_EVOLVE", "results/generated/evolution")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_elicitation_output_dir() -> Path:
    """Fresh Elicitation outputs directory (default: results/generated/elicitation)."""
    p = resolve_path("OUTPUT_DIR_ELICITATION", "results/generated/elicitation")
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_generated_domain_filename() -> str:
    """Base filename for generated domains (default: domain.pddl)."""
    return os.getenv("GENERATED_DOMAIN_FILE", "domain.pddl").strip().strip('"').strip("'")


def get_generated_problem_filename() -> str:
    """Base filename for generated problems (default: problem.pddl)."""
    return os.getenv("GENERATED_PROBLEM_FILE", "problem.pddl").strip().strip('"').strip("'")


def get_generated_plan_filename() -> str:
    """Base filename for generated plans (default: plan.txt)."""
    return os.getenv("GENERATED_PLAN_FILE", "plan.txt").strip().strip('"').strip("'")
