# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 1 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 2656       | 31.96     
ABLATION_NO_AST          | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 1850       | 35.88     
ZERO_SHOT                | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 1850       | 34.63     
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
