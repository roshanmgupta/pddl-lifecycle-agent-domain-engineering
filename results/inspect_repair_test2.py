import pandas as pd

df = pd.read_csv(r'E:\Rosh\Thesis\pddl_lifecycle_agent\results\runs\full_ipc_repair_test2_20261026_230040\metrics.csv')
for _, r in df.iterrows():
    print("=" * 60)
    print("Domain:", r['domain'])
    print("E2E Success:", r['e2e_success'])
    print("Plan Valid:", r['is_plan_valid'])
    print("VAL Valid:", r['val_plan_valid'])
    print("Code:", r['behavioral_code'])
    print("Iters Used:", r['iterations_used'])
    print("Action F1:", r['action_f1'])
    print("Plan Length:", r['plan_length'])
    print("Plan Cost:", r['plan_cost'])
    print("Search Time (s):", r['search_time_sec'])
    print("Error Summary:", str(r['error_summary'])[:120])
