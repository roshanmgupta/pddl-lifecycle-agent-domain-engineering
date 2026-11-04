import pypdf

reader = pypdf.PdfReader("paper/Srushti_Shetye_Thesis_Final.pdf")
print("Total pages in Srushti thesis:", len(reader.pages))

bib_pages = []
for idx in range(len(reader.pages)-1, max(len(reader.pages)-25, 0), -1):
    text = reader.pages[idx].extract_text()
    if "Bibliography" in text or "References" in text:
        bib_pages.append(idx)

print("Bibliography on pages:", [p+1 for p in bib_pages])
for p in reversed(bib_pages[:3]):
    print(f"--- Page {p+1} ---")
    print(reader.pages[p].extract_text()[:1200])
