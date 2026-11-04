import os
import re

chapters_dir = r"scientific-thesis-template-fresh/chapters-en"
active_files = [
    "10 - introduction.tex", "10 - introduction.md",
    "20 - background.tex", "20 - background.md",
    "30 - problem exposition.tex", "30 - problem exposition.md",
    "40 - first real chapter.tex", "40 - first real chapter.md",
    "50 - second real chapter.tex", "50 - second real chapter.md",
    "60 - evaluation.tex", "60 - evaluation.md",
    "90 - conclusion.tex", "90 - conclusion.md"
]

for fname in active_files:
    fpath = os.path.join(chapters_dir, fname)
    if not os.path.exists(fpath): continue
    lines = open(fpath, encoding="utf-8").readlines()
    print(f"\n==================== {fname} ====================")
    for idx, line in enumerate(lines):
        if re.search(r"\bsynthes\w*", line, re.IGNORECASE):
            print(f"L{idx+1}: {line.strip()}")
