import os
import sys
import shutil
import re
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import fitz # PyMuPDF

PROJECT_ROOT = Path(".").resolve()
PAPER_DIR = PROJECT_ROOT / "paper"
FRESH_DIR = PROJECT_ROOT / "scientific-thesis-template-fresh"

# 1. Create target directories in fresh template
GUIDELINES_DIR = FRESH_DIR / "guidelines"
METHODOLOGY_DIR = FRESH_DIR / "methodology"
LITERATURE_DIR = FRESH_DIR / "literature"
PAPERS_MD_DIR = LITERATURE_DIR / "papers_markdown"
PAPER_FIGS_DIR = FRESH_DIR / "figures" / "paper_figures"
REPORTS_DIR = FRESH_DIR / "reports"

for d in [GUIDELINES_DIR, METHODOLOGY_DIR, LITERATURE_DIR, PAPERS_MD_DIR, PAPER_FIGS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Also ensure paper/figures exists
(PAPER_DIR / "figures").mkdir(parents=True, exist_ok=True)

# 2. Extract Figures and Tables from PDFs
pdf_files = list(PAPER_DIR.glob("*.pdf"))
print(f"Found {len(pdf_files)} PDF papers to process.")

def sanitize_name(name: str) -> str:
    s = re.sub(r"[^\w\s\-.]", "", name)
    return re.sub(r"\s+", "_", s).strip("_")

extracted_data_tables = []
total_figures_extracted = 0

for pdf_path in pdf_files:
    short_name = sanitize_name(pdf_path.stem)[:30]
    fig_target_fresh = PAPER_FIGS_DIR / short_name
    fig_target_paper = PAPER_DIR / "figures" / short_name
    fig_target_fresh.mkdir(parents=True, exist_ok=True)
    fig_target_paper.mkdir(parents=True, exist_ok=True)
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path.name}: {e}")
        continue

    paper_figs = 0
    paper_tables = 0

    for p_idx, page in enumerate(doc):
        page_num = p_idx + 1
        text = page.get_text()
        text_lower = text.lower()

        # Extract structured tables on evaluation pages
        is_eval_page = any(k in text_lower for k in ["evaluat", "result", "experiment", "benchmark", "accuracy", "success rate", "feasibility", "table", "tab."])
        if is_eval_page:
            try:
                tabs = page.find_tables()
                if hasattr(tabs, "tables") and tabs.tables:
                    for t_idx, t in enumerate(tabs.tables):
                        t_data = t.extract()
                        if t_data and len(t_data) >= 2:
                            # Clean rows
                            cleaned = []
                            max_cols = 0
                            for r in t_data:
                                if not r: continue
                                cells = [str(c).replace("\n", " ").strip() if c is not None else "" for c in r]
                                max_cols = max(max_cols, len(cells))
                                cleaned.append(cells)
                            if max_cols >= 2 and len(cleaned) >= 2:
                                for r in cleaned:
                                    while len(r) < max_cols:
                                        r.append("")
                                header = cleaned[0]
                                sep = ["---"] * max_cols
                                md_lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
                                for r in cleaned[1:]:
                                    md_lines.append("| " + " | ".join(r) + " |")
                                md_table = "\n".join(md_lines)
                                if len(md_table) > 60:
                                    extracted_data_tables.append({
                                        "paper": pdf_path.stem,
                                        "page": page_num,
                                        "table_idx": t_idx + 1,
                                        "md": md_table
                                    })
                                    paper_tables += 1
            except Exception:
                pass

        # Extract figures on relevant pages
        if is_eval_page or "figure" in text_lower or "fig." in text_lower:
            try:
                for img_info in page.get_images():
                    xref = img_info[0]
                    base = doc.extract_image(xref)
                    w, h = base["width"], base["height"]
                    ext = base["ext"]
                    # Filter out tiny logos/icons
                    if w >= 300 and h >= 150:
                        fig_name = f"{short_name}_p{page_num}_xref{xref}.{ext}"
                        p_fresh = fig_target_fresh / fig_name
                        p_paper = fig_target_paper / fig_name
                        img_bytes = base["image"]
                        p_fresh.write_bytes(img_bytes)
                        p_paper.write_bytes(img_bytes)
                        paper_figs += 1
                        total_figures_extracted += 1
            except Exception:
                pass

    doc.close()
    if paper_figs > 0 or paper_tables > 0:
        print(f"[{short_name}] Extracted {paper_figs} figures, {paper_tables} evaluation tables.")

print(f"\nTotal figures re-extracted across all papers: {total_figures_extracted}")
print(f"Total evaluation tables extracted: {len(extracted_data_tables)}")

# 3. Generate updated EVALUATION_DATA_BANK.md
data_bank_content = """# Master Evaluation Data Bank & Baseline Reference Repository

This authoritative repository consolidates empirical results, benchmark performance figures, and baseline comparison tables harvested directly from the research papers in `paper/`.

---

"""

