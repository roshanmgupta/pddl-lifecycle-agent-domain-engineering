import os
import re
import sys
from pathlib import Path
import pypdf

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path('.').resolve()
PAPER_DIR = PROJECT_ROOT / "paper"
OUT_DIRS = [
    PAPER_DIR / "markdown",
    PROJECT_ROOT / "scientific-thesis-template-fresh" / "literature" / "papers_markdown"
]
INDEX_FILE = PAPER_DIR / "LITERATURE_INDEX.md"

for d in OUT_DIRS:
    d.mkdir(parents=True, exist_ok=True)

HEADING_PATTERNS = [
    r"^(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.\s+([A-Z\s]{3,})",
    r"^(?:\d+)\.?\s+([A-Z][A-Za-z0-9\s,\-]{3,})",
    r"^(?:\d+\.\d+)\.?\s+([A-Z][A-Za-z0-9\s,\-]{3,})",
    r"^(?:Abstract|ABSTRACT)",
    r"^(?:Introduction|INTRODUCTION)",
    r"^(?:Related Work|RELATED WORK|Background|BACKGROUND)",
    r"^(?:Methodology|METHODOLOGY|Proposed Framework|Approach|APPROACH)",
    r"^(?:System Architecture|SYSTEM ARCHITECTURE)",
    r"^(?:Implementation|IMPLEMENTATION)",
    r"^(?:Evaluation|EVALUATION|Experiments|EXPERIMENTS|Results|RESULTS)",
    r"^(?:Discussion|DISCUSSION)",
    r"^(?:Conclusion|CONCLUSION)",
]

REF_SPLIT_PATTERNS = [
    r"\n(?:\d+\.?\s+)?(?:References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*\n",
    r"\n(?:\d+\.?\s+)?(?:References and Notes|REFERENCES AND NOTES)\s*\n",
]

def sanitize_filename(name: str) -> str:
    s = re.sub(r"[^\w\s\-.]", "", name)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s

def extract_text_pypdf(pdf_path: Path):
    reader = pypdf.PdfReader(str(pdf_path))
    pages_text = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
            pages_text.append(t)
        except Exception:
            pass
    return "\n".join(pages_text), len(reader.pages)

def clean_and_format_markdown(raw_text: str, filename: str):
    raw_chars = len(raw_text)
    raw_tokens = raw_chars // 4

    split_pos = -1
    for pat in REF_SPLIT_PATTERNS:
        match = re.search(pat, raw_text)
        if match:
            split_pos = match.start()
            break
            
    has_refs_stripped = False
    if split_pos != -1 and split_pos > (raw_chars * 0.3):
        main_content = raw_text[:split_pos]
        has_refs_stripped = True
    else:
        main_content = raw_text

    lines = [l.strip() for l in main_content.splitlines() if l.strip()]
    
    title = ""
    for l in lines[:10]:
        if len(l) > 15 and not any(k in l.lower() for k in ["arxiv", "ieee", "acm", "proceedings", "conference", "vol.", "no.", "issn", "page", "http"]):
            title = l
            break
    if not title:
        title = filename.replace(".pdf", "").replace("_", " ")

    abstract = ""
    abs_match = re.search(r"(?:Abstract|ABSTRACT)[\s:—–\-]+(.*?)(?=\n\s*(?:I\.|1\.|Introduction|INTRODUCTION)|\n\n\n)", main_content, re.DOTALL)
    if abs_match:
        abstract = " ".join(abs_match.group(1).split())[:400] + "..."
    elif len(lines) > 5:
        abstract = " ".join(lines[3:8])[:350] + "..."

    formatted_lines = []
    for line in main_content.splitlines():
        l_strip = line.strip()
        is_heading = False
        for pat in HEADING_PATTERNS:
            if re.match(pat, l_strip):
                formatted_lines.append(f"\n## {l_strip}\n")
                is_heading = True
                break
        if not is_heading:
            formatted_lines.append(line)

    markdown_body = "\n".join(formatted_lines)
    markdown_body = re.sub(r"\n{3,}", "\n\n", markdown_body)

    clean_chars = len(markdown_body)
    clean_tokens = clean_chars // 4

    metadata = {
        "title": title,
        "abstract": abstract,
        "filename": filename,
        "raw_tokens": str(raw_tokens),
        "clean_tokens": str(clean_tokens),
        "has_refs_stripped": str(has_refs_stripped)
    }

    return markdown_body, metadata, raw_tokens, clean_tokens

