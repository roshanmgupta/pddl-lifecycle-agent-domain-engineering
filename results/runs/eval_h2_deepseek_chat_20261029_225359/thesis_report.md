# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 3 | **Max Retries**: 3

## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 24      | 100.0%   | 22/24 (91.7%)  | 1.57               | 11985      | 86.65     
ABLATION_NO_TRIAGE       | 24      | 100.0%   | 22/24 (91.7%)  | 1.67               | 12249      | 95.97     
==============================================================================================================
```

### Statistical Significance Tests (H2):
- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = 0.0, p-value = 1.0
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = 2.0, z = -0.9129, p-value = 0.36131
