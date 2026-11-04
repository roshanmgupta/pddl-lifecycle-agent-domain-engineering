import os
import sys
from pypdf import PdfReader

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = "paper/15_TIC_Translate-Infer-Compile for accurate -text to plan- using LLMs and Logical Representations.pdf"
target_dirs = [
    "paper/markdown",
    "scientific-thesis-template-fresh/literature/papers_markdown"
]

if not os.path.exists(pdf_path):
    print(f"Error: {pdf_path} not found")
    sys.exit(1)

print(f"Converting {pdf_path}...")
reader = PdfReader(pdf_path)
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

text_content = []
for idx, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    text_content.append(f"\n\n<!-- PAGE {idx+1} -->\n\n" + text)

full_text = "".join(text_content)

out_filename = "TIC_Translate_Infer_Compile.md"

for tdir in target_dirs:
    os.makedirs(tdir, exist_ok=True)
    out_path = os.path.join(tdir, out_filename)
    with open(out_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(full_text)
    print(f"Saved {out_path} ({len(full_text)} chars)")

print("Conversion complete.")
