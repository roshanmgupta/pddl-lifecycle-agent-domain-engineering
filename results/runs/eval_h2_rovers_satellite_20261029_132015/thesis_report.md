# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3

## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 8       | 100.0%   | 5/8 (62.5%)    | 3.13               | 16129      | 32.17     
ABLATION_NO_TRIAGE       | 8       | 100.0%   | 3/8 (37.5%)    | 4.58               | 15985      | 31.09     
==============================================================================================================
```

### Statistical Significance Tests (H2):
- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = 0.5, p-value = 0.5
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = 1.0, z = -1.8869, p-value = 0.05917
