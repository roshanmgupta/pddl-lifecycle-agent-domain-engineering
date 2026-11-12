import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Set styling for publication-quality figures
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9.5
plt.rcParams['figure.titlesize'] = 14

out_dirs = [
    'scientific-thesis-template-fresh/figures',
    r'C:\Users\Srushti\.gemini\antigravity\brain\920962ba-8190-4e31-9793-4d4793c5f9d2'
]
for od in out_dirs:
    os.makedirs(od, exist_ok=True)

df_ds = pd.read_csv('results/h2_evaluation_84_flaws_runs.csv')
df_gpt = pd.read_csv('results/h2_evaluation_84_flaws_runs_gpt4o.csv')

def parse_pp(s):
    try:
        parts = str(s).split('/')
        return int(parts[0]), int(parts[1])
    except:
        return 0, 0

for df in [df_ds, df_gpt]:
    df['solved'] = df['problems_passed'].apply(lambda x: parse_pp(x)[0])
    df['total'] = df['problems_passed'].apply(lambda x: parse_pp(x)[1])

domains = sorted(df_ds['domain'].unique())

records = []
for d in domains:
    d_ds_cl = df_ds[(df_ds['domain'] == d) & (df_ds['agent_type'] == 'CLOSED_LOOP_AST_AGENT')]
    d_ds_ab = df_ds[(df_ds['domain'] == d) & (df_ds['agent_type'] == 'ABLATION_NO_TRIAGE')]
    
    d_gpt_cl = df_gpt[(df_gpt['domain'] == d) & (df_gpt['agent_type'] == 'CLOSED_LOOP_AST_AGENT')]
    d_gpt_ab = df_gpt[(df_gpt['domain'] == d) & (df_gpt['agent_type'] == 'ABLATION_NO_TRIAGE')]
    
    n_tasks = len(d_ds_cl)
    tot_probs = d_ds_cl['total'].sum()
    
    records.append({
        'domain': d,
        'tasks': n_tasks,
        'tot_probs': tot_probs,
        'gpt_cl_tasks': d_gpt_cl['e2e_success'].sum(),
        'gpt_ab_tasks': d_gpt_ab['e2e_success'].sum(),
        'gpt_cl_solved': d_gpt_cl['solved'].sum(),
        'gpt_ab_solved': d_gpt_ab['solved'].sum(),
        'ds_cl_tasks': d_ds_cl['e2e_success'].sum(),
        'ds_ab_tasks': d_ds_ab['e2e_success'].sum(),
        'ds_cl_solved': d_ds_cl['solved'].sum(),
        'ds_ab_solved': d_ds_ab['solved'].sum(),
    })

data = pd.DataFrame(records)

# Sort domains in a consistent aesthetic order (e.g. reverse alphabetical so top-down reads A-Z)
data = data.iloc[::-1].reset_index(drop=True)

# ---------------------------------------------------------------------------------
# CHART 1: Domain-Level Tasks Successfully Repaired (GPT-4o vs DeepSeek-Chat-V3.1)
# ---------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.5, 11))
y_pos = np.arange(len(data))
bar_height = 0.36

rects_gpt = ax.barh(y_pos + bar_height/2, data['gpt_cl_tasks'], height=bar_height,
                    label='GPT-4o (Closed-Loop AST Agent)', color='#1f77b4', edgecolor='black', linewidth=0.7)
rects_ds = ax.barh(y_pos - bar_height/2, data['ds_cl_tasks'], height=bar_height,
                   label='DeepSeek-Chat-V3.1 (Closed-Loop AST Agent)', color='#2ca02c', edgecolor='black', linewidth=0.7)

# Background alternating shading for clean domain separation
for i in range(len(data)):
    if i % 2 == 0:
        ax.axhspan(i - 0.5, i + 0.5, color='#f7f7f9', zorder=0)

ax.set_yticks(y_pos)
ax.set_yticklabels(data['domain'], fontweight='bold', fontsize=10)
ax.set_xlabel('Number of Flaw Mutant Tasks Successfully Repaired (out of 4 tasks; 2 for visitall)', fontweight='bold', labelpad=8)
ax.set_title('Domain Fault Repair Benchmark (Hypothesis H2):\nTasks Successfully Repaired by Domain (GPT-4o vs. DeepSeek-Chat-V3.1)',
             fontweight='bold', pad=32, fontsize=13)
