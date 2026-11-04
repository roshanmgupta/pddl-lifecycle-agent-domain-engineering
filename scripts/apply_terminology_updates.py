import os
import re

chapters_dir = r"scientific-thesis-template-fresh/chapters-en"

# Pairs of (file_path, replacements)
# Each replacement is (target_regex, replacement_str)

tex_files = [
    "10 - introduction.tex",
    "20 - background.tex",
    "30 - problem exposition.tex",
    "40 - first real chapter.tex",
    "50 - second real chapter.tex",
    "60 - evaluation.tex",
    "90 - conclusion.tex"
]

md_files = [
    "10 - introduction.md",
    "20 - background.md",
    "30 - problem exposition.md",
    "40 - first real chapter.md",
    "50 - second real chapter.md",
    "60 - evaluation.md",
    "90 - conclusion.md"
]

all_files = tex_files + md_files

for fname in all_files:
    fpath = os.path.join(chapters_dir, fname)
    if not os.path.exists(fpath):
        continue
    content = open(fpath, encoding="utf-8").read()
    orig = content
    
    # Specific contextual replacements first
    # 1. Combining / Integrating
    content = re.sub(r"\bsynthesizing action model acquisition principles\b", "integrating action model acquisition principles", content, flags=re.IGNORECASE)
    content = re.sub(r"\bresearch gaps are synthesized into a comparative taxonomy\b", "research gaps are consolidated into a comparative taxonomy", content, flags=re.IGNORECASE)
    content = re.sub(r"\\section\{Synthesis and Positioning of this Thesis\}", r"\\section{Comparative Assessment and Positioning of this Thesis}", content)
    content = re.sub(r"# Synthesis and Positioning of this Thesis", "# Comparative Assessment and Positioning of this Thesis", content)
    content = re.sub(r"\bcomparative synthesis of the key frameworks\b", "comparative assessment of the key frameworks", content, flags=re.IGNORECASE)
    content = re.sub(r"\bcompiler synthesis\b", "compiler construction", content, flags=re.IGNORECASE)
    
    # 2. General synthesis -> generation replacements
    content = re.sub(r"\bSynthesis Modality\b", "Generation Modality", content)
    content = re.sub(r"\bSynthesis\b", "Generation", content)
    content = re.sub(r"\bsynthesis\b", "generation", content)
    content = re.sub(r"\bSynthesizes\b", "Generates", content)
    content = re.sub(r"\bsynthesizes\b", "generates", content)
    content = re.sub(r"\bSynthesizing\b", "Generating", content)
    content = re.sub(r"\bsynthesizing\b", "generating", content)
    content = re.sub(r"\bSynthesized\b", "Generated", content)
    content = re.sub(r"\bsynthesized\b", "generated", content)
    content = re.sub(r"\bSynthesize\b", "Generate", content)
    content = re.sub(r"\bsynthesize\b", "generate", content)
    
    # 3. Synonym cleanup: colloquial fixes -> repairs
    content = re.sub(r"\bwhile attempting to fix defective ones\b", "while attempting to repair defective ones", content)
    content = re.sub(r"\bidentify syntactic fixes\b", "identify syntactic repairs", content)
    content = re.sub(r"\btoward human-interpretable fixes\b", "toward human-interpretable repairs", content)
    content = re.sub(r"\bhallucinate unrelated fixes\b", "hallucinate unrelated repairs", content)
    
    # 4. Synonym cleanup: retry -> re-prompting
    content = re.sub(r"\bunstructured iterative retry\b", "unstructured iterative re-prompting", content)
    
    # 5. Synonym cleanup: two-way -> bidirectional
    content = re.sub(r"\btwo-way semantic task success\b", "bidirectional semantic task success", content)
    
    # 6. Double question mark typo fix if present
    content = re.sub(r"error dumps\?\?\}\{rq2-triage\}", "error dumps?}{rq2-triage}", content)
    
    # 7. SVR expansion stutter fix
    content = re.sub(r"Syntactic Validity Rate \(\\gls\{svr\}\)", r"\\gls{svr}", content)
    
    if content != orig:
        diff_count = len(re.findall(r"\bgenerat\w*", content, re.IGNORECASE)) - len(re.findall(r"\bgenerat\w*", orig, re.IGNORECASE))
        print(f"File {fname}: Modified (net +{diff_count} generation instances)")
        open(fpath, "w", encoding="utf-8").write(content)
    else:
        print(f"File {fname}: No changes")

print("Replacement complete.")
