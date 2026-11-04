# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: deepseek/deepseek-chat | **Runs per Task**: 1 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 3       | 100.0%   | 1/3 (33.3%)    | 4.33               | 20911      | 125.60    
ABLATION_NO_AST          | 3       | 100.0%   | 1/3 (33.3%)    | 4.33               | 931        | 14.22     
ZERO_SHOT                | 3       | 100.0%   | 2/3 (66.7%)    | 2.67               | 1462       | 25.15     
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.5, p-value = 1.0 (Discordant: 1 vs 1)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 1)
