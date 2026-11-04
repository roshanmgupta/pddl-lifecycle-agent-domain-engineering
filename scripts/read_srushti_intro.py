with open("scientific-thesis-template/literature/papers_markdown/Srushti_Shetye_Thesis_Final.md", "r", encoding="utf-8") as f:
    text = f.read()

# Let's find "1 Introduction"
start_idx = text.find("## 1 Introduction")
if start_idx != -1:
    print("--- FIRST 4000 CHARS OF SRUSHTI INTRODUCTION ---")
    print(text[start_idx:start_idx+4000])

# Also let's check Chapter 2 Background
bg_idx = text.find("## 2 Background")
if bg_idx != -1:
    print("\n--- FIRST 4000 CHARS OF SRUSHTI BACKGROUND ---")
    print(text[bg_idx:bg_idx+4000])
