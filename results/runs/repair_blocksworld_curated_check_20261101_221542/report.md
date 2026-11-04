# Domain Fault Repair Evaluation Report

## 1. Decoupled Multi-Stage Verification Funnel Summary

| Domain | Task / Flaw | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `blocksworld` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Identifier | L1: Top-1 Element | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|
| `blocksworld` | `flaw_01_unsatisfiable_precondition_1` | `pick-up` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_02_unsatisfiable_precondition_2` | `unstack` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_03_missing_goal_add_effect_1` | `pick-up` | `RepairOperationType.GENERAL_AST_REPAIR` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_04_missing_goal_add_effect_2` | `stack` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
