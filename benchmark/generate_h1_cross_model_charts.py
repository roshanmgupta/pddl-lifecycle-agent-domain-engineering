import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Publication-quality figure styling
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 9.5
plt.rcParams['figure.titlesize'] = 13.5

out_dirs = [
    'scientific-thesis-template-fresh/figures',
    'figures'
]
for od in out_dirs:
    os.makedirs(od, exist_ok=True)

# ---------------------------------------------------------------------------------
# 1. LOAD DATA FOR DOMAIN-LEVEL COMPARISON
# ---------------------------------------------------------------------------------
gpt_agg = pd.read_csv('results/h1_21_domains_gpt4o_updated_aggregated.csv')
ds_agg = pd.read_csv('results/h1_21_domains_deepseek_updated_aggregated_1.csv')

gpt_cl = gpt_agg[gpt_agg['Architecture'] == 'CLOSED_LOOP_AST_AGENT'].set_index('Domain')
ds_cl = ds_agg[ds_agg['Architecture'] == 'CLOSED_LOOP_AST_AGENT'].set_index('Domain')

all_domains = sorted(list(set(gpt_cl.index).union(set(ds_cl.index))))

domain_data = []
for dom in all_domains:
    g_pass = int(gpt_cl.loc[dom, 'Passed Runs']) if dom in gpt_cl.index else 0
    g_tot = int(gpt_cl.loc[dom, 'Total Runs']) if dom in gpt_cl.index else 3
    d_pass = int(ds_cl.loc[dom, 'Passed Runs']) if dom in ds_cl.index else 0
    d_tot = int(ds_cl.loc[dom, 'Total Runs']) if dom in ds_cl.index else 3
    domain_data.append({
        'domain': dom,
        'gpt_pass': g_pass,
        'gpt_tot': g_tot,
        'ds_pass': d_pass,
        'ds_tot': d_tot
    })

df_dom = pd.DataFrame(domain_data)
df_dom = df_dom.iloc[::-1].reset_index(drop=True)

# ---------------------------------------------------------------------------------
# FIGURE 1: Domain-Level Formulation Comparison (GPT-4o vs DeepSeek-Chat-V3.1)
# ---------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.5, 11))
y_pos = np.arange(len(df_dom))
bar_height = 0.36

rects_gpt = ax.barh(y_pos + bar_height/2, df_dom['gpt_pass'], height=bar_height,
                    label='GPT-4o (Closed-Loop AST Agent)', color='#1f77b4', edgecolor='black', linewidth=0.7)
rects_ds = ax.barh(y_pos - bar_height/2, df_dom['ds_pass'], height=bar_height,
                   label='DeepSeek-Chat-V3.1 (Closed-Loop AST Agent)', color='#2ca02c', edgecolor='black', linewidth=0.7)

for i in range(len(df_dom)):
    if i % 2 == 0:
        ax.axhspan(i - 0.5, i + 0.5, color='#f7f7f9', zorder=0)

ax.set_yticks(y_pos)
ax.set_yticklabels(df_dom['domain'], fontweight='bold', fontsize=10)
ax.set_xlabel('Number of Independent Formulation Runs Passed (out of 3 runs)', fontweight='bold', labelpad=8)
ax.set_title('Domain Modelling Benchmark (Hypothesis H1):\nRuns Successfully Verified by Domain (GPT-4o vs. DeepSeek-Chat-V3.1)',
             fontweight='bold', pad=32, fontsize=13)
ax.set_xlim(0, 3.7)
ax.set_ylim(-0.8, len(df_dom) - 0.2)
ax.set_xticks([0, 1, 2, 3])
ax.grid(axis='x', linestyle='--', alpha=0.6, zorder=0)

for i, (g_val, d_val, g_tot, d_tot) in enumerate(zip(df_dom['gpt_pass'], df_dom['ds_pass'], df_dom['gpt_tot'], df_dom['ds_tot'])):
    ax.text(g_val + 0.08, i + bar_height/2, f"{g_val}/{g_tot}", va='center', fontsize=9.5, fontweight='bold', color='#1f77b4')
    ax.text(d_val + 0.08, i - bar_height/2, f"{d_val}/{d_tot}", va='center', fontsize=9.5, fontweight='bold', color='#2ca02c')

ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=2, framealpha=0.95, facecolor='white', edgecolor='#cccccc', fontsize=10.5)

