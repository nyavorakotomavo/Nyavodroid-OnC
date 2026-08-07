#!/usr/bin/env python3
"""Téléchargement des polices VIS (Fraunces + Nunito) depuis Google Fonts GitHub."""
import os, requests

FONT_DIR = "assets/fonts"
os.makedirs(FONT_DIR, exist_ok=True)

URLS = {
    "Fraunces-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/Fraunces%5Bopsz%2Cwght%5D.ttf",
    "Nunito-VariableFont_wght.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf"
}

for filename, url in URLS.items():
    path = os.path.join(FONT_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"✅ {filename} déjà présent.")
        continue
    print(f"⬇️  {filename}...")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"✅ {filename} ({os.path.getsize(path):,} o)")
    except Exception as e:
        print(f"❌ Échec {filename} : {e}")
