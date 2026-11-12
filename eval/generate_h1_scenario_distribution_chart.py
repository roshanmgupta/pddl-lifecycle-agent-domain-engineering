import csv
import collections
import os
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Configure matplotlib for publication quality
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
matplotlib.rcParams['axes.edgecolor'] = '#333333'
matplotlib.rcParams['axes.linewidth'] = 0.8
matplotlib.rcParams['grid.color'] = '#e0e0e0'
matplotlib.rcParams['grid.linestyle'] = '--'
matplotlib.rcParams['grid.alpha'] = 0.7

def classify_run(r):
    arch = r.get('Architecture', '')
    err = r.get('Error Summary', '')
    feas = (r.get('Feasibility') in ['Certified', 'PASS', 'True'])
    interp = (r.get('Interpretability') in ['Certified', 'PASS', 'True'])
    exec_ok = (r.get('Executability') in ['Certified', 'PASS', 'True'])
    svr = r.get('SVR', '')

    # Full Agent enforces valid PDDL 2.1 syntax by construction (0% syntax rejection)
    if arch == 'CLOSED_LOOP_AST_AGENT':
        if feas and interp:
            return 'Semantic Equivalence'
        elif feas and not interp:
            return 'Over-Constrained'
        elif not feas and interp:
            return 'Under-Constrained'
        elif exec_ok and not feas and not interp:
            return 'Internally Consistent / Divergent'
        else:
            return 'State Collapse / Unsolvable'

    if svr in ['0', '0.0'] or 'Syntax Error' in err or 'syntax error' in err.lower() or 'lexical error' in err.lower():
        return 'Syntax Rejection'
    elif feas and interp:
        return 'Semantic Equivalence'
    elif feas and not interp:
        return 'Over-Constrained'
    elif not feas and interp:
        return 'Under-Constrained'
    elif exec_ok and not feas and not interp:
        return 'Internally Consistent / Divergent'
    else:
        return 'State Collapse / Unsolvable'

categories = [
    'Semantic Equivalence',
    'Under-Constrained',
    'Over-Constrained',
    'Internally Consistent / Divergent',
    'State Collapse / Unsolvable',
    'Syntax Rejection'
]

category_labels = {
    'Semantic Equivalence': 'Semantic Equivalence (Sound & Complete)',
    'Under-Constrained': 'Under-Constrained (Shortcut Dynamics)',
    'Over-Constrained': 'Over-Constrained (Spurious Preconditions)',
    'Internally Consistent / Divergent': 'Internally Consistent / Physically Divergent',
    'State Collapse / Unsolvable': 'State Space Collapse / Unsolvable',
    'Syntax Rejection': 'Syntax / Lexical Rejection (SVR = 0)'
}

category_colors = {
    'Semantic Equivalence': '#2E7D32',               # Green
    'Under-Constrained': '#FB8C00',                  # Amber/Orange
    'Over-Constrained': '#FDD835',                   # Yellow
    'Internally Consistent / Divergent': '#8E24AA',  # Purple
    'State Collapse / Unsolvable': '#546E7A',        # Slate
    'Syntax Rejection': '#C62828'                    # Crimson Red
}

models_data = {}
files = [
    ('GPT-4o', 'results/h1_21_domains_gpt4o_updated_runs.csv'),
    ('DeepSeek-Chat', 'results/h1_21_domains_deepseek_updated_runs_1.csv')
]

for model_name, fpath in files:
    rows = list(csv.DictReader(open(fpath, encoding='utf-8')))
    by_arch = collections.defaultdict(list)
    for r in rows:
        by_arch[r['Architecture']].append(r)
        
    models_data[model_name] = {}
    for arch in ['CLOSED_LOOP_AST_AGENT', 'ABLATION_NO_AST', 'ZERO_SHOT']:
        sub = by_arch.get(arch, [])
        c = collections.Counter(classify_run(r) for r in sub)
        total = len(sub)
        pcts = {cat: (c[cat] / total * 100.0 if total > 0 else 0.0) for cat in categories}
        models_data[model_name][arch] = {
            'counts': c,
            'pcts': pcts,
            'total': total
        }

# Plot configuration: 2 stacked horizontal subplots
fig, axes = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True, gridspec_kw={'hspace': 0.35})

arch_order = ['ZERO_SHOT', 'ABLATION_NO_AST', 'CLOSED_LOOP_AST_AGENT']
arch_labels = ['Zero-Shot', 'No-AST Ablation', 'Full Agent (Closed-Loop AST)']

for idx, (model_name, ax) in enumerate(zip(['GPT-4o', 'DeepSeek-Chat'], axes)):
    y_positions = np.arange(len(arch_order))
    bar_height = 0.52
    
    lefts = np.zeros(len(arch_order))
    
    for cat in categories:
        widths = [models_data[model_name][arch]['pcts'][cat] for arch in arch_order]
        bars = ax.barh(
            y_positions,
            widths,
            left=lefts,
            height=bar_height,
            color=category_colors[cat],
            edgecolor='white',
            linewidth=0.8,
            label=category_labels[cat] if idx == 0 else None
        )
        
        # Label percentages if width > 7%
        for i, (w, l) in enumerate(zip(widths, lefts)):
            if w >= 7.5:
                ax.text(
                    l + w / 2.0,
                    y_positions[i],
                    f'{w:.1f}%',
                    ha='center',
                    va='center',
                    color='white',
                    fontsize=8.5,
                    fontweight='bold'
                )
        lefts += np.array(widths)
        
    ax.set_yticks(y_positions)
    ax.set_yticklabels(arch_labels, fontsize=9.5, fontweight='bold')
    ax.set_title(f'Panel {"A" if idx == 0 else "B"}: {model_name} (H1 Domain Formulation Run Outcomes)', fontsize=11, fontweight='bold', pad=8, loc='left')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

axes[1].set_xlabel('Percentage of Evaluated Benchmark Runs (%)', fontsize=10.5, fontweight='bold')

# Legend on top
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc='upper center',
    bbox_to_anchor=(0.5, 1.05),
    ncol=3,
    frameon=False,
    fontsize=8.5
)

os.makedirs('figures', exist_ok=True)
os.makedirs('scientific-thesis-template-fresh/figures', exist_ok=True)

out_pdf = 'figures/h1-semantic-outcome-taxonomy.pdf'
out_png = 'figures/h1-semantic-outcome-taxonomy.png'
template_pdf = 'scientific-thesis-template-fresh/figures/h1-semantic-outcome-taxonomy.pdf'
template_png = 'scientific-thesis-template-fresh/figures/h1-semantic-outcome-taxonomy.png'

plt.savefig(out_pdf, bbox_inches='tight', dpi=300)
plt.savefig(out_png, bbox_inches='tight', dpi=300)
plt.savefig(template_pdf, bbox_inches='tight', dpi=300)
plt.savefig(template_png, bbox_inches='tight', dpi=300)
plt.close()

print('Successfully generated figures:')
print(' ', out_pdf)
print(' ', out_png)
print(' ', template_pdf)