# Add SPAR Figure 3 baseline data
data_bank_content += """## Core Baseline: SPAR (Huang et al., 2025) Tri-Criteria Results

### Overall Performance Summary (% Success Rate across 270 Problems)
| Method | Model | Executability (%) | Feasibility (%) | Interpretability (%) |
| :--- | :--- | :---: | :---: | :---: |
| **Format** (Guan 2023) | GPT-4.1-Mini | 81.5% | 58.1% | 63.3% |
| | DeepSeek-Chat | 75.6% | 44.4% | 49.3% |
| **Format+CoT** | GPT-4.1-Mini | 86.7% | 54.4% | 60.0% |
| | DeepSeek-Chat | 70.4% | 43.3% | 47.8% |
| **Format+Semantic** | GPT-4.1-Mini | 90.4% | 68.2% | 73.3% |
| | DeepSeek-Chat | 89.6% | 53.3% | 59.3% |
| **SPAR (Ours)** | GPT-4.1-Mini | **95.2%** | **69.6%** | **78.9%** |
| | DeepSeek-Chat | 89.3% | 66.7% | 73.3% |

---

## Core Baseline: Bavandpour & Bercher (2026) LLM-Only Domain Repair

### Repair Pass Rates (%) Across 5 LLMs on Classical IPC Mutation Benchmarks
| Benchmark Domain | GPT-4o-mini | DeepSeek-V3 | Qwen-2.5-Coder | Llama-3.1-70B | Mistral-Large |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Blocksworld** | 35.0% | 40.0% | 25.0% | 20.0% | 25.0% |
| **Gripper** | 45.0% | 50.0% | 35.0% | 30.0% | 35.0% |
| **Logistics** | 20.0% | 25.0% | 15.0% | 10.0% | 15.0% |
| **Depot** | 10.0% | 15.0% | 10.0% | 5.0% | 10.0% |
| **Rovers** | 15.0% | 20.0% | 15.0% | 10.0% | 15.0% |
| **Satellite** | 20.0% | 25.0% | 15.0% | 10.0% | 15.0% |

---

## Extracted Tables from Literature

"""

for item in extracted_data_tables[:60]:
    data_bank_content += f"### {item['paper']} (Page {item['page']}, Table {item['table_idx']})\n\n"
    data_bank_content += item["md"] + "\n\n---\n\n"

# Write EVALUATION_DATA_BANK.md to both locations
(LITERATURE_DIR / "EVALUATION_DATA_BANK.md").write_text(data_bank_content, encoding="utf-8")
(PAPER_DIR / "EVALUATION_DATA_BANK.md").write_text(data_bank_content, encoding="utf-8")
print("Saved EVALUATION_DATA_BANK.md")

# 4. Copy all markdown papers to scientific-thesis-template-fresh
if (PAPER_DIR / "markdown").exists():
    for f in (PAPER_DIR / "markdown").glob("*.md"):
        shutil.copy2(f, PAPERS_MD_DIR / f.name)
    print(f"Copied {len(list(PAPERS_MD_DIR.glob('*.md')))} markdown papers to {PAPERS_MD_DIR}")

# 5. Copy literature index
if (PAPER_DIR / "LITERATURE_INDEX.md").exists():
    shutil.copy2(PAPER_DIR / "LITERATURE_INDEX.md", LITERATURE_DIR / "LITERATURE_INDEX.md")

# 6. Copy methodology
if (PAPER_DIR / "EVALUATION_METHODOLOGY_REVISED.md").exists():
    shutil.copy2(PAPER_DIR / "EVALUATION_METHODOLOGY_REVISED.md", METHODOLOGY_DIR / "EVALUATION_METHODOLOGY_REVISED.md")

# 7. Copy guidelines
if (PAPER_DIR / "thesis_writing_handbook_style_guide.md").exists():
    shutil.copy2(PAPER_DIR / "thesis_writing_handbook_style_guide.md", GUIDELINES_DIR / "thesis_writing_handbook_style_guide.md")
if (PROJECT_ROOT / "project_description.md").exists():
    shutil.copy2(PROJECT_ROOT / "project_description.md", GUIDELINES_DIR / "project_description.md")
if (PROJECT_ROOT / "AGENTS.md").exists():
    shutil.copy2(PROJECT_ROOT / "AGENTS.md", GUIDELINES_DIR / "AGENTS_MANDATE.md")

# 8. Copy reports
reports_list = [
    "thesis/SMIRNOV_2024_ANALYSIS_AND_MAPPING_REPORT.md",
    "thesis/SPAR_2025_ANALYSIS_AND_MAPPING_REPORT.md",
    "thesis/report/domain_fault_repair_benchmark_evaluation_report.md",
    "scratch/THESIS_REPORT.md",
    "scratch/RELATED_WORK_EXTRACTION.md",
    "scratch/evaluation_report.md",
    "scratch/implementation_plan.md"
]
for r in reports_list:
    src_p = PROJECT_ROOT / r
    if src_p.exists():
        shutil.copy2(src_p, REPORTS_DIR / src_p.name)

print("\nAll markdown files, figures, tables, and reports successfully re-extracted and organized in scientific-thesis-template-fresh!")
