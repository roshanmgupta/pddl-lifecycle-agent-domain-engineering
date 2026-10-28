import pandas as pd

df = pd.read_csv(r'E:\Rosh\Thesis\pddl_lifecycle_agent\results\runs\full_ipc_pure30_all_20261026_182435\metrics.csv')
failed = df[df['e2e_success'] == False]
for _, r in failed.iterrows():
    print(f"Domain: {r['domain']:<28} | Code: {r['behavioral_code']:<6} | Defect: {r['defect_class']:<25} | Iters: {r['iterations_used']} | F1: {r['action_f1']:.2f}")
    err = str(r['error_summary'])
    print(f"   Summary: {err[:140]}")
