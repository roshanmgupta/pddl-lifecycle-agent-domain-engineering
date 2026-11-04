"""
scripts/generate_curated_flaws_h2.py
Generates the 24 curated flaw benchmark tasks across the 6 core domains
strictly conforming to the 6 core domains evaluation mandate:
- 2 Mutation Operators:
  1. Adding a precondition that cannot be satisfied (2 mutants per domain)
  2. Removing an add effect needed for a goal (2 mutants per domain)
- Total tasks: 6 domains * 4 mutants = 24 tasks
- Adds explicit ';' comments inside domain_flawed.pddl documenting the injected flaw
- Formally validates with Fast Downward that each mutant makes reference problem fail.
"""

import os
import sys
import re
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.paths import get_benchmark_dir
from tools.symbolic_oracles import run_fast_downward

BENCHMARK_ROOT = get_benchmark_dir()

# Definitive 24-Task Curated Flaws Specifications (6 Domains x 4 Mutants)
# Each entry: (flaw_id, operator_type, target_action, mutation_detail, mutate_fn, fix_advice)

def mutate_blocksworld(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: pick-up
        mut = re.sub(r'(:action\s+pick-up[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "pick-up", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'pick-up'", "Remove '(unreachable_precondition)' from action 'pick-up' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: unstack
        mut = re.sub(r'(:action\s+unstack[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "unstack", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'unstack'", "Remove '(unreachable_precondition)' from action 'unstack' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: pick-up remove (holding ?ob)
        mut = re.sub(r'(:action\s+pick-up[\s\S]*?:effect\s*\(and\s*)\(holding\s+\?ob\)\s*', r'\1', clean_text)
        return mut, "pick-up", "Removed required add effect '(holding ?ob)' from action 'pick-up'", "Restore add effect '(holding ?ob)' in action 'pick-up' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: stack remove (on ?ob ?underob)
        mut = re.sub(r'(:action\s+stack[\s\S]*?:effect\s*\(and[\s\S]*?)\(on\s+\?ob\s+\?underob\)\s*', r'\1', clean_text)
        return mut, "stack", "Removed required goal add effect '(on ?ob ?underob)' from action 'stack'", "Restore add effect '(on ?ob ?underob)' in action 'stack' effects."


def mutate_gripper(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: pick
        mut = re.sub(r'(:action\s+pick[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "pick", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'pick'", "Remove '(unreachable_precondition)' from action 'pick' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: move
        mut = re.sub(r'(:action\s+move[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "move", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'move'", "Remove '(unreachable_precondition)' from action 'move' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: pick remove (carry ?r ?obj ?g)
        mut = re.sub(r'(:action\s+pick[\s\S]*?:effect\s*\(and\s*)\(carry\s+\?r\s+\?obj\s+\?g\)\s*', r'\1', clean_text)
        return mut, "pick", "Removed required add effect '(carry ?r ?obj ?g)' from action 'pick'", "Restore add effect '(carry ?r ?obj ?g)' in action 'pick' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: drop remove (at ?obj ?room)
        mut = re.sub(r'(:action\s+drop[\s\S]*?:effect\s*\(and\s*)\(at\s+\?obj\s+\?room\)\s*', r'\1', clean_text)
        return mut, "drop", "Removed required goal add effect '(at ?obj ?room)' from action 'drop'", "Restore add effect '(at ?obj ?room)' in action 'drop' effects."


def mutate_logistics(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: FLY-AIRPLANE
        mut = re.sub(r'(:action\s+FLY-AIRPLANE[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "FLY-AIRPLANE", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'FLY-AIRPLANE'", "Remove '(unreachable_precondition)' from action 'FLY-AIRPLANE' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: LOAD-AIRPLANE
        mut = re.sub(r'(:action\s+LOAD-AIRPLANE[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "LOAD-AIRPLANE", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'LOAD-AIRPLANE'", "Remove '(unreachable_precondition)' from action 'LOAD-AIRPLANE' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: UNLOAD-AIRPLANE remove (at ?obj ?loc)
        mut = re.sub(r'(:action\s+UNLOAD-AIRPLANE[\s\S]*?:effect\s*\(and[\s\S]*?)\(at\s+\?obj\s+\?loc\)\s*', r'\1', clean_text)
        return mut, "UNLOAD-AIRPLANE", "Removed required goal add effect '(at ?obj ?loc)' from action 'UNLOAD-AIRPLANE'", "Restore add effect '(at ?obj ?loc)' in action 'UNLOAD-AIRPLANE' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: FLY-AIRPLANE remove (at ?airplane ?loc-to)
        mut = re.sub(r'(:action\s+FLY-AIRPLANE[\s\S]*?:effect\s*\(and[\s\S]*?)\(at\s+\?airplane\s+\?loc-to\)\s*', r'\1', clean_text)
        return mut, "FLY-AIRPLANE", "Removed required add effect '(at ?airplane ?loc-to)' from action 'FLY-AIRPLANE'", "Restore add effect '(at ?airplane ?loc-to)' in action 'FLY-AIRPLANE' effects."


def mutate_depot(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: Lift
        mut = re.sub(r'(:action\s+Lift[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "Lift", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'Lift'", "Remove '(unreachable_precondition)' from action 'Lift' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: Drive
        mut = re.sub(r'(:action\s+Drive[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "Drive", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'Drive'", "Remove '(unreachable_precondition)' from action 'Drive' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: Drop remove (on ?y ?z)
        mut = re.sub(r'(:action\s+Drop[\s\S]*?:effect\s*\(and[\s\S]*?)\(on\s+\?y\s+\?z\)\s*', r'\1', clean_text)
        return mut, "Drop", "Removed required goal add effect '(on ?y ?z)' from action 'Drop'", "Restore add effect '(on ?y ?z)' in action 'Drop' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: Lift remove (lifting ?x ?y)
        mut = re.sub(r'(:action\s+Lift[\s\S]*?:effect\s*\(and[\s\S]*?)\(lifting\s+\?x\s+\?y\)\s*', r'\1', clean_text)
        return mut, "Lift", "Removed required add effect '(lifting ?x ?y)' from action 'Lift'", "Restore add effect '(lifting ?x ?y)' in action 'Lift' effects."


def mutate_rovers(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: sample_soil
        mut = re.sub(r'(:action\s+sample_soil[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "sample_soil", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'sample_soil'", "Remove '(unreachable_precondition)' from action 'sample_soil' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: navigate
        mut = re.sub(r'(:action\s+navigate[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "navigate", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'navigate'", "Remove '(unreachable_precondition)' from action 'navigate' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: communicate_soil_data remove (communicated_soil_data ?p)
        mut = re.sub(r'(:action\s+communicate_soil_data[\s\S]*?:effect\s*\(and[\s\S]*?)\(communicated_soil_data\s+\?p\)\s*', r'\1', clean_text)
        return mut, "communicate_soil_data", "Removed required goal add effect '(communicated_soil_data ?p)' from action 'communicate_soil_data'", "Restore add effect '(communicated_soil_data ?p)' in action 'communicate_soil_data' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: sample_soil remove (have_soil_analysis ?x ?p)
        mut = re.sub(r'(:action\s+sample_soil[\s\S]*?:effect\s*\(and[\s\S]*?)\(have_soil_analysis\s+\?x\s+\?p\)\s*', r'\1', clean_text)
        return mut, "sample_soil", "Removed required add effect '(have_soil_analysis ?x ?p)' from action 'sample_soil'", "Restore add effect '(have_soil_analysis ?x ?p)' in action 'sample_soil' effects."


def mutate_satellite(clean_text, flaw_id):
    if flaw_id == "flaw_01_unsatisfiable_precondition_1":
        # Op 1: calibrate
        mut = re.sub(r'(:action\s+calibrate[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "calibrate", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'calibrate'", "Remove '(unreachable_precondition)' from action 'calibrate' preconditions."
    elif flaw_id == "flaw_02_unsatisfiable_precondition_2":
        # Op 1: turn_to
        mut = re.sub(r'(:action\s+turn_to[\s\S]*?:precondition\s*\(and\s*)', r'\1(unreachable_precondition) ', clean_text)
        mut = re.sub(r'(\(:predicates\s*)', r'\1(unreachable_precondition)\n  ', mut)
        return mut, "turn_to", "Added unsatisfiable precondition '(unreachable_precondition)' to action 'turn_to'", "Remove '(unreachable_precondition)' from action 'turn_to' preconditions."
    elif flaw_id == "flaw_03_missing_goal_add_effect_1":
        # Op 2: take_image remove (have_image ?d ?m)
        mut = clean_text.replace(':effect (have_image ?d ?m)', ':effect (and )')
        return mut, "take_image", "Removed required goal add effect '(have_image ?d ?m)' from action 'take_image'", "Restore add effect '(have_image ?d ?m)' in action 'take_image' effects."
    elif flaw_id == "flaw_04_missing_goal_add_effect_2":
        # Op 2: calibrate remove (calibrated ?i)
        mut = clean_text.replace(':effect (calibrated ?i)', ':effect (and )')
        return mut, "calibrate", "Removed required add effect '(calibrated ?i)' from action 'calibrate'", "Restore add effect '(calibrated ?i)' in action 'calibrate' effects."


DOMAINS_MUTATORS = {
    "blocksworld": mutate_blocksworld,
    "gripper": mutate_gripper,
    "logistics": mutate_logistics,
    "depot": mutate_depot,
    "rovers": mutate_rovers,
    "satellite": mutate_satellite
}

FLAW_IDS = [
    ("flaw_01_unsatisfiable_precondition_1", "OPERATOR_1_UNSATISFIABLE_PRECONDITION"),
    ("flaw_02_unsatisfiable_precondition_2", "OPERATOR_1_UNSATISFIABLE_PRECONDITION"),
    ("flaw_03_missing_goal_add_effect_1", "OPERATOR_2_REMOVE_GOAL_ADD_EFFECT"),
    ("flaw_04_missing_goal_add_effect_2", "OPERATOR_2_REMOVE_GOAL_ADD_EFFECT")
]

def main():
    print("=" * 80)
    print(" GENERATING 24 CURATED FLAW BENCHMARK MUTANTS (6 CORE DOMAINS H2)")
    print("=" * 80)

    total_created = 0
    total_verified = 0

    manifest_data = {
        "benchmark_name": "PDDLLifeCycleBench",
        "version": "3.0_curated_h2",
        "description": "Curated fault repair benchmark conforming strictly to H2 evaluation mandate.",
        "taxonomy": {
            "operator_1": "Adding a precondition that cannot be satisfied (12 tasks)",
            "operator_2": "Removing an add effect needed for a goal (12 tasks)"
        },
        "total_domains": len(DOMAINS_MUTATORS),
        "total_flaw_tasks": len(DOMAINS_MUTATORS) * 4,
        "domains": []
    }

    for domain_name, mutate_fn in DOMAINS_MUTATORS.items():
        domain_dir = BENCHMARK_ROOT / domain_name
        clean_dom_file = domain_dir / "domain.pddl"
        prob_file = domain_dir / "orig_problems" / "instance-1.pddl"

        if not clean_dom_file.exists() or not prob_file.exists():
            print(f"[ERROR]: Missing clean domain or problem for {domain_name}")
            continue

        clean_text = clean_dom_file.read_text(encoding="utf-8")

        # Verify clean domain solves reference problem
        gt_solvable, _ = run_fast_downward(str(clean_dom_file), str(prob_file))
        if not gt_solvable:
            print(f"[ERROR]: Clean {domain_name} fails instance-1.pddl! Cannot benchmark.")
            continue
        print(f"\n[DOMAIN: {domain_name.upper()}]: Ground truth verified solvable on instance-1.pddl.")

        flaws_dir = domain_dir / "flaws"
        # Remove old flaw folders
        if flaws_dir.exists():
            shutil.rmtree(flaws_dir)
        flaws_dir.mkdir(parents=True, exist_ok=True)

        dom_info = {
            "domain": domain_name,
            "flaws_count": 4,
            "tasks": []
        }

        for flaw_id, op_type in FLAW_IDS:
            flaw_target_dir = flaws_dir / flaw_id
            flaw_target_dir.mkdir(parents=True, exist_ok=True)

            mutated_text, target_act, mut_detail, fix_advice = mutate_fn(clean_text, flaw_id)

            # Insert explicit PDDL comments (;) inside domain_flawed.pddl
            annotated_pddl = f"""; ==============================================================================
; CURATED FLAW BENCHMARK MUTANT: {flaw_id}
; DOMAIN: {domain_name}
; MUTATION OPERATOR: {op_type}
; TARGET ACTION SCHEMA: {target_act}
; INJECTED FLAW: {mut_detail}
; RATIONALE: Renders action unexecutable or breaks goal reachability
; GROUND TRUTH FIX: {fix_advice}
; ==============================================================================

{mutated_text.strip()}
"""
            flawed_pddl_file = flaw_target_dir / "domain_flawed.pddl"
            flawed_pddl_file.write_text(annotated_pddl, encoding="utf-8")

            # Write flaw_metadata.json
            metadata = {
                "flaw_id": flaw_id,
                "domain": domain_name,
                "flaw_category": "PRECONDITION_UNSATISFIABLE" if "PRECONDITION" in op_type else "ACTION_EFFECT_DELETION",
                "mutation_operator": op_type,
                "target_action": target_act,
                "description": mut_detail,
                "ground_truth_fix": fix_advice,
                "expected_oracle_signal": "Fast Downward reports unsolvable (goal unreachable from initial state)."
            }
            (flaw_target_dir / "flaw_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            # Verify that this mutant genuinely fails the reference problem
            solvable, _ = run_fast_downward(str(flawed_pddl_file), str(prob_file))
            if not solvable:
                print(f"  [VERIFIED]: {flaw_id} ({target_act}) -> Solvable=False (Fails instance-1.pddl as required)")
                total_verified += 1
            else:
                print(f"  [CRITICAL ERROR]: {flaw_id} ({target_act}) was STILL SOLVABLE! Does not break reference problem.")

            total_created += 1
            dom_info["tasks"].append(metadata)

        manifest_data["domains"].append(dom_info)

    # Save manifest
    manifest_file = BENCHMARK_ROOT / "benchmark_manifest_h2.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"\n[MANIFEST]: Saved benchmark manifest to {manifest_file}")

    print("\n" + "=" * 80)
    print(f" COMPLETED: {total_verified}/{total_created} flaw benchmark tasks verified.")
    print("=" * 80)

if __name__ == "__main__":
    main()
