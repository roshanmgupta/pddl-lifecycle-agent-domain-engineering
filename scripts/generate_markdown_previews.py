import os
import re

content_dir = "scientific-thesis-template/content"
preview_dir = "scientific-thesis-template/previews"
os.makedirs(preview_dir, exist_ok=True)

def tex_to_markdown(tex_text: str) -> str:
    # 1. Strip comments
    lines = []
    for line in tex_text.splitlines():
        if line.strip().startswith("%"):
            continue
        # Strip trailing unescaped comments
        line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(line)
    text = "\n".join(lines)

    # 2. Chapters, Sections, Subsections
    text = re.sub(r"\\chapter\{([^}]+)\}", r"# \1\n", text)
    text = re.sub(r"\\section\{([^}]+)\}", r"## \1\n", text)
    text = re.sub(r"\\subsection\{([^}]+)\}", r"### \1\n", text)
    text = re.sub(r"\\subsubsection\{([^}]+)\}", r"#### \1\n", text)
    text = re.sub(r"\\paragraph\{([^}]+)\}", r"**\1**\n", text)

    # 3. Labels and citations
    text = re.sub(r"\\label\{[^}]+\}", "", text)
    text = re.sub(r"\\cite\{([^}]+)\}", r"[\1]", text)
    text = re.sub(r"\\gls\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\glspl\{([^}]+)\}", r"\1s", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", text)
    text = re.sub(r"\\texttt\{([^}]+)\}", r"`\1`", text)

    # 4. Math environments
    text = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", r"\n```\n\1\n```\n", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{align\}(.*?)\\end\{align\}", r"\n```\n\1\n```\n", text, flags=re.DOTALL)

    # 5. Lists
    text = re.sub(r"\\begin\{itemize\}", "", text)
    text = re.sub(r"\\end\{itemize\}", "", text)
    text = re.sub(r"\\begin\{enumerate\}(?:\[.*?\])?", "", text)
    text = re.sub(r"\\end\{enumerate\}", "", text)
    text = re.sub(r"\\begin\{description\}(?:\[.*?\])?", "", text)
    text = re.sub(r"\\end\{description\}", "", text)
    text = re.sub(r"\\item\[\s*\\textbf\{([^}]+)\}\s*\]", r"- **\1**", text)
    text = re.sub(r"\\item", r"- ", text)

    # 6. Quotes
    text = re.sub(r"\\begin\{quote\}(.*?)\\end\{quote\}", r"\n> \1\n", text, flags=re.DOTALL)

    # 7. Clean up extra spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

for fname in os.listdir(content_dir):
    if fname.endswith(".tex"):
        base_name = os.path.splitext(fname)[0]
        src_path = os.path.join(content_dir, fname)
        dst_path = os.path.join(preview_dir, f"{base_name}.md")
        with open(src_path, "r", encoding="utf-8") as f:
            tex_content = f.read()
        md_content = tex_to_markdown(tex_content)
        header = f"> **Live Formatted Preview of [`content/{fname}`](file:///{os.path.abspath(src_path)})**\n\n---\n\n"
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(header + md_content + "\n")
        print(f"Generated preview: {dst_path}")

print("All chapter previews generated successfully.")
