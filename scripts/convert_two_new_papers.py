import os
import sys
from pypdf import PdfReader

sys.stdout.reconfigure(encoding='utf-8')

pdf_dir = "paper"
target_dirs = [
    "paper/markdown",
    "scientific-thesis-template-fresh/literature/papers_markdown"
]

files_to_convert = [
    ("HEART Coordination of Heterogeneous Expert Agents for Physically Grounded Robotic Task Planning.pdf", "HEART_Coordination_of_Heterogeneous_Expert_Agents.md"),
    ("towards pddl domaining copilot.pdf", "towards_pddl_domain_modelling_copilot.md")
]

for pdf_name, md_name in files_to_convert:
    pdf_path = os.path.join(pdf_dir, pdf_name)
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found")
        continue
    
    print(f"Converting {pdf_name}...")
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    text_content = []
    
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text_content.append(f"\n\n<!-- PAGE {idx+1} -->\n\n" + text)
        
    full_text = "".join(text_content)
    
    for tdir in target_dirs:
        os.makedirs(tdir, exist_ok=True)
        out_path = os.path.join(tdir, md_name)
        with open(out_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(full_text)
        print(f"Saved {out_path} ({total_pages} pages, {len(full_text)} chars)")

print("Conversion complete.")
