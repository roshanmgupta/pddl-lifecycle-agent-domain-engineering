from tools.symbolic_oracles import run_val_validator, run_fast_downward
import os
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from benchmark.schema import BenchmarkTask, LifecycleTaskType

PROJECT_ROOT = Path(__file__).resolve().parent.parent
from config.paths import get_benchmark_dir
BENCHMARK_ROOT = get_benchmark_dir()

# ==============================================================================
# AutoPlanBench Dynamic Loader Helpers (Flaws & Synthesis)
# ==============================================================================

def list_benchmark_domains() -> List[str]:
    """Returns sorted list of all 21 canonical benchmark domains."""
    from benchmark.pure_strips_benchmarks import DOMAINS_21
    return list(DOMAINS_21)


def list_domain_flaws(domain_name: str) -> List[str]:
    """Lists available curated flaw task folders for a domain."""
    flaws_dir = BENCHMARK_ROOT / domain_name / "flaws"
    if not flaws_dir.exists():
        return []
    flaws = [f.name for f in flaws_dir.iterdir() if f.is_dir()]
    return sorted(flaws)

def find_causally_activating_problem(domain_name: str, flaw_name: str) -> Optional[Path]:
    """
    Finds the first problem instance that causally activates the flaw
    (i.e. where the flawed domain fails VAL or Fast Downward, while the gold domain solves it).
    Defaults to problem_flawed.pddl or instance-1.pddl.
    """
    flaw_dir = BENCHMARK_ROOT / domain_name / "flaws" / flaw_name
    gt_dom = BENCHMARK_ROOT / domain_name / "domain.pddl"


    prob_flawed = flaw_dir / "problem_flawed.pddl"
    if prob_flawed.exists():
        # A valid benchmark test instance MUST be solvable by the reference gold domain!
        if gt_dom.exists():
            gt_ok, _ = run_fast_downward(str(gt_dom), str(prob_flawed))
            if gt_ok:
                return prob_flawed
        else:
            return prob_flawed

    dom_flawed = flaw_dir / "domain_flawed.pddl"
    orig_dir = BENCHMARK_ROOT / domain_name / "orig_problems"
    if not orig_dir.exists():
        return None

    probs = sorted(list(orig_dir.glob("*.pddl")), key=lambda p: (len(p.name), p.name))
    if not probs:
        return None

    gt_dom = BENCHMARK_ROOT / domain_name / "domain.pddl"

    # 1. Quick test on instance-1 (most common)
    p1 = orig_dir / "instance-1.pddl"
    if p1.exists():
        v1_ok, _ = run_val_validator(str(dom_flawed), str(p1))
        if not v1_ok:
            return p1
        fd1_ok, _ = run_fast_downward(str(dom_flawed), str(p1))
        if not fd1_ok:
            return p1

    # 2. If instance-1 bypassed the flaw, find the first problem instance where the flaw is activated
    for p in probs:
        v_ok, _ = run_val_validator(str(dom_flawed), str(p))
        if not v_ok:
            return p
        fd_ok, _ = run_fast_downward(str(dom_flawed), str(p))
        if not fd_ok:
            if gt_dom.exists():
                gt_ok, _ = run_fast_downward(str(gt_dom), str(p))
                if gt_ok:
                    return p
            else:
                return p
    return p1 if p1.exists() else probs[0]


