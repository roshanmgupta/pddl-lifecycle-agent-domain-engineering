import os
import re

chapters_dir = r"scientific-thesis-template-fresh/chapters-en"
for fname in ["20 - background.tex", "30 - problem exposition.tex", "40 - first real chapter.tex", "50 - second real chapter.tex"]:
    fpath = os.path.join(chapters_dir, fname)
    lines = open(fpath, encoding="utf-8").readlines()
    print(f"\n==================== {fname} ====================")
    for idx, line in enumerate(lines):
        if re.search(r"\bsynthes\w*", line, re.IGNORECASE):
            print(f"L{idx+1}: {line.strip()}")