ax.set_xlim(0, 4.65)
ax.set_ylim(-0.8, len(data) - 0.2)
ax.set_xticks([0, 1, 2, 3, 4])
ax.grid(axis='x', linestyle='--', alpha=0.6, zorder=0)

# Add value labels
for i, (g_val, d_val, t_tot) in enumerate(zip(data['gpt_cl_tasks'], data['ds_cl_tasks'], data['tasks'])):
    ax.text(g_val + 0.08, i + bar_height/2, f"{g_val}/{t_tot}", va='center', fontsize=9.5, fontweight='bold', color='#1f77b4')
    ax.text(d_val + 0.08, i - bar_height/2, f"{d_val}/{t_tot}", va='center', fontsize=9.5, fontweight='bold', color='#2ca02c')

ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=2, framealpha=0.95, facecolor='white', edgecolor='#cccccc', fontsize=10.5)
plt.tight_layout()

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h2_domain_task_repair_comparison.png'), dpi=300)
    fig.savefig(os.path.join(od, 'h2_domain_task_repair_comparison.pdf'))
plt.close(fig)
print("Saved Chart 1: h2_domain_task_repair_comparison")

# ---------------------------------------------------------------------------------
# CHART 2: Problem Instances Solved vs. Failed to Repair by Domain
# ---------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 11), sharey=True)

# Subplot 1: GPT-4o
ax1.barh(y_pos, data['gpt_cl_solved'], color='#2b5c8f', edgecolor='black', linewidth=0.6, label='Solved Problems')
ax1.barh(y_pos, data['tot_probs'] - data['gpt_cl_solved'], left=data['gpt_cl_solved'],
         color='#e26d5c', edgecolor='black', linewidth=0.6, label='Unsolved / Failed Problems')

for i, (solv, tot) in enumerate(zip(data['gpt_cl_solved'], data['tot_probs'])):
    pct = (solv / tot) * 100 if tot > 0 else 0
    ax1.text(tot + 2, i, f"{solv}/{tot} ({pct:.0f}%)", va='center', fontsize=8.5, fontweight='bold')

ax1.set_yticks(y_pos)
ax1.set_yticklabels(data['domain'], fontweight='bold', fontsize=9.5)
ax1.set_xlabel('Number of Problem Instances', fontweight='bold', labelpad=8)
ax1.set_title('GPT-4o (Closed-Loop AST Agent)', fontweight='bold', fontsize=12, color='#2b5c8f', pad=10)
ax1.set_xlim(0, 160)
ax1.set_ylim(-0.8, len(data) - 0.2)
ax1.grid(axis='x', linestyle='--', alpha=0.5)

# Subplot 2: DeepSeek-Chat-V3.1
ax2.barh(y_pos, data['ds_cl_solved'], color='#2e8b57', edgecolor='black', linewidth=0.6, label='Solved Problems')
ax2.barh(y_pos, data['tot_probs'] - data['ds_cl_solved'], left=data['ds_cl_solved'],
         color='#f4a261', edgecolor='black', linewidth=0.6, label='Unsolved / Failed Problems')

for i, (solv, tot) in enumerate(zip(data['ds_cl_solved'], data['tot_probs'])):
    pct = (solv / tot) * 100 if tot > 0 else 0
    ax2.text(tot + 2, i, f"{solv}/{tot} ({pct:.0f}%)", va='center', fontsize=8.5, fontweight='bold')

ax2.set_xlabel('Number of Problem Instances', fontweight='bold', labelpad=8)
ax2.set_title('DeepSeek-Chat-V3.1 (Closed-Loop AST Agent)', fontweight='bold', fontsize=12, color='#2e8b57', pad=10)
ax2.set_xlim(0, 160)
ax2.set_ylim(-0.8, len(data) - 0.2)
ax2.grid(axis='x', linestyle='--', alpha=0.5)