def load_flaw_task(domain_name: str, flaw_name: str, problem_instance: Optional[str] = None) -> Optional[BenchmarkTask]:
    """
    Loads a single Category B flaw task from PDDLLifeCycleBench/<domain>/flaws/<flaw_name>.
    Constructs an executable BenchmarkTask with ground-truth metadata and oracle expectations.
    """
    flaw_dir = BENCHMARK_ROOT / domain_name / "flaws" / flaw_name
    if not flaw_dir.exists():
        return None

    dom_flawed = (flaw_dir / "domain_flawed.pddl").read_text(encoding="utf-8-sig")
    meta = json.loads((flaw_dir / "flaw_metadata.json").read_text(encoding="utf-8-sig"))

    # Pure domain requirements from domain_encoding.txt (avoids bundled problem statements or notes)
    domain_enc_file = BENCHMARK_ROOT / domain_name / "domain_encoding.txt"
    spec = domain_enc_file.read_text(encoding="utf-8-sig") if domain_enc_file.exists() else ""
    spec = re.sub(r"\[NOTE:[^\]]+\]\s*", "", spec).strip()
    gt_dom = (BENCHMARK_ROOT / domain_name / "domain.pddl").read_text(encoding="utf-8-sig")

    # Select problem instance: explicit argument, problem_flawed.pddl, or causally activating problem
    if problem_instance:
        prob_file = BENCHMARK_ROOT / domain_name / "orig_problems" / problem_instance
        if not prob_file.exists():
            prob_file = Path(problem_instance)
    else:
        prob_file = find_causally_activating_problem(domain_name, flaw_name)
        if not prob_file or not prob_file.exists():
            prob_file = BENCHMARK_ROOT / domain_name / "orig_problems" / "instance-1.pddl"

    prob_pddl = prob_file.read_text(encoding="utf-8-sig") if (prob_file and prob_file.exists()) else ""
    active_prob_name = prob_file.name if prob_file else "instance-1.pddl"
    gold_plans_dir = BENCHMARK_ROOT / domain_name / "orig_gold_plans"

    all_prob_pddls: List[str] = []
    all_gold_plans: List[str] = []
    all_prob_names: List[str] = []
    if prob_file and prob_file.exists():
        all_prob_pddls.append(prob_pddl)
        all_prob_names.append(prob_file.name)
        gp_first = gold_plans_dir / f"{prob_file.stem}_gold_plan.txt"
        all_gold_plans.append(str(gp_first) if gp_first.exists() else "")

        if not problem_instance and prob_file.parent.name in ("orig_problems", "adapted_instances"):
            sibling_probs = sorted(
                list(prob_file.parent.glob("*.pddl")),
                key=lambda p: (len(p.name), p.name)
            )
            for sp in sibling_probs:
                if sp.resolve() == prob_file.resolve():
                    continue
                try:
                    all_prob_pddls.append(sp.read_text(encoding="utf-8-sig"))
                    all_prob_names.append(sp.name)
                    gp_cand = gold_plans_dir / f"{sp.stem}_gold_plan.txt"
                    all_gold_plans.append(str(gp_cand) if gp_cand.exists() else "")
                except Exception:
                    pass

    fcat = meta.get("flaw_category", "UNKNOWN")
    return BenchmarkTask(
        task_id=f"{domain_name}_{flaw_name}",
        domain_family=domain_name,
        task_type=LifecycleTaskType.SYNTHETIC_FAULT_REPAIR,
        title=f"{domain_name.upper()} Flaw: {fcat} ({active_prob_name})",
        natural_language_requirements=spec,
        initial_domain_pddl=dom_flawed,
        initial_problem_pddl=prob_pddl,
        fault_category=fcat,
        gold_fault_element=meta.get("target_action"),
        gold_fault_category=fcat,
        expected_repair_behavior=meta.get("ground_truth_fix"),
        ground_truth_domain_pddl=gt_dom,
        ground_truth_problem_pddl=prob_pddl,
        ground_truth_problems=all_prob_pddls,
        ground_truth_gold_plans=all_gold_plans,
        ground_truth_problem_names=all_prob_names
    )


def load_elicitation_task(domain_name: str) -> Optional[BenchmarkTask]:
    """Loads a single Category A Elicitation task for a standard benchmark domain."""
    dom_dir = BENCHMARK_ROOT / domain_name
    if not dom_dir.exists():
        return None
    spec_file = dom_dir / "domain_encoding.txt"
    dom_file = dom_dir / "domain.pddl"
    prob_files = sorted(
        list((dom_dir / "orig_problems").glob("instance-*.pddl")),
        key=lambda p: (len(p.name), p.name)
    )
    if not spec_file.exists() or not dom_file.exists() or not prob_files:
        return None

    spec = spec_file.read_text(encoding="utf-8")
    spec = re.sub(r"\[NOTE:[^\]]+\]\s*", "", spec).strip()
    gt_dom = dom_file.read_text(encoding="utf-8")
    gt_prob = prob_files[0].read_text(encoding="utf-8")

    all_prob_pddls: List[str] = []
    all_gold_plans: List[str] = []
    all_prob_names: List[str] = []
    gold_plans_dir = dom_dir / "orig_gold_plans"
    for pf in prob_files:
        all_prob_pddls.append(pf.read_text(encoding="utf-8"))
        all_prob_names.append(pf.name)
        gp_cand = gold_plans_dir / f"{pf.stem}_gold_plan.txt"
        all_gold_plans.append(str(gp_cand) if gp_cand.exists() else "")

    return BenchmarkTask(
        task_id=f"{domain_name}_elicit",
        domain_family=domain_name,
        task_type=LifecycleTaskType.ELICITATION,
        title=f"{domain_name.upper()} Initial Elicitation",
        natural_language_requirements=spec,
        initial_domain_pddl=None,
        initial_problem_pddl=gt_prob,
        ground_truth_domain_pddl=gt_dom,
        ground_truth_problem_pddl=gt_prob,
        ground_truth_problems=all_prob_pddls,
        ground_truth_gold_plans=all_gold_plans,
        ground_truth_problem_names=all_prob_names
    )