plt.tight_layout()

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h1-domain-task-formulation-comparison.pdf'))
    fig.savefig(os.path.join(od, 'h1-domain-task-formulation-comparison.png'), dpi=300)
plt.close(fig)
print("Saved Chart 1: h1-domain-task-formulation-comparison")

# ---------------------------------------------------------------------------------
# FIGURE 2: 3-Way Comparative Macro Summary (Full Agent vs No-AST Ablation vs Zero-Shot)
# ---------------------------------------------------------------------------------
fig, ((ax_succ, ax_iter), (ax_cost, ax_svr)) = plt.subplots(2, 2, figsize=(12.0, 9.5))

models = ['GPT-4o', 'DeepSeek-Chat-V3.1']
x = np.arange(len(models))
width = 0.25

# Color scheme for the 3 conditions
col_cl = '#2b5c8f'   # Deep Blue - Full Agent
col_un = '#e67e22'   # Warm Amber - No-AST Ablation
col_zs = '#7f8c8d'   # Neutral Slate Gray - Zero-Shot Baseline

# 1. Panel A: Majority Task Success Rate (%)
cl_rates = [12/21 * 100, 11/21 * 100]  # 57.1%, 52.4%
un_rates = [4/21 * 100, 10/18 * 100]   # 19.0%, 55.6%
zs_rates = [3/21 * 100, 5/21 * 100]    # 14.3%, 23.8%

r1_s = ax_succ.bar(x - width, cl_rates, width, label='Closed-Loop Full Agent (AST)', color=col_cl, edgecolor='black', linewidth=0.7)
r2_s = ax_succ.bar(x,         un_rates, width, label='No-AST Ablation (Raw)',        color=col_un, edgecolor='black', linewidth=0.7)
r3_s = ax_succ.bar(x + width, zs_rates, width, label='Zero-Shot Baseline (Raw)',     color=col_zs, edgecolor='black', linewidth=0.7)

ax_succ.set_ylabel('Task Success Rate (%)', fontweight='bold')
ax_succ.set_title('(A) Majority Task Success Rate (>= 2/3 Runs Passed)', fontweight='bold')
ax_succ.set_xticks(x)
ax_succ.set_xticklabels(models, fontweight='bold', fontsize=11)
ax_succ.set_ylim(0, 75)
ax_succ.grid(axis='y', linestyle='--', alpha=0.6)
ax_succ.legend(framealpha=0.95, loc='upper right', fontsize=9)

for rect, val, num, den in zip(r1_s, cl_rates, [12, 11], [21, 21]):
    ax_succ.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num}/{den})", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val, num, den in zip(r2_s, un_rates, [4, 10], [21, 18]):
    ax_succ.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num}/{den})", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val, num, den in zip(r3_s, zs_rates, [3, 5], [21, 21]):
    ax_succ.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num}/{den})", ha='center', va='bottom', fontsize=8.5)

# 2. Panel B: Mean Convergence Iterations (Penalized P=6)
cl_iters = [3.22, 3.30]
un_iters = [4.86, 3.49]
zs_iters = [5.29, 4.89]

r1_i = ax_iter.bar(x - width, cl_iters, width, label='Closed-Loop Full Agent (AST)', color=col_cl, edgecolor='black', linewidth=0.7)
r2_i = ax_iter.bar(x,         un_iters, width, label='No-AST Ablation (Raw)',        color=col_un, edgecolor='black', linewidth=0.7)
r3_i = ax_iter.bar(x + width, zs_iters, width, label='Zero-Shot Baseline (Raw)',     color=col_zs, edgecolor='black', linewidth=0.7)

