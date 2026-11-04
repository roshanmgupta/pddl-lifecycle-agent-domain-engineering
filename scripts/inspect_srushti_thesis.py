import re

with open("scientific-thesis-template/literature/papers_markdown/Srushti_Shetye_Thesis_Final.md", "r", encoding="utf-8") as f:
    text = f.read()

print("Length:", len(text))
headings = [line for line in text.splitlines() if line.startswith("#")]
print("\n--- Headings in Srushti Thesis ---")
for h in headings[:50]:
    print(h)
