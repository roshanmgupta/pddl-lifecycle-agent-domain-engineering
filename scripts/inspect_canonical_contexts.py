import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

paper_dir = r"paper/markdown"
papers = [
    "Grounded_Evaluation_and_Repair_for_NL-to-PDDL_Problem_Generation.md",
    "978-3-030-38561-3.md",
    "7385_Position_LLMs_Can_t_Plan.md",
    "Position_LLMs_Can_t_Plan_But_Can_Help_Planning_in_LLM_Modulo_Frameworks.md",
    "evalution_methodology_proposal-ilche_comments.md"
]

for p in papers:
    fpath = os.path.join(paper_dir, p)
    if not os.path.exists(fpath): continue
    content = open(fpath, encoding="utf-8", errors="ignore").read()
    print(f"\n==================== {p} ====================")
    for line in content.split("\n"):
        if re.search(r"\bcanonical\b", line, re.IGNORECASE):
            clean_line = line.strip().encode('ascii', errors='replace').decode('ascii')
            print(f"- {clean_line[:140]}")
