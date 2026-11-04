# Domain Fault Repair Evaluation Report

## 1. Decoupled Multi-Stage Verification Funnel Summary

| Domain | Task / Flaw | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `blocksworld` | `PRECONDITION_UNSATISFIABLE` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Identifier | L1: Top-1 Element | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---:|:---:|
| `blocksworld` | `flaw_01_unsatisfiable_precondition_1` | `pick-up` | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
