# Empirical Thesis Evaluation Report: Hypothesis H2 (Unified 24 Tasks)

**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3 | **Total Runs**: 144

## Hypothesis H2: Fault Repair Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 24      | 100.0%   | 20/24 (83.3%)  | 2.01               | 12268      | 19.26     
ABLATION_NO_TRIAGE       | 24      | 100.0%   | 17/24 (70.8%)  | 2.81               | 11996      | 21.30     
==============================================================================================================
```

### Statistical Significance Tests (H2 across 24 Tasks):
- **Full Agent vs ABLATION_NO_TRIAGE (Exact McNemar on Success)**: Chi2 = 1.3333, p-value = 0.25 (Discordant Pairs: Full Agent only = 3, No Triage only = 0)
- **Full Agent vs ABLATION_NO_TRIAGE (Wilcoxon Signed-Rank on Iterations)**: W-statistic = 4.5, z = -2.4895, p-value = 0.01279
