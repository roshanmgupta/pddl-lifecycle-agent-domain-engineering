import sys
from pathlib import Path

sys.path.insert(0, 'scripts')
import convert_papers_to_markdown as cpm

files = [
    'demsar06a.pdf',
    'Engineering AI Planning Systems.pdf',
    'From Formalisers to EngineersAn Agentic Position to HTN Domain Model Generation.pdf',
    'PDDL_-_The_Planning_Domain_Definition_Language.pdf',
    'Planetarium A Rigorous Benchmark for Translating Text to Structured Planning Languages.pdf',
    'Position_LLMs_Can_t_Plan_But_Can_Help_Planning_in_LLM_Modulo_Frameworks.pdf'
]

for f in files:
    pdf_p = Path('paper') / f
    print(f'Testing {f}...')
    try:
        raw_text, pages = cpm.extract_paper_content(pdf_p)
        print(f'  Extracted {len(raw_text)} chars across {pages} pages.')
        md_body, meta, raw_tok, clean_tok = cpm.clean_and_format_markdown(raw_text, f)
        print(f'  Formatted: {meta["title"]} ({clean_tok} clean tokens)')
    except Exception as e:
        print(f'  ERROR on {f}: {e}')
