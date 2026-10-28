# Domain Fault Repair Evaluation Report (Hierarchical Multi-Granular Fault Localization)

## 1. Tri-Criteria Operational & Semantic Verification Summary

| Domain | Flaw Category | Agent | Syntax | Solvable | Exec | Feas | Interp | E2E Success | Iterations |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `gripper` | `TYPE_SIGNATURE_ARITY_INVERSION` | `CLOSED_LOOP_AST_AGENT` | True | True | True | True | True | **True** | 1 |

## 2. Hierarchical Multi-Granular Fault Localization (H-MGFL) Performance

| Domain | Flaw | Gold Fault Element | L1: Top-1 Element | L1: Top-1 Match | L1: MRR | L2: Repair Op Type | L2: Arity Match | Pre F1 | Add F1 | Del F1 |
|:---|:---|:---|:---|:---:|:---:|:---|:---:|:---:|:---:|:---:|
| `gripper` | `flaw_01_type_signature_arity` | `move` | `move` | True | 1.00 | `RepairOperationType.TYPE_ARITY_ALIGNMENT` | 100% | 1.000 | 1.000 | 1.000 |
