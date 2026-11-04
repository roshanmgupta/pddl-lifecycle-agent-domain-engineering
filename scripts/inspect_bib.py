import re

with open("scientific-thesis-template/bibliography.bib", "r", encoding="utf-8") as f:
    text = f.read()

keys = re.findall(r"@\w+\{([^,]+),", text)
print("Total keys in bibliography.bib:", len(keys))
for k in keys:
    print(k)