def categorize_paper(filename: str, title: str, text: str) -> str:
    t_lower = (filename + " " + title + " " + text[:2000]).lower()
    if any(k in t_lower for k in ["survey", "position", "conceptual", "from formalisers to engineers", "nila"]):
        return "Position / Survey"
    if any(k in t_lower for k in ["repair", "fault", "localization", "defect", "patch", "fixing", "orcaloca", "autostructor"]):
        return "Fault Localization & Repair"
    if any(k in t_lower for k in ["evolution", "maintenance", "continuous", "regression", "plan2evolve"]):
        return "Domain Evolution & Maintenance"
    if any(k in t_lower for k in ["thesis"]):
        return "Prior IAAS Theses"
    if any(k in t_lower for k in ["spar", "aerial robotics", "uav", "generating domain models", "domain generator", "pddlcoder", "more", "planetarium"]):
        return "PDDL Domain Synthesis"
    if any(k in t_lower for k in ["val", "fast downward", "oracle", "soundness", "verification", "simulation", "demsar"]):
        return "Planning Oracles & Verification"
    return "LLM Planning Foundations"

def convert_pdf_file(pdf_path: Path):
    filename = pdf_path.name
    safe_name = sanitize_filename(pdf_path.stem)
    md_filename = f"{safe_name}.md"
    
    raw_text, page_count = extract_text_pypdf(pdf_path)
    md_body, meta, raw_tok, clean_tok = clean_and_format_markdown(raw_text, filename)
    
    category = categorize_paper(filename, meta["title"], raw_text)
    meta["category"] = category
    meta["page_count"] = str(page_count)
    meta["md_filename"] = md_filename

    # Clean title of forbidden characters
    clean_title = meta['title'].replace('"', "'")
    
    header = (
        f"---\n"
        f"title: \"{clean_title}\"\n"
        f"original_file: \"{filename}\"\n"
        f"pages: {page_count}\n"
        f"category: \"{category}\"\n"
        f"raw_tokens: ~{raw_tok:,}\n"
        f"clean_tokens: ~{clean_tok:,}\n"
        f"---\n\n"
        f"# {clean_title}\n\n"
        f"**Category:** {category} | **Pages:** {page_count} | **Tokens:** ~{clean_tok:,} (reduced from ~{raw_tok:,})\n\n"
        f"### Abstract / Overview\n{meta['abstract']}\n\n"
        f"---\n\n"
    )

    full_md = header + md_body

    for out_d in OUT_DIRS:
        out_p = out_d / md_filename
        out_p.write_text(full_md, encoding="utf-8")
        
    return meta, raw_tok, clean_tok

def main():
    pdf_files = sorted(list(PAPER_DIR.glob("*.pdf")))
    print(f"Scanning {len(pdf_files)} PDFs in {PAPER_DIR}...")
    
    converted = 0
    catalog = []
    
    for idx, pdf in enumerate(pdf_files, 1):
        safe_name = sanitize_filename(pdf.stem)
        target1 = OUT_DIRS[0] / f"{safe_name}.md"
        target2 = OUT_DIRS[1] / f"{safe_name}.md"
        
        needs_convert = not (target1.exists() and target2.exists())
        if needs_convert:
            print(f"Converting [{idx}/{len(pdf_files)}]: {pdf.name}...")
            try:
                meta, raw_t, clean_t = convert_pdf_file(pdf)
                converted += 1
                catalog.append(meta)
                print(f"  -> SUCCESS: Saved {safe_name}.md to both directories.")
            except Exception as e:
                print(f"  -> ERROR on {pdf.name}: {e}")
        else:
            # Already exists in both, parse meta if needed
            pass
            
    print(f"\nDone! Converted {converted} new/missing papers.")

if __name__ == "__main__":
    main()
