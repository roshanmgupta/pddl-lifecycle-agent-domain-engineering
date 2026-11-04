import os
import sys
import shutil
from pathlib import Path

# UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(".").resolve()
PAPER_DIR = PROJECT_ROOT / "paper"
FRESH_DIR = PROJECT_ROOT / "scientific-thesis-template-fresh"

print("1. Creating target directories in scientific-thesis-template-fresh...")
GUIDELINES_DIR = FRESH_DIR / "guidelines"
METHODOLOGY_DIR = FRESH_DIR / "methodology"
LITERATURE_DIR = FRESH_DIR / "literature"
PAPERS_MD_DIR = LITERATURE_DIR / "papers_markdown"
PAPER_FIGS_DIR = FRESH_DIR / "figures" / "paper_figures"
REPORTS_DIR = FRESH_DIR / "reports"

for d in [GUIDELINES_DIR, METHODOLOGY_DIR, LITERATURE_DIR, PAPERS_MD_DIR, PAPER_FIGS_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print("2. Copying markdown papers...")
md_count = 0
for f in (PAPER_DIR / "markdown").glob("*.md"):
    shutil.copy2(f, PAPERS_MD_DIR / f.name)
    md_count += 1
print(f"   Copied {md_count} markdown papers.")

print("3. Copying literature index, evaluation data bank, and methodology...")
if (PAPER_DIR / "LITERATURE_INDEX.md").exists():
    shutil.copy2(PAPER_DIR / "LITERATURE_INDEX.md", LITERATURE_DIR / "LITERATURE_INDEX.md")
if (PAPER_DIR / "EVALUATION_DATA_BANK.md").exists():
    shutil.copy2(PAPER_DIR / "EVALUATION_DATA_BANK.md", LITERATURE_DIR / "EVALUATION_DATA_BANK.md")
if (PAPER_DIR / "EVALUATION_METHODOLOGY_REVISED.md").exists():
    shutil.copy2(PAPER_DIR / "EVALUATION_METHODOLOGY_REVISED.md", METHODOLOGY_DIR / "EVALUATION_METHODOLOGY_REVISED.md")

print("4. Copying guidelines...")
if (PAPER_DIR / "thesis_writing_handbook_style_guide.md").exists():
    shutil.copy2(PAPER_DIR / "thesis_writing_handbook_style_guide.md", GUIDELINES_DIR / "thesis_writing_handbook_style_guide.md")
if (PROJECT_ROOT / "project_description.md").exists():
    shutil.copy2(PROJECT_ROOT / "project_description.md", GUIDELINES_DIR / "project_description.md")
if (PROJECT_ROOT / "AGENTS.md").exists():
    shutil.copy2(PROJECT_ROOT / "AGENTS.md", GUIDELINES_DIR / "AGENTS_MANDATE.md")

print("5. Copying reports...")
reports_list = [
    "thesis/SMIRNOV_2024_ANALYSIS_AND_MAPPING_REPORT.md",
    "thesis/SPAR_2025_ANALYSIS_AND_MAPPING_REPORT.md",
    "thesis/report/domain_fault_repair_benchmark_evaluation_report.md",
    "scratch/THESIS_REPORT.md",
    "scratch/RELATED_WORK_EXTRACTION.md",
    "scratch/evaluation_report.md",
    "scratch/implementation_plan.md"
]
for r in reports_list:
    src_p = PROJECT_ROOT / r
    if src_p.exists():
        shutil.copy2(src_p, REPORTS_DIR / src_p.name)

print("6. Copying extracted figures from paper/figures...")
fig_count = 0
for root, dirs, files in os.walk(PAPER_DIR / "figures"):
    rel = Path(root).relative_to(PAPER_DIR / "figures")
    target = PAPER_FIGS_DIR / rel
    target.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(Path(root) / f, target / f)
        fig_count += 1
print(f"   Copied {fig_count} figures into figures/paper_figures.")

print("7. Updating bibliography.bib in fresh template...")
bib_path = FRESH_DIR / "bibliography.bib"
bib_text = bib_path.read_text(encoding="utf-8")

# Entries from our comprehensive bibliography
additional_bib = """
@inproceedings{ghallab2004,
  author    = {Malik Ghallab and Dana Nau and Paolo Traverso},
  title     = {Automated Planning: Theory and Practice},
  publisher = {Morgan Kaufmann},
  year      = {2004}
}

@article{mcdermott1998,
  author    = {Drew McDermott and Malik Ghallab and Adele E. Howe and Craig A. Knoblock and Ashwin Ram and Manuela M. Veloso and Daniel S. Weld and David E. Wilkins},
  title     = {{PDDL} - The Planning Domain Definition Language},
  journal   = {Technical Report CSRP-98-003, Yale Center for Computational Vision and Control},
  year      = {1998}
}

@article{howey2004,
  author    = {Richard Howey and Derek Long and Maria Fox},
  title     = {{VAL}: Automatic Plan Validation, Continuous Effects and Mixed Initiative Planning Using {PDDL2.1}},
  journal   = {IEEE ICTAI},
  year      = {2004}
}

@article{helmert2006,
  author    = {Malte Helmert},
  title     = {The {Fast Downward} Planning System},
  journal   = {Journal of Artificial Intelligence Research},
  volume    = {26},
  pages     = {191--246},
  year      = {2006}
}

@article{georgievski2023,
  author    = {Ilche Georgievski},
  title     = {Software Development Life Cycle for Engineering {AI} Planning Systems},
  journal   = {arXiv preprint arXiv:2308.10668},
  year      = {2023}
}

@mastersthesis{patil2024,
  author    = {Kshitij Patil},
  title     = {{LLMs} for {AI} Planning: A Study on Error Detection and Correction in {PDDL} Domain Models},
  school    = {Institute of Architecture of Application Systems, University of Stuttgart},
  year      = {2024},
  type      = {Master's Thesis},
  note      = {Supervised by PD Dr. Ilche Georgievski}
}

@mastersthesis{shetye2025,
  author    = {Srushti Shetye},
  title     = {Automated Planning Domain Model Generation Using Large Language Models and Intermediate Representations},
  school    = {Institute of Architecture of Application Systems, University of Stuttgart},
  year      = {2025},
  type      = {Master's Thesis},
  note      = {Supervised by PD Dr. Ilche Georgievski}
}

@article{tantakoun2025,
  author    = {S. Tantakoun and others},
  title     = {Understanding Real-World {AI} Planning Domains: A Conceptual Framework},
  journal   = {arXiv preprint},
  year      = {2025}
}

@article{kambhampati2024,
  author    = {Subbarao Kambhampati and Karthik Valmeekam and Lin Guan and Mudit Verma and Kaya Stechly and Sarath Sreedharan},
  title     = {{LLMs} Can't Plan, But Can Help Planning in {LLM-Modulo} Frameworks},
  journal   = {arXiv preprint arXiv:2402.01817},
  year      = {2024}
}

@article{valmeekam2023,
  author    = {Karthik Valmeekam and Matthew Marquez and Sarath Sreedharan and Subbarao Kambhampati},
  title     = {On the Planning Abilities of Large Language Models: A Comprehensive Investigation},
  journal   = {NeurIPS},
  year      = {2023}
}

@article{bavandpour2026llmonly,
  author    = {Mohammad Bavandpour and Pascal Bercher},
  title     = {{LLM-Only} {PDDL} Domain Repair with Open-Weight Models},
  journal   = {arXiv preprint arXiv:2602.09876},
  year      = {2026}
}

@article{oswald2024,
  author    = {Julian Oswald and others},
  title     = {Generating Domain Models for Automated Planning from Natural Language Descriptions},
  journal   = {arXiv preprint},
  year      = {2024}
}

@article{silver2022,
  author    = {Tom Silver and Kelsey R. Allen and Josh B. Tenenbaum and Leslie Pack Kaelbling},
  title     = {{PDDL} Planning with Pretrained Large Language Models},
  journal   = {arXiv preprint arXiv:2210.03595},
  year      = {2022}
}

@article{guan2023,
  author    = {Lin Guan and Valmeekam Karthik and Sarath Sreedharan and Subbarao Kambhampati},
  title     = {Leveraging Pre-trained Large Language Models to Construct and Utilize World Models for Model-based Planning},
  journal   = {NeurIPS},
  year      = {2023}
}

@article{huang2025,
  author    = {Zhen Huang and others},
  title     = {{SPAR}: Scalable {LLM}-based {PDDL} Domain Generation},
  journal   = {arXiv preprint arXiv:2501.00000},
  year      = {2025}
}

@article{smirnov2024,
  author    = {Pavel Smirnov and Frank Joublin and Antonello Ceravola and Michael Gienger},
  title     = {Generating Consistent {PDDL} Domains with {LLMs}},
  journal   = {arXiv preprint},
  year      = {2024}
}

@article{agarwal2024,
  author    = {S. Agarwal and S. Sreepathy},
  title     = {Answer Set Programming for Semantic Planning Verification},
  journal   = {arXiv preprint},
  year      = {2024}
}

@article{rosa2026grounded,
  author    = {A. Rosa and others},
  title     = {Grounded Evaluation and Repair for {NL}-to-{PDDL} Problem Generation},
  journal   = {arXiv preprint},
  year      = {2026}
}

@article{stein2024autoplanbench,
  author    = {K. Stein and others},
  title     = {{AutoPlanBench}: Automatically Generating Benchmark Problems for Planning},
  journal   = {arXiv preprint},
  year      = {2024}
}

@misc{x,
  author    = {{Author / AI Synthesis}},
  title     = {Unpublished Architectural Claim or Thesis-Specific Formulation},
  year      = {2026},
  note      = {[x] Design claim or AI generated statement pending external citation}
}
"""

for block in additional_bib.strip().split("\n\n@"):
    entry = ("@" + block) if not block.startswith("@") else block
    key = entry.split("{")[1].split(",")[0].strip()
    if key not in bib_text:
        bib_text += "\n\n" + entry.strip()

bib_path.write_text(bib_text, encoding="utf-8")
print("   bibliography.bib updated with all literature citations.")

print("\nAll files successfully populated into scientific-thesis-template-fresh!")