# ==============================================================================
# AutoPlanBench Loader Integration
# ==============================================================================

def list_autoplanbench_domains() -> List[str]:
    """Returns sorted list of pure STRIPS AutoPlanBench domains."""
    from benchmark.pure_strips_benchmarks import AUTOPLANBENCH_PURE_STRIPS_DOMAINS
    return list(AUTOPLANBENCH_PURE_STRIPS_DOMAINS)


def load_autoplanbench_synthesis_task(domain_name: str, instance_name: Optional[str] = None) -> Optional[BenchmarkTask]:
    """Loads a synthesis task from AutoPlanBench dataset with all ground-truth reference problems."""
    from benchmark.pure_strips_benchmarks import (
        load_autoplanbench_original_domain_data,
        get_autoplanbench_domain_folder,
    )
    try:
        unified_prompt, dom_desc, prob_desc, ref_dom, ref_inst, prob_files = load_autoplanbench_original_domain_data(domain_name, instance_name)
    except Exception as e:
        print(f"[AutoPlanBench Loader Error]: {e}")
        return None

    if not ref_dom or not ref_inst:
        return None

    inst_stem = Path(instance_name).stem if instance_name else (Path(prob_files[0]).stem if prob_files else "instance-1")
    d_folder = get_autoplanbench_domain_folder(domain_name)
    probs_dir = d_folder / "orig_problems"
    if not probs_dir.exists():
        probs_dir = d_folder / "problems"
    gold_plans_dir = d_folder / "orig_gold_plans"

    all_prob_pddls: List[str] = []
    all_gold_plans: List[str] = []
    all_prob_names: List[str] = []
    if instance_name:
        p_path = probs_dir / instance_name
        if p_path.exists():
            all_prob_pddls.append(p_path.read_text(encoding="utf-8"))
            all_prob_names.append(p_path.name)
            gp_cand = gold_plans_dir / f"{p_path.stem}_gold_plan.txt"
            all_gold_plans.append(str(gp_cand) if gp_cand.exists() else "")
    elif probs_dir.exists():
        for pf in prob_files:
            p_path = probs_dir / pf
            if p_path.exists():
                try:
                    all_prob_pddls.append(p_path.read_text(encoding="utf-8"))
                    all_prob_names.append(pf)
                    gp_cand = gold_plans_dir / f"{Path(pf).stem}_gold_plan.txt"
                    all_gold_plans.append(str(gp_cand) if gp_cand.exists() else "")
                except Exception:
                    pass

    clean_spec = re.sub(r"\[NOTE:[^\]]+\]\s*", "", (dom_desc or unified_prompt)).strip()

    return BenchmarkTask(
        task_id=f"apb_{domain_name}_{inst_stem}",
        domain_family=domain_name,
        task_type=LifecycleTaskType.ELICITATION,
        title=f"AutoPlanBench {domain_name.capitalize()} Synthesis ({instance_name or (prob_files[0] if prob_files else 'instance-1.pddl')})",
        natural_language_requirements=clean_spec,
        initial_domain_pddl=None,
        initial_problem_pddl=ref_inst,
        ground_truth_domain_pddl=ref_dom,
        ground_truth_problem_pddl=ref_inst,
        ground_truth_problems=all_prob_pddls,
        ground_truth_gold_plans=all_gold_plans,
        ground_truth_problem_names=all_prob_names
    )
