import os

content_dir = "scientific-thesis-template/content"
magic_comment = "% !TeX root = ../thesismain.tex\n"

for fname in os.listdir(content_dir):
    if fname.endswith(".tex"):
        fpath = os.path.join(content_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Check if already present
        if lines and "% !TeX root" in lines[0]:
            continue
        
        # Prepend magic comment
        new_content = magic_comment + "".join(lines)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Added TeX root magic comment to {fpath}")

print("All chapter subfiles configured with magic root directive!")
