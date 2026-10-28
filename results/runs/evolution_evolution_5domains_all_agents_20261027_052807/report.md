# Domain Evolution Benchmark Report

- **Experiment Tag**: `evolution_5domains_all_agents`
- **Output Run Folder**: `E:\Rosh\Thesis\pddl_lifecycle_agent\results\runs\evolution_evolution_5domains_all_agents_20261027_052807`

| Domain | Evolution Task | Agent | Syntax | Target Exec | Target Feas | Ref Interp (%) | Macro F1 | Iters (k) | Code |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| logistics | evolution_01_feature_addition | CLOSED_LOOP_AST_AGENT | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| logistics | evolution_01_feature_addition | ZERO_SHOT | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| logistics | evolution_01_feature_addition | ABLATION_NO_MAINTENANCE | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| logistics | evolution_01_feature_addition | ABLATION_NO_TRIAGE | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| gripper | evolution_01_feature_addition | CLOSED_LOOP_AST_AGENT | True | **True** | True | 0.0% | 0.900 | 6 | `EVO.E: Reference Interpretability Regression` |
| gripper | evolution_01_feature_addition | ZERO_SHOT | True | **True** | True | 0.0% | 0.900 | 2 | `EVO.E: Reference Interpretability Regression` |
| gripper | evolution_01_feature_addition | ABLATION_NO_MAINTENANCE | True | **True** | True | 0.0% | 0.900 | 1 | `EVO.E: Reference Interpretability Regression` |
| gripper | evolution_01_feature_addition | ABLATION_NO_TRIAGE | True | **True** | True | 0.0% | 0.900 | 6 | `EVO.E: Reference Interpretability Regression` |
| satellite | evolution_01_feature_addition | CLOSED_LOOP_AST_AGENT | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| satellite | evolution_01_feature_addition | ZERO_SHOT | True | **True** | True | 100.0% | 1.000 | 1 | `EVO.A1: First-Attempt Verified Evolution` |
| satellite | evolution_01_feature_addition | ABLATION_NO_MAINTENANCE | False | **False** | False | 0.0% | 0.000 | 1 | `EVO.B: Syntax Parse Failure` |
| satellite | evolution_01_feature_addition | ABLATION_NO_TRIAGE | False | **False** | False | 0.0% | 0.000 | 1 | `EVO.B: Syntax Parse Failure` |
| rovers | evolution_01_feature_addition | CLOSED_LOOP_AST_AGENT | True | **True** | False | 0.0% | 0.393 | 6 | `EVO.D: Target Feasibility Divergence` |
| rovers | evolution_01_feature_addition | ZERO_SHOT | False | **False** | False | 0.0% | 0.000 | 1 | `EVO.B: Syntax Parse Failure` |
| rovers | evolution_01_feature_addition | ABLATION_NO_MAINTENANCE | True | **True** | True | 0.0% | 0.829 | 1 | `EVO.E: Reference Interpretability Regression` |
