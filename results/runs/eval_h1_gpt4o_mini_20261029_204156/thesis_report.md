# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: openai/gpt-4o-mini | **Runs per Task**: 3 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 6       | 100.0%   | 5/6 (83.3%)    | 1.83               | 10053      | 18.86     
ABLATION_NO_AST          | 6       | 100.0%   | 6/6 (100.0%)   | 1.05               | 3476       | 13.87     
ZERO_SHOT                | 6       | 100.0%   | 3/6 (50.0%)    | 3.50               | 1760       | 6.76      
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 1)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.5, p-value = 0.5 (Discordant: 2 vs 0)
