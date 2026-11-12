import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Set styling for publication-quality figures
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 9.5
plt.rcParams['ytick.labelsize'] = 9.5
plt.rcParams['figure.titlesize'] = 13.5

out_dirs = [
    'scientific-thesis-template-fresh/figures',
    'figures'
]
for od in out_dirs:
    os.makedirs(od, exist_ok=True)

# Data from Table 6.1 (Domain Formulation Benchmark, H1, GPT-4o, 21 Domains, R=3 runs, k_max=3, P=6)
architectures = [
    'Full Agent\n(Closed-Loop)',
    'No-Triage\nAblation',
    'Unstructured\nRetry',
    'No-AST\nAblation',
    'Zero-Shot\nBaseline'
]

svr = [100.0, 100.0, 84.1, 33.3, 19.0]
success_rate = [57.1, 61.9, 38.1, 19.0, 14.3]
success_counts = [12, 13, 8, 4, 3]
mean_iters = [3.22, 2.95, 4.14, 4.86, 5.29]
tokens = [43651, 21999, 9407, 20706, 2114]
costs = [0.13, 0.07, 0.04, 0.07, 0.01]

colors = ['#1f77b4', '#3b92d4', '#e67e22', '#e74c3c', '#95a5a6']

fig, ((ax_svr, ax_succ), (ax_iter, ax_cost)) = plt.subplots(2, 2, figsize=(11.5, 9.2))

x = np.arange(len(architectures))
bar_width = 0.55

# ---------------------------------------------------------------------------------
# (A) Syntactic Validity Rate (SVR %)
# ---------------------------------------------------------------------------------
bars_svr = ax_svr.bar(x, svr, width=bar_width, color=colors, edgecolor='black', linewidth=0.7)
ax_svr.set_ylabel('Syntactic Validity Rate (%)', fontweight='bold')
ax_svr.set_title('(A) Syntactic Validity Rate (SVR)', fontweight='bold')
ax_svr.set_xticks(x)
ax_svr.set_xticklabels(architectures, fontweight='bold', fontsize=9)
ax_svr.set_ylim(0, 115)
ax_svr.grid(axis='y', linestyle='--', alpha=0.6)

for bar, val in zip(bars_svr, svr):
    ax_svr.text(bar.get_x() + bar.get_width()/2, val + 2.0, f"{val:.1f}%",
                ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# ---------------------------------------------------------------------------------
# (B) Task Success Rate (%)
# ---------------------------------------------------------------------------------
bars_succ = ax_succ.bar(x, success_rate, width=bar_width, color=colors, edgecolor='black', linewidth=0.7)
ax_succ.set_ylabel('Task Success Rate (%)', fontweight='bold')
ax_succ.set_title('(B) Task Success Rate (>= 2/3 Runs Passed)', fontweight='bold')
ax_succ.set_xticks(x)
ax_succ.set_xticklabels(architectures, fontweight='bold', fontsize=9)
ax_succ.set_ylim(0, 75)
ax_succ.grid(axis='y', linestyle='--', alpha=0.6)

for bar, val, count in zip(bars_succ, success_rate, success_counts):
    ax_succ.text(bar.get_x() + bar.get_width()/2, val + 1.5, f"{val:.1f}%\n({count}/21)",
                 ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# ---------------------------------------------------------------------------------
# (C) Penalized Mean Convergence Iterations (P=6)
# ---------------------------------------------------------------------------------
bars_iter = ax_iter.bar(x, mean_iters, width=bar_width, color=colors, edgecolor='black', linewidth=0.7)
ax_iter.set_ylabel('Mean Iterations (Penalty P=6)', fontweight='bold')
ax_iter.set_title('(C) Convergence Iterations Efficiency', fontweight='bold')
ax_iter.set_xticks(x)
ax_iter.set_xticklabels(architectures, fontweight='bold', fontsize=9)
ax_iter.set_ylim(0, 6.2)
ax_iter.grid(axis='y', linestyle='--', alpha=0.6)

for bar, val in zip(bars_iter, mean_iters):
    ax_iter.text(bar.get_x() + bar.get_width()/2, val + 0.1, f"{val:.2f}",
                ha='center', va='bottom', fontsize=9.5, fontweight='bold')

# ---------------------------------------------------------------------------------
# (D) Total Financial Cost & Token Consumption
# ---------------------------------------------------------------------------------
bars_cost = ax_cost.bar(x, costs, width=bar_width, color=colors, edgecolor='black', linewidth=0.7)
ax_cost.set_ylabel('Mean Cost per Domain (USD)', fontweight='bold')
ax_cost.set_title('(D) Financial Expenditure per Domain Task', fontweight='bold')
ax_cost.set_xticks(x)
ax_cost.set_xticklabels(architectures, fontweight='bold', fontsize=9)
ax_cost.set_ylim(0, 0.16)
ax_cost.grid(axis='y', linestyle='--', alpha=0.6)

for bar, cost_val, tok_val in zip(bars_cost, costs, tokens):
    ax_cost.text(bar.get_x() + bar.get_width()/2, cost_val + 0.005, f"${cost_val:.2f}\n({tok_val:,} tok)",
                 ha='center', va='bottom', fontsize=8.5, fontweight='bold')

fig.suptitle('Domain Formulation Benchmark Architecture Summary (Hypothesis H1)\nEvaluation across 21 Classical Planning Domains under OpenAI GPT-4o (N=315 Executions)',
             fontweight='bold', fontsize=13, y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.94])

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h1-formulation-architecture-summary.pdf'))
    fig.savefig(os.path.join(od, 'h1-formulation-architecture-summary.png'), dpi=300)

plt.close(fig)
print("Saved H1 formulation architecture summary chart successfully in PDF and PNG!")