# Background shading across both subplots
for i in range(len(data)):
    if i % 2 == 0:
        ax1.axhspan(i - 0.5, i + 0.5, color='#f7f7f9', zorder=0)
        ax2.axhspan(i - 0.5, i + 0.5, color='#f7f7f9', zorder=0)

handles = [
    plt.Rectangle((0,0),1,1, color='#2b5c8f', ec='black', lw=0.6, label='GPT-4o Solved'),
    plt.Rectangle((0,0),1,1, color='#e26d5c', ec='black', lw=0.6, label='GPT-4o Failed'),
    plt.Rectangle((0,0),1,1, color='#2e8b57', ec='black', lw=0.6, label='DeepSeek Solved'),
    plt.Rectangle((0,0),1,1, color='#f4a261', ec='black', lw=0.6, label='DeepSeek Failed'),
]
fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 0.94), ncol=4, framealpha=0.95, fontsize=10)

fig.suptitle('Hypothesis H2: Problem Instances Solved vs. Failed by Domain\nComparing GPT-4o vs. DeepSeek-Chat-V3.1 across 82 Flaw Mutant Tasks',
             fontweight='bold', fontsize=13.5, y=0.99)

plt.tight_layout(rect=[0, 0, 1, 0.92])

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h2_problem_instances_by_domain.png'), dpi=300)
    fig.savefig(os.path.join(od, 'h2_problem_instances_by_domain.pdf'))
plt.close(fig)
print("Saved Chart 2: h2_problem_instances_by_domain")

# ---------------------------------------------------------------------------------
# CHART 3: Macro Executive Summary & Telemetry Dashboard
# ---------------------------------------------------------------------------------
fig, ((ax_succ, ax_prob), (ax_cost, ax_iter)) = plt.subplots(2, 2, figsize=(11, 8.5))

models = ['GPT-4o', 'DeepSeek-Chat-V3.1']
colors_cl = ['#1f77b4', '#2ca02c']
colors_ab = ['#aec7e8', '#98df8a']

# 1. Task Success Rate (%)
x = np.arange(len(models))
width = 0.35

cl_task_rates = [56/82 * 100, 53/82 * 100]
ab_task_rates = [50/82 * 100, 42/82 * 100]

r1 = ax_succ.bar(x - width/2, cl_task_rates, width, label='Closed-Loop Full Agent', color=colors_cl, edgecolor='black', linewidth=0.7)
r2 = ax_succ.bar(x + width/2, ab_task_rates, width, label='No-Triage Baseline', color=colors_ab, edgecolor='black', linewidth=0.7)

ax_succ.set_ylabel('Binary Repair Rate (%)', fontweight='bold')
ax_succ.set_title('(A) Task Repair Success Rate (N=82)', fontweight='bold')
ax_succ.set_xticks(x)
ax_succ.set_xticklabels(models, fontweight='bold')
ax_succ.set_ylim(0, 85)
ax_succ.grid(axis='y', linestyle='--', alpha=0.6)
ax_succ.legend(framealpha=0.9)

for rect, val, num in zip(r1, cl_task_rates, [56, 53]):
    ax_succ.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num}/82)", ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect, val, num in zip(r2, ab_task_rates, [50, 42]):
    ax_succ.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num}/82)", ha='center', va='bottom', fontsize=8.5)

# 2. Problem Instance Pass Rate (%)
cl_prob_rates = [1134/1566 * 100, 1151/1566 * 100]
ab_prob_rates = [1062/1566 * 100, 1006/1566 * 100]

r1_p = ax_prob.bar(x - width/2, cl_prob_rates, width, label='Closed-Loop Full Agent', color=colors_cl, edgecolor='black', linewidth=0.7)
r2_p = ax_prob.bar(x + width/2, ab_prob_rates, width, label='No-Triage Baseline', color=colors_ab, edgecolor='black', linewidth=0.7)

