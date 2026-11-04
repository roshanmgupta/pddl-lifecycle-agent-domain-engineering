import os
import re

chapters_dir = r"scientific-thesis-template-fresh/chapters-en"
tex_files = [
    "10 - introduction.tex", "20 - background.tex", "30 - problem exposition.tex",
    "40 - first real chapter.tex", "50 - second real chapter.tex",
    "60 - evaluation.tex", "90 - conclusion.tex"
]

for f in tex_files:
    fpath = os.path.join(chapters_dir, f)
    if not os.path.exists(fpath): continue
    lines = open(fpath, encoding="utf-8").readlines()
    for idx, line in enumerate(lines):
        if re.search(r"\bcanonical\b", line, re.IGNORECASE):
            print(f"{f}:L{idx+1}: {line.strip()[:120]}")
