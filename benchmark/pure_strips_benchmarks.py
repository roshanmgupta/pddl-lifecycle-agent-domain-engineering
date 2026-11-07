"""
benchmark/pure_strips_benchmarks.py
Curated Pure STRIPS + Typing Benchmark Loaders for AutoPlanBench & NL2PDDL.

Strictly filters for domains that ONLY contain (:requirements :strips :typing)
or a subset thereof (no :equality, :negative-preconditions, :disjunctive-preconditions,
:adl, :action-costs, :fluents, etc.).

Reads directly from original repository folders:
  - AutoPlanBench: autoplanbench/data/<domain>/
  # - NL2PDDL: NL2PDDL/test/<domain>/ (Disabled)
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from config.paths import get_autoplanbench_dir #, get_nl2pddl_dir

# ==============================================================================
# Canonical 21 Pure STRIPS + Typing Benchmark Domains (autoplanbench/data/)
# ==============================================================================

DOMAINS_21: List[str] = [
    "blocksworld",
    "gripper",
    "logistics",
    "depot",
    "rovers",
    "satellite",
    "elevators08",
    "parking11",
    "goldminer",
    "scanalyzer08",
    "visitall",
    "transport08-bfs",
    "floortile",
    "tpp06-bfs",
    "pegsol08",
    "nomystery11-bfs",
    "barman14-bfs",
    "pipesworld-notankage04-bfs",
    "woodworking08",
    "zenotravel02",
    "driverlog02-bfs"
]

AUTOPLANBENCH_PURE_STRIPS_DOMAINS = DOMAINS_21

# ==============================================================================
# AutoPlanBench Original Loader
# ==============================================================================

def get_autoplanbench_domain_folder(domain_name: str) -> Path:
    return Path(get_autoplanbench_dir()) / domain_name


def list_autoplanbench_problem_files(domain_name: str) -> List[str]:
    """Lists sorted problem PDDL files from autoplanbench/data/<domain>/orig_problems/ or /problems/."""
    base = get_autoplanbench_domain_folder(domain_name)
    probs_dir = base / "orig_problems"
    if not probs_dir.exists():
        probs_dir = base / "problems"
    if not probs_dir.exists():
        return []
    def _extract_num(name: str) -> int:
        m = re.search(r'\d+', name)
        return int(m.group(0)) if m else 9999
    return sorted([f for f in os.listdir(probs_dir) if f.endswith(".pddl")], key=_extract_num)


def translate_autoplanbench_problem(prob_pddl: str, pred_maps: Dict[str, str], instance_name: str, domain_name: str) -> str:
    """Translates objects, init, and goal facts from problem PDDL into structured readable text plus the fixed P_gold interface contract."""
    clean_pddl = re.sub(r';[^\n]*', '', prob_pddl)
    obj_match = re.search(r'\(:objects\s*(.*?)\)', clean_pddl, re.IGNORECASE | re.DOTALL)
    objects_nl = []
    if obj_match:
        raw_objs = obj_match.group(1).strip()
        for line in raw_objs.split('\n'):
            line = line.strip()
            if line and not line.startswith(';'):
                objects_nl.append(line)

    init_match = re.search(r'\(:init\s*(.*?)\(:goal', clean_pddl, re.IGNORECASE | re.DOTALL)
    init_facts = []
    if init_match:
        for fact in re.findall(r'\(([^()]+)\)', init_match.group(1)):
            parts = fact.strip().split()
            if not parts:
                continue
            pname, args = parts[0], parts[1:]
            if pname == '=':
                continue
            if pname in pred_maps:
                try:
                    init_facts.append(pred_maps[pname].format(*args))
                except Exception:
                    init_facts.append(f"{pname} ({', '.join(args)})")
            elif pname.lower() in pred_maps:
                try:
                    init_facts.append(pred_maps[pname.lower()].format(*args))
                except Exception:
                    init_facts.append(f"{pname} ({', '.join(args)})")
            else:
                init_facts.append(f"{pname} ({', '.join(args)})")

    goal_match = re.search(r'\(:goal\s*(.*)', clean_pddl, re.IGNORECASE | re.DOTALL)
    goal_facts = []
    if goal_match:
        for fact in re.findall(r'\(([^()]+)\)', goal_match.group(1)):
            parts = fact.strip().split()
            if not parts or parts[0].lower() in ('and', 'or', 'not'):
                continue
            pname, args = parts[0], parts[1:]
            if pname in pred_maps:
                try:
                    goal_facts.append(pred_maps[pname].format(*args))
                except Exception:
                    goal_facts.append(f"{pname} ({', '.join(args)})")
            elif pname.lower() in pred_maps:
                try:
                    goal_facts.append(pred_maps[pname.lower()].format(*args))
                except Exception:
                    goal_facts.append(f"{pname} ({', '.join(args)})")
            else:
                goal_facts.append(f"{pname} ({', '.join(args)})")

    lines = [f"Problem Instance: {instance_name} (Domain: {domain_name})"]
    if objects_nl:
        lines.append("\nObjects:")
        for obj in objects_nl:
            lines.append(f"- {obj}")
    if init_facts:
        lines.append("\nInitial State:")
        for f in init_facts:
            lines.append(f"- {f}")
    if goal_facts:
        lines.append("\nGoal State:")
        for f in goal_facts:
            lines.append(f"- {f}")

    return "\n".join(lines)


def load_autoplanbench_original_domain_data(
    domain_name: str,
    selected_instance: Optional[str] = None
) -> Tuple[str, str, str, str, str, List[str]]:
    """
    Loads requirements, ground-truth domain PDDL, and problem instance directly
    from autoplanbench/data/<domain_name>/.
    
    Returns:
      (unified_prompt, domain_desc, problem_desc, ref_domain_pddl, ref_problem_pddl, problem_files)
    """
    d_dir = get_autoplanbench_domain_folder(domain_name)
    
    # 1. Domain description
    dom_desc = ""
    for cand_desc in ["domain_description.txt", "domain_encoding.txt"]:
        enc_path = d_dir / cand_desc
        if enc_path.exists():
            with open(enc_path, "r", encoding="utf-8", errors="ignore") as f:
                dom_desc = f.read().strip()
            break
    if not dom_desc:
        seed1_path = d_dir / "domain_description_seed1.json"
        if seed1_path.exists():
            with open(seed1_path, "r", encoding="utf-8", errors="ignore") as f:
                sdata = json.load(f)
                dom_desc = sdata.get("domain_intro", f"Natural language specification for {domain_name}")

    # 2. Reference ground-truth domain PDDL
    ref_dom = ""
    dom_pddl_path = d_dir / "domain.pddl"
    if dom_pddl_path.exists():
        with open(dom_pddl_path, "r", encoding="utf-8", errors="ignore") as f:
            ref_dom = f.read()

    # 3. Predicate mappings for problem translation
    pred_maps = {}
    seed1_path = d_dir / "domain_description_seed1.json"
    if seed1_path.exists():
        try:
            with open(seed1_path, "r", encoding="utf-8", errors="ignore") as f:
                sdata = json.load(f)
                pred_maps = sdata.get("predicate_mappings", {})
        except Exception:
            pred_maps = {}

    # 4. Problem files & selected instance
    prob_files = list_autoplanbench_problem_files(domain_name)
    inst_name = selected_instance if selected_instance and selected_instance in prob_files else (prob_files[0] if prob_files else "instance-1.pddl")
    
    ref_inst = ""
    prob_desc = ""
    inst_path = d_dir / "orig_problems" / inst_name
    if not inst_path.exists():
        inst_path = d_dir / "problems" / inst_name
    if inst_path.exists():
        with open(inst_path, "r", encoding="utf-8", errors="ignore") as f:
            ref_inst = f.read()
        prob_desc = translate_autoplanbench_problem(ref_inst, pred_maps, inst_name, domain_name)

    unified_prompt = f"{dom_desc}\n\n{prob_desc}".strip()
    return unified_prompt, dom_desc, prob_desc, ref_dom, ref_inst, prob_files
