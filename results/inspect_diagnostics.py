import pandas as pd

diag_df = pd.read_csv(r'E:\Rosh\Thesis\pddl_lifecycle_agent\results\runs\full_ipc_pure30_all_20261026_182435\diagnostic_reports.csv')
for d in ['barman11-bfs', 'transport14', 'pipesworld-notankage04-bfs', 'floortile14', 'woodworking08']:
    sub = diag_df[diag_df['domain'] == d]
    if len(sub) > 0:
        r = sub.iloc[0]
        print(f"\n==================== DOMAIN: {d} ====================")
        print("Why Failed:", r.get('why_failed_verdict'))
        print("Faulty Elements:", r.get('faulty_elements'))
        print("Error Categories:", r.get('error_categories'))
        print("Fault Hints:\n", str(r.get('fault_localization_hints'))[:500])
