import os
import re
from collections import Counter

chapters_dir = r"scientific-thesis-template-fresh/chapters-en"
active_files = [
    "10 - introduction.tex", "20 - background.tex", "30 - problem exposition.tex",
    "40 - first real chapter.tex", "50 - second real chapter.tex",
    "60 - evaluation.tex", "90 - conclusion.tex"
]

patterns = {
    "synthesis / generation": [r"\bsynthes\w*", r"\bgenerat\w*"],
    "repair / fix / patch": [r"\brepair\w*", r"\bfix\w*", r"\bpatch\w*", r"\bcorrect\w*"],
    "fault / flaw / defect / bug / error": [r"\bfault\w*", r"\bflaw\w*", r"\bdefect\w*", r"\bbug\w*", r"\berror\w*"],
    "localization / diagnosis / triage": [r"\blocaliz\w*", r"\bdiagnos\w*", r"\btriage\w*"],
    "ground truth / reference / gold": [r"\bground[- ]truth\w*", r"\breference\w*", r"\bgold\w*"],
    "verification / validation": [r"\bverif\w*", r"\bvalid\w*"],
    "prompt / re-prompt / retry": [r"\bprompt\w*", r"\bre[- ]prompt\w*", r"\bretry\w*"],
    "LLM / language model": [r"\bLLM\w*", r"\blanguage model\w*"]
}

for cat, regexes in patterns.items():
    print(f"=== Category: {cat} ===")
    for r in regexes:
        total = 0
        file_counts = {}
        for f in active_files:
            p = os.path.join(chapters_dir, f)
            if not os.path.exists(p): continue
            txt = open(p, encoding='utf-8', errors='ignore').read()
            c = len(re.findall(r, txt, re.IGNORECASE))
            if c > 0:
                file_counts[f] = c
                total += c
        print(f"  {r}: total={total} {file_counts}")
