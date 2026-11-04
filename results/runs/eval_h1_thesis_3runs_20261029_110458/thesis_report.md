# Empirical Thesis Evaluation Report (Reduced Experimental Design)

**Model**: OpenAI GPT-4o | **Runs per Task**: 3 | **Max Retries**: 3

## 1. Hypothesis H1: Formulation Benchmark (Descriptive Table)
```
==============================================================================================================
CONDITION / AGENT        | TASKS   | SVR      | SUCCESS RATE   | MEAN ITERS (P=6)   | TOKENS     | LATENCY (s)
--------------------------------------------------------------------------------------------------------------
CLOSED_LOOP_AST_AGENT    | 6       | 100.0%   | 6/6 (100.0%)   | 1.11               | 4155       | 14.40     
ABLATION_NO_AST          | 6       | 100.0%   | 6/6 (100.0%)   | 1.17               | 3554       | 12.75     
ZERO_SHOT                | 6       | 100.0%   | 4/6 (66.7%)    | 2.39               | 1777       | 5.59      
==============================================================================================================
```

### Statistical Significance Tests (H1):
- **Full Agent vs ABLATION_NO_AST (McNemar)**: Chi2 = 0.0, p-value = 1.0 (Discordant: 0 vs 0)
- **Full Agent vs ZERO_SHOT (McNemar)**: Chi2 = 0.5, p-value = 0.5 (Discordant: 2 vs 0)
