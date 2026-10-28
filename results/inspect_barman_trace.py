import json
import re

log_path = r'C:\Users\Srushti\.gemini\antigravity\brain\9339c029-43ff-4baf-996d-b341a1955898\.system_generated\tasks\task-11317.log'
with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

barman_idx = text.find('[1/2] Evaluating Domain: BARMAN11-BFS')
pipes_idx = text.find('[2/2] Evaluating Domain: PIPESWORLD-NOTANKAGE04-BFS')

barman_text = text[barman_idx:pipes_idx] if pipes_idx != -1 else text[barman_idx:]

lines = barman_text.splitlines()
print(f"Total lines in Barman trace: {len(lines)}")
for i, line in enumerate(lines):
    if 'FAULT LOCALIZATION & REPAIR HINTS' in line or 'REPAIR APPLIED' in line or 'Active Tier' in line or 'SOLVER FAILURE' in line or 'Translator' in line:
        print(f"L{i}: {line}")
        for j in range(i+1, min(len(lines), i+8)):
            if lines[j].strip():
                print(f"   {lines[j]}")
        print("-" * 50)
