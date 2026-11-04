import re
from pathlib import Path

intro_path = Path("scientific-thesis-template-fresh/chapters-en/10 - introduction.tex")
text = intro_path.read_text(encoding="utf-8")

# Search for pronouns
patterns = [r"\bwe\b", r"\bour\b", r"\bus\b", r"\bI\b", r"\bmy\b", r"\bthe author\b", r"\bthe authors\b"]
found = []
for idx, line in enumerate(text.splitlines()):
    for p in patterns:
        if re.search(p, line, re.IGNORECASE):
            found.append((idx + 1, p, line.strip()))

print(f"Found {len(found)} pronoun/reference matches in 10 - introduction.tex:")
for line_no, pat, content in found:
    print(f"Line {line_no} [{pat}]: {content}")
