import re
from pathlib import Path

PAPER_DIR = Path("paper")
MD_DIR = PAPER_DIR / "markdown"
INDEX_FILE = PAPER_DIR / "LITERATURE_INDEX.md"

md_files = sorted(list(MD_DIR.glob("*.md")))

catalog = []
total_clean_tokens = 0

for md_path in md_files:
    content = md_path.read_text(encoding="utf-8")
    
    # extract title from frontmatter or first heading
    title_m = re.search(r'title:\s*"(.*?)"', content)
    cat_m = re.search(r'category:\s*"(.*?)"', content)
    pages_m = re.search(r'pages:\s*(\d+)', content)
    clean_tok_m = re.search(r'clean_tokens:\s*~?([0-9,]+)', content)
    
    title = title_m.group(1) if title_m else md_path.stem.replace('_', ' ')
    category = cat_m.group(1) if cat_m else "LLM Planning Foundations"
    pages = pages_m.group(1) if pages_m else "N/A"
    
    clean_tokens = len(content) // 4
    total_clean_tokens += clean_tokens
    
    catalog.append({
        "title": title,
        "category": category,
        "pages": pages,
        "clean_tokens": clean_tokens,
        "filename": md_path.name
    })

# sort catalog by category then title
catalog.sort(key=lambda x: (x["category"], x["title"]))

index_md = [
    "# Master Research Literature Index (IAAS PDDL Lifecycle)",
    f"**Total Cataloged Papers:** {len(catalog)} | **Total Clean Markdown Tokens:** ~{total_clean_tokens:,} tokens\n",
    "> [!TIP]",
    "> **Side-by-Side Research Rule:** Never load raw PDFs into conversational context.",
    "> All papers in `paper/` have been converted into clean Markdown in `paper/markdown/` and `scientific-thesis-template-fresh/literature/papers_markdown/` for immediate side-by-side verification with thesis chapters.\n",
    "## Master Paper Catalog\n",
    "| # | Paper Title / Key | Category | Pages | Clean Tokens | Markdown File Link |",
    "| :-: | :--- | :--- | :-: | :-: | :--- |"
]

for idx, item in enumerate(catalog, 1):
    title_trunc = item["title"][:58] + "..." if len(item["title"]) > 58 else item["title"]
    clean_tok_str = f"~{item['clean_tokens']:,}"
    link = f"[{item['filename']}](file:///e:/Rosh/Thesis/pddl_lifecycle_agent/paper/markdown/{item['filename']})"
    index_md.append(f"| {idx:02d} | **{title_trunc}** | {item['category']} | {item['pages']} | {clean_tok_str} | {link} |")

INDEX_FILE.write_text("\n".join(index_md), encoding="utf-8")
print(f"Updated {INDEX_FILE} with {len(catalog)} papers!")
