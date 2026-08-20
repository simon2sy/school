# Rebrand helper: Galaxy English School (replaces stale "Galaxy English School" references).
# Ordered so the most specific strings win before the generic catch-all.
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REPLACEMENTS = [
    ("Galaxy English School, Bhadrapur-9, Jhapa 57204, Nepal",
     "Galaxy English School, Bhadrapur-9, Jhapa 57204, Nepal"),
    ("Bhadrapur-9, Jhapa 57204, Nepal",
     "Bhadrapur-9, Jhapa 57204, Nepal"),
    ("info@galaxyenglishschool.edu.np",
     "info@galaxyenglishschool.edu.np"),
    ("https://www.galaxyenglishschool.edu.np",
     "https://www.galaxyenglishschool.edu.np"),
    ("Galaxy English School",
     "Galaxy English School"),
    ("Welcome to Galaxy English School Admin Panel",
     "Welcome to Galaxy English School Admin Panel"),
    ("Galaxy English School Administration",
     "Galaxy English School Administration"),
    ("Galaxy English School Admin",
     "Galaxy English School Admin"),
    ("Latest News", "Latest News"),
    ("Life at Galaxy", "Life at Galaxy"),
    ("WHY CHOOSE GALAXY", "WHY CHOOSE GALAXY"),
    ("Galaxy English School", "Galaxy English School"),
    ("Galaxy English School", "Galaxy English School"),
]


def target_files():
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        rel = os.path.relpath(root, BASE)
        if rel.startswith("venv") or rel.startswith(".venv"):
            continue
        for name in files:
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            if ext == ".py":
                yield path
            elif ext == ".html" and rel.startswith("templates"):
                yield path
            elif path.endswith("config/settings.py"):
                yield path


changed = 0
for path in target_files():
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        changed += 1
        print("updated:", os.path.relpath(path, BASE))

print(f"\n{changed} file(s) rebranded to Galaxy English School.")