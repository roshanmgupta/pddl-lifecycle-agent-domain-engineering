with open("scientific-thesis-template/literature/papers_markdown/Srushti_Shetye_Thesis_Final.md", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("## Bibliography")
if idx == -1:
    idx = text.find("# Bibliography")
if idx == -1:
    idx = text.find("References")

if idx != -1:
    print("Found references at:", idx)
    print(text[idx:idx+3000])
else:
    print("No bibliography section heading found.")
