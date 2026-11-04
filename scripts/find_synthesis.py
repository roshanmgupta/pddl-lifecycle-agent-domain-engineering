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

results = {}
for fname in active_files:
    fpath = os.path.join(chapters_dir, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    matches = []
    for idx, line in enumerate(lines):
        m = re.findall(r"\b\w*synthes\w*\b", line, re.IGNORECASE)
        if m:
            matches.append((idx + 1, m, line.strip()))
    if matches:
        results[fname] = matches

for fname, matches in results.items():
    print(f"=== {fname} ({len(matches)} occurrences) ===")
    for lno, words, line in matches:
        print(f"  Line {lno}: {words} -> {line[:120]}")
