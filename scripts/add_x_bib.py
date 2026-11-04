with open("scientific-thesis-template/bibliography.bib", "r", encoding="utf-8") as f:
    text = f.read()

if "@misc{x," not in text:
    x_entry = """
@misc{x,
  author       = {{Author / AI Synthesis}},
  title        = {Unpublished Architectural Claim or Thesis Specific Formulation},
  year         = {2026},
  note         = {[x] Design claim or AI generated statement pending external citation}
}
"""
    text += "\n" + x_entry.strip() + "\n"
    with open("scientific-thesis-template/bibliography.bib", "w", encoding="utf-8") as f:
        f.write(text)
    print("Added @misc{x} to bibliography.bib successfully.")
else:
    print("@misc{x} already exists in bibliography.bib.")
