import os
from pathlib import Path

base = Path("scientific-thesis-template-fresh")
print("--- Directories in scientific-thesis-template-fresh ---")
for d in sorted(base.iterdir()):
    if d.is_dir():
        print(f"  [DIR]  {d.name}")

print("\n--- Key Files ---")
for f in ["main-english.tex", "thesismain.tex", "bibliography.bib", "chapters-en/10 - introduction.tex"]:
    p = base / f
    if p.exists():
        print(f"  [FILE] {f} exists ({p.stat().st_size} bytes)")
    else:
        print(f"  [MISSING] {f}")

print("\n--- Content Counts ---")
md_papers = list((base / "literature" / "papers_markdown").glob("*.md"))
print(f"  Markdown papers: {len(md_papers)}")

figs = list((base / "figures" / "paper_figures").rglob("*.*"))
print(f"  Extracted figures: {len(figs)}")

reports = list((base / "reports").glob("*.md"))
print(f"  Reports: {len(reports)}")

guidelines = list((base / "guidelines").glob("*.md"))
print(f"  Guidelines: {len(guidelines)}")
