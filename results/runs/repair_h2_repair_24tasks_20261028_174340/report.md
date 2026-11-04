# Domain Fault Repair Evaluation Report

## 1. Decoupled Multi-Stage Verification Funnel Summary

| Domain | Task / Flaw | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `blocksworld` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `blocksworld` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `gripper` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `gripper` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `gripper` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | False | False | False | False | False | **False** | 3 |
| `gripper` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 2 |
| `logistics` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `logistics` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `logistics` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 2 |
| `logistics` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `depot` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `depot` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `depot` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | False | False | False | False | False | **False** | 3 |
| `depot` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 3 |
| `rovers` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 3 |
| `rovers` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | False | False | False | False | False | False | **False** | 3 |
| `rovers` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 2 |
| `rovers` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | False | False | False | False | False | **False** | 3 |
| `satellite` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `satellite` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `satellite` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `satellite` | `ACTION_EFFECT_DELETION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | False | True | False | **False** | 3 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Identifier | L1: Top-1 Element | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|
| `blocksworld` | `flaw_01_unsatisfiable_precondition_1` | `pick-up` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_02_unsatisfiable_precondition_2` | `unstack` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_03_missing_goal_add_effect_1` | `None` | `RepairOperationType.GENERAL_AST_REPAIR` | 100% | 1.000 | 1.000 | 1.000 |
| `blocksworld` | `flaw_04_missing_goal_add_effect_2` | `goal predicate (on c b)` | `RepairOperationType.ACTION_ADDITION` | 100% | 1.000 | 1.000 | 1.000 |
| `gripper` | `flaw_01_unsatisfiable_precondition_1` | `pick` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `gripper` | `flaw_02_unsatisfiable_precondition_2` | `move` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `gripper` | `flaw_03_missing_goal_add_effect_1` | `drop` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 0.933 | 0.667 | 1.000 |
| `gripper` | `flaw_04_missing_goal_add_effect_2` | `None` | `RepairOperationType.GENERAL_AST_REPAIR` | 100% | 1.000 | 1.000 | 1.000 |
| `logistics` | `flaw_01_unsatisfiable_precondition_1` | `FLY-AIRPLANE` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `logistics` | `flaw_02_unsatisfiable_precondition_2` | `LOAD-AIRPLANE` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `logistics` | `flaw_03_missing_goal_add_effect_1` | `LOAD-TRUCK` | `RepairOperationType.PRECONDITION_RELAXATION` | 100% | 1.000 | 1.000 | 1.000 |
| `logistics` | `flaw_04_missing_goal_add_effect_2` | `LOAD-TRUCK or LOAD-AIRPLANE` | `RepairOperationType.ACTION_ADDITION` | 100% | 1.000 | 1.000 | 1.000 |
| `depot` | `flaw_01_unsatisfiable_precondition_1` | `Lift` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `depot` | `flaw_02_unsatisfiable_precondition_2` | `None` | `RepairOperationType.PRECONDITION_RELAXATION` | 100% | 1.000 | 1.000 | 1.000 |
| `depot` | `flaw_03_missing_goal_add_effect_1` | `crate0` | `RepairOperationType.GENERAL_AST_REPAIR` | 100% | 1.000 | 0.960 | 1.000 |
| `depot` | `flaw_04_missing_goal_add_effect_2` | `None` | `RepairOperationType.GENERAL_AST_REPAIR` | 100% | 1.000 | 1.000 | 1.000 |
| `rovers` | `flaw_01_unsatisfiable_precondition_1` | `communicate_soil_data` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 0.833 | 0.667 |
| `rovers` | `flaw_02_unsatisfiable_precondition_2` | `communicate_soil_data` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 0.988 | 0.833 | 0.667 |
| `rovers` | `flaw_03_missing_goal_add_effect_1` | `communicate_soil_data` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 0.833 | 0.667 |
| `rovers` | `flaw_04_missing_goal_add_effect_2` | `communicate_soil_data` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 0.963 | 0.667 |
| `satellite` | `flaw_01_unsatisfiable_precondition_1` | `calibrate` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `satellite` | `flaw_02_unsatisfiable_precondition_2` | `turn_to` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `satellite` | `flaw_03_missing_goal_add_effect_1` | `domain.actions` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `satellite` | `flaw_04_missing_goal_add_effect_2` | `switch_on` | `RepairOperationType.EFFECT_ALIGNMENT` | 100% | 1.000 | 0.933 | 0.933 |
