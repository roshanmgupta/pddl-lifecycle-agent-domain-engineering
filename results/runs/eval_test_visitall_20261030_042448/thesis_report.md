# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 1 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 1220       | 8.09      
ABLATION_NO_AST          | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 509        | 11.17     
ZERO_SHOT                | 1       | 100.0%   | 1/1 (100.0%)   | 1.00               | 509        | 9.09      
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
