import sys
sys.path.insert(0, ".")
from benchmark.loader import load_evolution_task

task = load_evolution_task("gripper", "evolution_01_feature_addition")
print("Task type:", task.task_type)
print("Domain family:", task.domain_family)
print("Evolution category:", task.metadata.get("evolution_category"))
print("\n--- Capability Delta Specification ---")
print(task.capability_delta_text)
print("\n--- Baseline Problem ---")
print(task.initial_problem_pddl[:200])
print("\n--- Target Problem ---")
print(task.target_problem_pddl[:200])
print("\n--- Historical Problems Total ---")
print(len(task.historical_problem_cases))
