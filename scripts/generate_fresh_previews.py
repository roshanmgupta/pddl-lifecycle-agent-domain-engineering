import os
import re
from pathlib import Path

base_dir = Path("scientific-thesis-template-fresh")
chapters_dir = base_dir / "chapters-en"
previews_dir = base_dir / "previews"
previews_dir.mkdir(parents=True, exist_ok=True)

def tex_to_markdown(tex_text: str) -> str:
    lines = []
    for line in tex_text.splitlines():
        if line.strip().startswith("%"):
            continue
        line = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(line)
    text = "\n".join(lines)

    text = re.sub(r"\\chapter\{([^}]+)\}(?:\\label\{[^}]+\})?", r"# \1\n", text)
    text = re.sub(r"\\section\{([^}]+)\}(?:\\label\{[^}]+\})?", r"## \1\n", text)
    text = re.sub(r"\\subsection\{([^}]+)\}(?:\\label\{[^}]+\})?", r"### \1\n", text)
    text = re.sub(r"\\subsubsection\{([^}]+)\}(?:\\label\{[^}]+\})?", r"#### \1\n", text)
    text = re.sub(r"\\paragraph\{([^}]+)\}", r"**\1**\n", text)

    text = re.sub(r"\\label\{[^}]+\}", "", text)
    text = re.sub(r"\\cite\{([^}]+)\}", r"[\1]", text)
    text = re.sub(r"\\gls\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\glspl\{([^}]+)\}", r"\1s", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", text)
    text = re.sub(r"\\texttt\{([^}]+)\}", r"`\1`", text)

    text = re.sub(r"\\begin\{equation\}(.*?)\\end\{equation\}", r"\n```\n\1\n```\n", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{align\}(.*?)\\end\{align\}", r"\n```\n\1\n```\n", text, flags=re.DOTALL)

    text = re.sub(r"\\begin\{itemize\}", "", text)
    text = re.sub(r"\\end\{itemize\}", "", text)
    text = re.sub(r"\\begin\{enumerate\}(?:\[.*?\])?", "", text)
    text = re.sub(r"\\end\{enumerate\}", "", text)
    text = re.sub(r"\\begin\{description\}(?:\[.*?\])?", "", text)
    text = re.sub(r"\\end\{description\}", "", text)
    text = re.sub(r"\\item\[\s*\\textbf\{([^}]+)\}\s*\]", r"- **\1**", text)
    text = re.sub(r"\\item", r"- ", text)

    text = re.sub(r"\\begin\{quote\}(.*?)\\end\{quote\}", r"\n> \1\n", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

for tex_file in chapters_dir.glob("*.tex"):
    out_name = tex_file.stem.replace(" ", "_") + ".md"
    tex_str = tex_file.read_text(encoding="utf-8")
    md_str = tex_to_markdown(tex_str)
    header = f"> **Formatted Preview of [`chapters-en/{tex_file.name}`](file:///{tex_file.resolve()})**\n\n---\n\n"
    (previews_dir / out_name).write_text(header + md_str + "\n", encoding="utf-8")
    print(f"Generated preview: {out_name}")

print("Previews ready in scientific-thesis-template-fresh/previews/")
