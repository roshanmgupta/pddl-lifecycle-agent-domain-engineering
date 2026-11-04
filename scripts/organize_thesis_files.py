import os
import shutil

base = "scientific-thesis-template"
dirs = [
    os.path.join(base, "guidelines"),
    os.path.join(base, "methodology"),
    os.path.join(base, "literature", "papers_markdown"),
    os.path.join(base, "literature", "paper_figures"),
    os.path.join(base, "reports")
]
for d in dirs:
    os.makedirs(d, exist_ok=True)

# 1. Guidelines
if os.path.exists("paper/thesis_writing_handbook_style_guide.md"):
    shutil.copy2("paper/thesis_writing_handbook_style_guide.md", os.path.join(base, "guidelines", "thesis_writing_handbook_style_guide.md"))
if os.path.exists("project_description.md"):
    shutil.copy2("project_description.md", os.path.join(base, "guidelines", "project_description.md"))
if os.path.exists("AGENTS.md"):
    shutil.copy2("AGENTS.md", os.path.join(base, "guidelines", "AGENTS_MANDATE.md"))

# 2. Methodology
if os.path.exists("paper/EVALUATION_METHODOLOGY_REVISED.md"):
    shutil.copy2("paper/EVALUATION_METHODOLOGY_REVISED.md", os.path.join(base, "methodology", "EVALUATION_METHODOLOGY_REVISED.md"))

# 3. Literature
if os.path.exists("paper/LITERATURE_INDEX.md"):
    shutil.copy2("paper/LITERATURE_INDEX.md", os.path.join(base, "literature", "LITERATURE_INDEX.md"))
if os.path.exists("paper/EVALUATION_DATA_BANK.md"):
    shutil.copy2("paper/EVALUATION_DATA_BANK.md", os.path.join(base, "literature", "EVALUATION_DATA_BANK.md"))

# Papers markdown
if os.path.exists("paper/markdown"):
    for f in os.listdir("paper/markdown"):
        src = os.path.join("paper/markdown", f)
        dst = os.path.join(base, "literature", "papers_markdown", f)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

# Figures
if os.path.exists("paper/figures"):
    for root, d_names, f_names in os.walk("paper/figures"):
        rel = os.path.relpath(root, "paper/figures")
        target_dir = os.path.join(base, "literature", "paper_figures", rel)
        os.makedirs(target_dir, exist_ok=True)
        for f in f_names:
            shutil.copy2(os.path.join(root, f), os.path.join(target_dir, f))

# 4. Reports
reports = [
    ("thesis/SMIRNOV_2024_ANALYSIS_AND_MAPPING_REPORT.md", "SMIRNOV_2024_ANALYSIS_AND_MAPPING_REPORT.md"),
    ("thesis/SPAR_2025_ANALYSIS_AND_MAPPING_REPORT.md", "SPAR_2025_ANALYSIS_AND_MAPPING_REPORT.md"),
    ("thesis/report/domain_fault_repair_benchmark_evaluation_report.md", "domain_fault_repair_benchmark_evaluation_report.md"),
    ("scratch/THESIS_REPORT.md", "THESIS_REPORT.md"),
    ("scratch/RELATED_WORK_EXTRACTION.md", "RELATED_WORK_EXTRACTION.md"),
    ("scratch/evaluation_report.md", "evaluation_report.md"),
    ("scratch/implementation_plan.md", "implementation_plan.md")
]
for src, name in reports:
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(base, "reports", name))

print("Successfully organized all markdown and reference files into scientific-thesis-template!")
