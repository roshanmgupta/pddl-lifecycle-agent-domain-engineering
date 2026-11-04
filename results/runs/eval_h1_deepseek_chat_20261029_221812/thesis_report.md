# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 3 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 6       | 100.0%   | 6/6 (100.0%)   | 1.00               | 2510       | 41.20     
ABLATION_NO_AST          | 6       | 100.0%   | 6/6 (100.0%)   | 1.00               | 1897       | 41.44     
ZERO_SHOT                | 6       | 100.0%   | 6/6 (100.0%)   | 1.28               | 1814       | 31.43     
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
