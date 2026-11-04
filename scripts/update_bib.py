with open("scientific-thesis-template/bibliography.bib", "r", encoding="utf-8") as f:
    bib_text = f.read()

entries_to_add = """
@mastersthesis{patil2024,
  author       = {Kshitij Patil},
  title        = {LLMs for AI Planning: A Study on Error Detection and Correction in PDDL Domain Models},
  school       = {Institute of Architecture of Application Systems, University of Stuttgart},
  year         = {2024},
  type         = {Master's Thesis},
  note         = {Supervised by PD Dr. Ilche Georgievski}
}

@mastersthesis{shetye2025,
  author       = {Srushti Shetye},
  title        = {Automated Planning Domain Model Generation Using Large Language Models and Intermediate Representations},
  school       = {Institute of Architecture of Application Systems, University of Stuttgart},
  year         = {2025},
  type         = {Master's Thesis},
  note         = {Supervised by PD Dr. Ilche Georgievski}
}

@article{silver2022,
  author       = {Tom Silver and Kelsey R. Allen and Josh B. Tenenbaum and Leslie Pack Kaelbling},
  title        = {PDDL Planning with Pretrained Large Language Models},
  journal      = {arXiv preprint arXiv:2210.03595},
  year         = {2022}
}
"""

for key in ["patil2024", "shetye2025", "silver2022"]:
    if key not in bib_text:
        bib_text += "\n" + entries_to_add.strip() + "\n"
        print(f"Added {key} to bibliography.bib")
        break

with open("scientific-thesis-template/bibliography.bib", "w", encoding="utf-8") as f:
    f.write(bib_text)
print("Updated bibliography.bib successfully.")
