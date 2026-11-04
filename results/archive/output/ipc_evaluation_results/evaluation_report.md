# Empirical IPC Benchmark Evaluation Report

**Generated:** 2026-10-08 18:16:40  
**Agent Architecture:** `CLOSED_LOOP_AST_AGENT`  
**Total Tasks Evaluated:** 3  

## 1. Summary Across 7 Lifecycle Metrics

| Metric | Empirical Result |
| :--- | :---: |
| **Syntax Validity Rate (SVR)** | **100.0%** (3/3) |
| **Plan Solvability Rate (TR)** | **100.0%** (3/3) |
| **Repair Success Rate (RSR)** | **100.0%** (1/1) |
| **Average Repair Iterations ($\bar{I}$)** | **1.0** |
| **Top-1 Fault Localization Accuracy** | **0.0%** (0/1) |
| **Regression Suite Pass Rate (RPR)** | **100.0%** |
| **Average Cost / Task** | **$0.000307** (1948 tokens) |
| **Average Latency** | **26.92s** |

## 2. Per-Task Empirical Result Table

| Task ID | Domain | Task Type | Syntax Valid | Plan Solvable | Repaired | Iterations | Time (s) | Cost ($) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `gripper_elicit_01` | gripper | ELICITATION | True | True | False | 1 | 40.76s | $0.00039 |
| `gripper_repair_capacity_01` | gripper | SYNTHETIC_FAULT_REPAIR | True | True | True | 1 | 19.58s | $0.00025 |
| `gripper_evolve_01` | gripper | DOMAIN_EVOLUTION | True | True | False | 1 | 20.42s | $0.00028 |
