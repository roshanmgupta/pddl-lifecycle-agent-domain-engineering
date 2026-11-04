#!/usr/bin/env python3
"""
Zero-Token Paper Query Utility.
Allows Antigravity and the user to search, summarize, and extract targeted sections
from the 57 research papers without ever reading whole documents into the context window.
"""

import argparse
import re
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles to prevent charmap errors on mathematical/Greek symbols
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = PROJECT_ROOT / "paper" / "markdown"

def find_matching_papers(paper_query: str) -> list[Path]:
    query_norm = paper_query.lower().replace("-", "_").replace(" ", "_")
    matches = []
    for f in MARKDOWN_DIR.glob("*.md"):
        f_norm = f.name.lower().replace("-", "_")
        if query_norm in f_norm:
            matches.append(f)
    if not matches:
        # Fallback: search inside file headers
        for f in MARKDOWN_DIR.glob("*.md"):
            try:
                head = f.read_text(encoding="utf-8")[:1000].lower()
                if paper_query.lower() in head:
                    matches.append(f)
            except Exception:
                pass
    return matches

def search_keyword_across_all(keyword: str, max_results: int = 8):
    print(f"\nSearching for '{keyword}' across all papers in {MARKDOWN_DIR.name}/...\n")
    results = []
    kw_re = re.compile(rf"([^.\n]*?{re.escape(keyword)}[^.\n]*)", re.IGNORECASE)
    
    for f in sorted(MARKDOWN_DIR.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            matches = kw_re.findall(text)
            if matches:
                # Get clean sample snippet
                snippet = matches[0].strip()
                if len(snippet) > 160:
                    snippet = snippet[:160] + "..."
                results.append((f.name, len(matches), snippet))
        except Exception:
            pass
            
    # Sort by frequency
    results.sort(key=lambda x: x[1], reverse=True)
    
    if not results:
        print(f"No matches found for '{keyword}'.")
        return
        
    print(f"Found {len(results)} papers mentioning '{keyword}' (showing top {min(len(results), max_results)}):\n")
    for fname, count, snippet in results[:max_results]:
        print(f"  * {fname} ({count} hits):")
        print(f"    \"{snippet}\"\n")

def extract_section(paper_query: str, section_kw: str, max_lines: int = 35):
    matches = find_matching_papers(paper_query)
    if not matches:
        print(f"No paper found matching '{paper_query}'.")
        return
        
    target_file = matches[0]
    print(f"\nExtracting section '{section_kw}' from {target_file.name}...\n")
    
    text = target_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    
    found_idx = -1
    for i, line in enumerate(lines):
        if re.search(rf"\b{re.escape(section_kw)}\b", line, re.IGNORECASE):
            found_idx = i
            break
            
    if found_idx == -1:
        print(f"Keyword '{section_kw}' not found in {target_file.name}.")
        return
        
    start_line = max(0, found_idx - 3)
    end_line = min(len(lines), found_idx + max_lines)
    
    snippet = "\n".join(lines[start_line:end_line])
    print(f"--- Snippet from {target_file.name} (Lines {start_line}-{end_line}) ---")
    print(snippet)
    print(f"--- End of Snippet (~{len(snippet)//4} tokens consumed) ---\n")

def display_paper_card(paper_query: str):
    matches = find_matching_papers(paper_query)
    if not matches:
        print(f"No paper found matching '{paper_query}'.")
        return
        
    target_file = matches[0]
    text = target_file.read_text(encoding="utf-8")
    
    # Read first 30 lines (header and abstract)
    lines = text.splitlines()
    header_lines = []
    for l in lines[:40]:
        if l.strip() == "---" and len(header_lines) > 5:
            header_lines.append(l)
            break
        header_lines.append(l)
        
    print(f"\n=======================================================")
    print(f" Paper Card: {target_file.name}")
    print(f"=======================================================")
    print("\n".join(header_lines))
    print(f"=======================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Zero-Token Paper Query Utility")
    parser.add_argument("--search", type=str, help="Search for a keyword across all cataloged papers")
    parser.add_argument("--paper", type=str, help="Paper name or keyword to query")
    parser.add_argument("--section", type=str, help="Section or topic to extract from specified paper")
    parser.add_argument("--card", type=str, help="Show 1-paragraph summary card of a paper")
    
    args = parser.parse_args()
    
    if args.search:
        search_keyword_across_all(args.search)
    elif args.card:
        display_paper_card(args.card)
    elif args.paper and args.section:
        extract_section(args.paper, args.section)
    elif args.paper:
        display_paper_card(args.paper)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