ax_prob.set_ylabel('Problem Pass Rate (%)', fontweight='bold')
ax_prob.set_title('(B) Problem Instance Pass Rate (N=1,566)', fontweight='bold')
ax_prob.set_xticks(x)
ax_prob.set_xticklabels(models, fontweight='bold')
ax_prob.set_ylim(0, 90)
ax_prob.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val, num in zip(r1_p, cl_prob_rates, [1134, 1151]):
    ax_prob.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num})", ha='center', va='bottom', fontsize=9, fontweight='bold')
for rect, val, num in zip(r2_p, ab_prob_rates, [1062, 1006]):
    ax_prob.text(rect.get_x() + rect.get_width()/2, val + 1.5, f"{val:.1f}%\n({num})", ha='center', va='bottom', fontsize=8.5)

# 3. Total Financial Cost (USD)
costs_cl = [13.92, 0.35]
costs_ab = [7.81, 0.24]

r1_c = ax_cost.bar(x - width/2, costs_cl, width, label='Closed-Loop Full Agent', color=colors_cl, edgecolor='black', linewidth=0.7)
r2_c = ax_cost.bar(x + width/2, costs_ab, width, label='No-Triage Baseline', color=colors_ab, edgecolor='black', linewidth=0.7)

ax_cost.set_ylabel('Total Cost (USD)', fontweight='bold')
ax_cost.set_title('(C) Financial Cost Attribution (82 Tasks)', fontweight='bold')
ax_cost.set_xticks(x)
ax_cost.set_xticklabels(models, fontweight='bold')
ax_cost.set_ylim(0, 16.5)
ax_cost.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val in zip(r1_c, costs_cl):
    ax_cost.text(rect.get_x() + rect.get_width()/2, val + 0.4, f"${val:.2f}", ha='center', va='bottom', fontsize=9.5, fontweight='bold')
for rect, val in zip(r2_c, costs_ab):
    ax_cost.text(rect.get_x() + rect.get_width()/2, val + 0.4, f"${val:.2f}", ha='center', va='bottom', fontsize=9)

# Note about 40x cost reduction
ax_cost.annotate('39.8x Cost Reduction\nwith DeepSeek-Chat-V3.1!', xy=(1, 0.5), xytext=(0.7, 8.5),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.2),
                fontsize=9.5, fontweight='bold', bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffcc', edgecolor='#ddddaa'))

# 4. Mean Repair Iterations (Penalized P=3)
iters_cl = [1.77, 1.77]
iters_ab = [2.09, 2.05]

r1_i = ax_iter.bar(x - width/2, iters_cl, width, label='Closed-Loop Full Agent', color=colors_cl, edgecolor='black', linewidth=0.7)
r2_i = ax_iter.bar(x + width/2, iters_ab, width, label='No-Triage Baseline', color=colors_ab, edgecolor='black', linewidth=0.7)

ax_iter.set_ylabel('Mean Iterations (k_max=3, P=3)', fontweight='bold')
ax_iter.set_title('(D) Convergence Iterations Efficiency', fontweight='bold')
ax_iter.set_xticks(x)
ax_iter.set_xticklabels(models, fontweight='bold')
ax_iter.set_ylim(0, 2.6)
ax_iter.grid(axis='y', linestyle='--', alpha=0.6)

for rect, val in zip(r1_i, iters_cl):
    ax_iter.text(rect.get_x() + rect.get_width()/2, val + 0.05, f"{val:.2f}", ha='center', va='bottom', fontsize=9.5, fontweight='bold')
for rect, val in zip(r2_i, iters_ab):
    ax_iter.text(rect.get_x() + rect.get_width()/2, val + 0.05, f"{val:.2f}", ha='center', va='bottom', fontsize=9)

fig.suptitle('Cross-Model Telemetry & Repair Efficiency Dashboard (Hypothesis H2)\nGPT-4o vs. DeepSeek-Chat-V3.1 (82 Tasks, 1,566 Problem Instances)',
             fontweight='bold', fontsize=13, y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.95])

for od in out_dirs:
    fig.savefig(os.path.join(od, 'h2_cross_model_macro_summary.png'), dpi=300)
    fig.savefig(os.path.join(od, 'h2_cross_model_macro_summary.pdf'))
plt.close(fig)
print("Saved Chart 3: h2_cross_model_macro_summary")
print("All charts generated successfully!")
