# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 1 | **Max Retries**: 5

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 7       | 100.0%   | 5/7 (71.4%)    | 2.43               | 17690      | 170.58    
ABLATION_NO_AST          | 7       | 100.0%   | 4/7 (57.1%)    | 3.14               | 5820       | 70.06     
ZERO_SHOT                | 7       | 100.0%   | 4/7 (57.1%)    | 3.14               | 2044       | 30.44     
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 1 vs 0)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 1 vs 0)
