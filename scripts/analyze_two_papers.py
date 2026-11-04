import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

p1 = "paper/markdown/HEART_Coordination_of_Heterogeneous_Expert_Agents.md"
p2 = "paper/markdown/towards_pddl_domain_modelling_copilot.md"

for path in [p1, p2]:
    print(f"\n{'='*30} {os.path.basename(path)} {'='*30}")
    content = open(path, encoding="utf-8").read()
    
    # Check title / authors from first 1500 chars
    print("--- TITLE / HEADER ---")
    print(content[:1200].encode('ascii', errors='replace').decode('ascii'))
    print("\n--- LANGGRAPH MATCHES ---")
    matches = [line.strip() for line in content.split("\n") if "langgraph" in line.lower()]
    print(f"Found {len(matches)} lines mentioning LangGraph:")
    for m in matches[:10]:
        clean_m = m.encode('ascii', errors='replace').decode('ascii')
        print(f"  * {clean_m[:140]}")
