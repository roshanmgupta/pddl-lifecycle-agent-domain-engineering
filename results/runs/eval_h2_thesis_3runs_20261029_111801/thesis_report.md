# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3

## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 24      | 100.0%   | 7/24 (29.2%)   | 4.64               | 3744       | 10.24     
ABLATION_NO_TRIAGE       | 24      | 100.0%   | 6/24 (25.0%)   | 4.94               | 3519       | 11.11     
==============================================================================================================
```

### Statistical Significance Tests (H2):
- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = 0.0, p-value = 1.0
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = 2.5, z = -1.2136, p-value = 0.22492
