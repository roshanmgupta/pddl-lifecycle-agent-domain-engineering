from pypdf import PdfReader
import os, re
from pathlib import Path

def convert_pdf(pdf_path):
    print(f"Reading {pdf_path}...")
    reader = PdfReader(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    pages_text = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
    
    full_text = "\n\n".join(pages_text)
    
    # clean lines
    lines = [line.rstrip() for line in full_text.splitlines()]
    body = "\n".join(lines)
    
    md_content = f"""---
title: "{base_name}"
original_file: "{os.path.basename(pdf_path)}"
pages: {len(reader.pages)}
---

# {base_name}

{body}
"""
    clean_fn = re.sub(r'[^\w\s\-.]', '', base_name)
    clean_fn = re.sub(r'\s+', '_', clean_fn).strip('_') + '.md'
    
    out_dirs = [
        Path("paper/markdown"),
        Path("scientific-thesis-template-fresh/literature/papers_markdown")
    ]
    
    for od in out_dirs:
        od.mkdir(parents=True, exist_ok=True)
        out_p = od / clean_fn
        out_p.write_text(md_content, encoding='utf-8')
        print(f"Saved: {out_p} ({len(reader.pages)} pages, {len(md_content)} chars)")
    
    return clean_fn

new_pdfs = [
    "paper/Leveraging Pre-trained Large Language Models to Construct and Utilize World Models for Model-based Planning.pdf",
    "paper/There and Back Again Extracting Formal Domains for Controllable Neurosymbolic Story Authoring.pdf"
]

for p in new_pdfs:
    if os.path.exists(p):
        convert_pdf(p)
    else:
        print(f"Not found: {p}")