ax_iter.set_ylabel('Mean Iterations (Penalty P=6)', fontweight='bold')
ax_iter.set_title('(B) Convergence Iterations Efficiency', fontweight='bold')
ax_iter.set_xticks(x)
ax_iter.set_xticklabels(models, fontweight='bold', fontsize=11)
ax_iter.set_ylim(0, 6.2)
ax_iter.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val in zip(r1_i, cl_iters):
    ax_iter.text(rect.get_x() + rect.get_width()/2, val + 0.1, f"{val:.2f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect, val in zip(r2_i, un_iters):
    ax_iter.text(rect.get_x() + rect.get_width()/2, val + 0.1, f"{val:.2f}", ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect, val in zip(r3_i, zs_iters):
    ax_iter.text(rect.get_x() + rect.get_width()/2, val + 0.1, f"{val:.2f}", ha='center', va='bottom', fontsize=9)

# 3. Panel C: Mean Financial Cost (USD per Domain Task)
cl_costs = [0.130, 0.0128]
un_costs = [0.070, 0.0070]
zs_costs = [0.010, 0.0010]

r1_c = ax_cost.bar(x - width, cl_costs, width, label='Closed-Loop Full Agent (AST)', color=col_cl, edgecolor='black', linewidth=0.7)
r2_c = ax_cost.bar(x,         un_costs, width, label='No-AST Ablation (Raw)',        color=col_un, edgecolor='black', linewidth=0.7)
r3_c = ax_cost.bar(x + width, zs_costs, width, label='Zero-Shot Baseline (Raw)',     color=col_zs, edgecolor='black', linewidth=0.7)

ax_cost.set_ylabel('Mean Cost per Domain Task (USD)', fontweight='bold')
ax_cost.set_title('(C) Financial Cost Attribution', fontweight='bold')
ax_cost.set_xticks(x)
ax_cost.set_xticklabels(models, fontweight='bold', fontsize=11)
ax_cost.set_ylim(0, 0.16)
ax_cost.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val in zip(r1_c, cl_costs):
    ax_cost.text(rect.get_x() + rect.get_width()/2, val + 0.005, f"${val:.4f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val in zip(r2_c, un_costs):
    ax_cost.text(rect.get_x() + rect.get_width()/2, val + 0.005, f"${val:.4f}", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val in zip(r3_c, zs_costs):
    ax_cost.text(rect.get_x() + rect.get_width()/2, val + 0.005, f"${val:.4f}", ha='center', va='bottom', fontsize=8.5)

# Annotation for 10.2x cost reduction
ax_cost.annotate('10.2x Cost Reduction\nwith DeepSeek-Chat!', xy=(1 - width, 0.02), xytext=(0.55, 0.08),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
                fontsize=9.5, fontweight='bold', bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffcc', edgecolor='#ddddaa'))

# 4. Panel D: Syntactic Validity Rate (SVR %)
cl_svr = [100.0, 95.2]
no_ast_svr = [33.3, 81.1]
zs_svr = [19.0, 27.4]

r1_v = ax_svr.bar(x - width, cl_svr, width, label='Closed-Loop Full Agent (AST)', color=col_cl, edgecolor='black', linewidth=0.7)
r2_v = ax_svr.bar(x,         no_ast_svr, width, label='No-AST Ablation (Raw)',     color=col_un, edgecolor='black', linewidth=0.7)
r3_v = ax_svr.bar(x + width, zs_svr, width, label='Zero-Shot Baseline (Raw)',     color=col_zs, edgecolor='black', linewidth=0.7)

ax_svr.set_ylabel('Syntactic Validity Rate (%)', fontweight='bold')
ax_svr.set_title('(D) Syntactic Validity Rate (SVR)', fontweight='bold')
ax_svr.set_xticks(x)
ax_svr.set_xticklabels(models, fontweight='bold', fontsize=11)
ax_svr.set_ylim(0, 120)
ax_svr.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val in zip(r1_v, cl_svr):
    ax_svr.text(rect.get_x() + rect.get_width()/2, val + 2.0, f"{val:.1f}%", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val in zip(r2_v, no_ast_svr):
    ax_svr.text(rect.get_x() + rect.get_width()/2, val + 2.0, f"{val:.1f}%", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
for rect, val in zip(r3_v, zs_svr):
    ax_svr.text(rect.get_x() + rect.get_width()/2, val + 2.0, f"{val:.1f}%", ha='center', va='bottom', fontsize=8.5)

fig.suptitle('Cross-Model Domain Modelling Benchmark Summary (Hypothesis H1)\nContrasting Closed-Loop Full Agent vs. No-AST Ablation vs. Zero-Shot Baseline',
             fontweight='bold', fontsize=13, y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.95])

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h1-cross-model-macro-summary.pdf'))
    fig.savefig(os.path.join(od, 'h1-cross-model-macro-summary.png'), dpi=300)
plt.close(fig)
print("Saved Chart 2: h1-cross-model-macro-summary (PDF and PNG) with 3-way condition comparison!")
