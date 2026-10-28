# Domain Fault Repair Evaluation Report (Decoupled Multi-Stage Verification Funnel)

## 1. Decoupled Multi-Stage Verification Funnel Summary

| Domain | Flaw Category | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `gripper` | `TYPE_SIGNATURE_ARITY_INVERSION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |
| `gripper` | `PRECONDITION_MISALIGNMENT` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | True | **True** | 1 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Flaw | Gold Fault Element | L1: Top-1 Element | L1: Top-1 Match | L1: MRR | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| `gripper` | `flaw_01_type_signature_arity` | `move` | `move` | True | 1.00 | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
| `gripper` | `flaw_02_precondition_misalignment` | `move` | `move` | True | 1.00 | `RepairOperationType.PRECONDITION_RELAXATION` | 100% | 1.000 | 1.000 | 1.000 |
