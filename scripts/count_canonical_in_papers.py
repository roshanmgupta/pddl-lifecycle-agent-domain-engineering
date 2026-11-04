import os
import re

paper_dir = r"paper/markdown"
papers = [f for f in os.listdir(paper_dir) if f.endswith(".md") and f != "LITERATURE_INDEX.md"]

canonical_papers = {}
total_occurrences = 0

for p in sorted(papers):
    fpath = os.path.join(paper_dir, p)
    content = open(fpath, encoding="utf-8", errors="ignore").read()
    matches = re.findall(r"\bcanonical\w*\b", content, re.IGNORECASE)
    if matches:
        canonical_papers[p] = len(matches)
        total_occurrences += len(matches)

print(f"Total papers examined: {len(papers)}")
print(f"Papers using 'canonical': {len(canonical_papers)} / {len(papers)}")
print(f"Total occurrences across all papers: {total_occurrences}\n")

for p, count in sorted(canonical_papers.items(), key=lambda x: x[1], reverse=True):
    print(f"{p}: {count} occurrences")
