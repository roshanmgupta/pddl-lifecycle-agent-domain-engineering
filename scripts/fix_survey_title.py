import re
from pathlib import Path

for base in ['scientific-thesis-template-fresh/literature/papers_markdown', 'paper/markdown']:
    fp = Path(base) / 'Llms_as_planning_formalizers_A_survey_for_leveraging_LLM_to_construct_automated_planning_models.md'
    if fp.exists():
        content = fp.read_text(encoding='utf-8')
        content = re.sub(
            r'title:\s*".*?Association for Computational Linguistics.*?"',
            'title: "LLMs as Planning Formalizers: A Survey for Leveraging LLM to Construct Automated Planning Models"',
            content
        )
        content = re.sub(
            r'#\s*July 27 - August 1, 2025.*?Linguistics',
            '# LLMs as Planning Formalizers: A Survey for Leveraging LLM to Construct Automated Planning Models\n\n**Authors:** Anusorn Tantakoun, Zhendong Zhu, Christian Muise (Queen\'s University, Canada - ACL 2025)',
            content
        )
        fp.write_text(content, encoding='utf-8')
        print(f"Cleaned title in {fp}")
