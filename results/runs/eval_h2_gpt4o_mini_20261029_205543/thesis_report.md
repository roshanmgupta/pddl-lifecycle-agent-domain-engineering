# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: openai/gpt-4o-mini | **Runs per Task**: 3 | **Max Retries**: 3

## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 24      | 100.0%   | 19/24 (79.2%)  | 2.35               | 14625      | 23.72     
ABLATION_NO_TRIAGE       | 24      | 100.0%   | 19/24 (79.2%)  | 2.25               | 14409      | 22.41     
==============================================================================================================
```

### Statistical Significance Tests (H2):
- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = 0.0, p-value = 1.0
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = 13.5, z = -0.5601, p-value = 0.5754
