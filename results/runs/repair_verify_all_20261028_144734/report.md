# Domain Fault Repair Evaluation Report

## 1. Decoupled Multi-Stage Verification Funnel Summary

| Domain | Task / Flaw | Agent | SVR | Solvable | Executability | Feasibility | Interpretability | Semantic Soundness | Strict E2E | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `gripper` | `TYPE_SIGNATURE_ARITY_INVERSION` | `ZERO_SHOT` | True | True | True | True | True | True | **True** | 1 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Identifier | Gold Fault Element | L1: Top-1 Element | L1: Top-1 Match | L1: MRR | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| `gripper` | `flaw_01_type_signature_arity` | `move` | `NONE` | False | 0.00 | `NONE` | 100% | 1.000 | 1.000 | 1.000 |
