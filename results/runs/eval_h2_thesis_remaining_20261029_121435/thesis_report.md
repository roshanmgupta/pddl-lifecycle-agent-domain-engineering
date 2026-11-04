# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3

## 2. Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 16      | 100.0%   | 8/16 (50.0%)   | 3.50               | 6366       | 7.61      
ABLATION_NO_TRIAGE       | 16      | 100.0%   | 8/16 (50.0%)   | 3.50               | 4881       | 7.10      
==============================================================================================================
```

### Statistical Significance Tests (H2):
- **Full Agent vs ABLATION_NO_TRIAGE (McNemar on Success)**: Chi2 = 0.0, p-value = 1.0
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon on Iterations)**: W-statistic = 0.0, z = 0.0, p-value = 1.0
