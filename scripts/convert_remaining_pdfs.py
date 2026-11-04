from pypdf import PdfReader
import os, re
from pathlib import Path

def convert_pdf_to_md(pdf_path, out_dir):
    reader = PdfReader(pdf_path)
    title = os.path.splitext(os.path.basename(pdf_path))[0]
    pages_text = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
    
    full_text = '\n\n'.join(pages_text)
    
    lines = full_text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned_lines.append(line.rstrip())
    
    body = "\n".join(cleaned_lines)
    md_content = f"""---
title: "{title}"
original_file: "{os.path.basename(pdf_path)}"
pages: {len(reader.pages)}
---

# {title}

{body}
"""
    out_name = re.sub(r'[^\w\s\-.]', '', title)
    out_name = re.sub(r'\s+', '_', out_name).strip('_') + '.md'
    out_path = Path(out_dir) / out_name
    out_path.write_text(md_content, encoding='utf-8')
    print(f"Converted {pdf_path} -> {out_path} ({len(reader.pages)} pages, {len(md_content)} chars)")
    return out_path

to_convert = [
    'paper/Finding Semantically Guided Repairs in PDDL Domains Using LLMs.pdf',
    'paper/planning05-causal-graphs-pre-handout (1).pdf',
    'NL2PDDL/appendix.pdf'
]

for p in to_convert:
    if os.path.exists(p):
        convert_pdf_to_md(p, 'paper/markdown')
        convert_pdf_to_md(p, 'scientific-thesis-template-fresh/literature/papers_markdown')
    else:
        print('Not found:', p)
