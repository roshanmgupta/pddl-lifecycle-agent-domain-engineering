import os, glob, re

md_dir = 'scientific-thesis-template-fresh/literature/papers_markdown'
files = glob.glob(os.path.join(md_dir, '*.md'))

patterns = [
    r'automated planning is',
    r'ai planning is',
    r'classical planning is',
    r'planning is a discipline in',
    r'generating sequences of actions',
    r'state transition system',
    r'planning domain definition language'
]

results = []

for f in files:
    fname = os.path.basename(f)
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            content = fp.read()
            lines = content.splitlines()

        for idx, line in enumerate(lines):
            for pat in patterns:
                if re.search(pat, line, re.IGNORECASE):
                    # find section header
                    sec = "Unknown Section"
                    for prev_idx in range(idx, -1, -1):
                        if lines[prev_idx].strip().startswith('#'):
                            sec = lines[prev_idx].strip()
                            break
                    
                    # grab surrounding lines
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 5)
                    para = "\n".join(lines[start:end])
                    results.append({
                        "file": fname,
                        "line": idx + 1,
                        "section": sec,
                        "matched_line": line.strip(),
                        "para": para
                    })
                    break
    except Exception as e:
        pass

# Write results out cleanly to a file for examination
out_path = 'scripts/extracted_definitions.txt'
with open(out_path, 'w', encoding='utf-8') as out:
    out.write(f"Total occurrences: {len(results)}\n\n")
    for idx, r in enumerate(results):
        out.write(f"--- MATCH {idx+1} ---\n")
        out.write(f"File: {r['file']}\n")
        out.write(f"Section: {r['section']}\n")
        out.write(f"Line Number: {r['line']}\n")
        out.write(f"Matched Line: {r['matched_line']}\n")
        out.write(f"Paragraph:\n{r['para']}\n\n")

print(f"Extraction complete. Found {len(results)} matches. Written to {out_path}.")
