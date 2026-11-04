with open("scientific-thesis-template/literature/papers_markdown/Srushti_Shetye_Thesis_Final.md", "r", encoding="utf-8") as f:
    text = f.read()

import re
matches = list(re.finditer(r"## 1\.[1-5] [^\n]+", text))
for i, m in enumerate(matches):
    print(f"\n=================== {m.group(0)} ===================")
    start = m.start()
    end = matches[i+1].start() if i+1 < len(matches) else start + 3000
    print(text[start:min(start+2500, end)])
