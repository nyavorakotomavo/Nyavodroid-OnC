#!/usr/bin/env python3
"""
VIS — Téléchargement des polices Fraunces + Nunito avec cascade de sources.
Fraunces : dépôt officiel Undercase Type + CDN jsDelivr + fallback Google Fonts.
Nunito : GitHub Google Fonts.
Idempotent : ne retélécharge pas si le fichier final existe et fait > 100 Ko.
"""
import os
import urllib.request
import shutil
from pathlib import Path

FONT_DIR = Path("assets/fonts")
FONT_DIR.mkdir(parents=True, exist_ok=True)

# Pour chaque police : liste d'URLs à tenter dans l'ordre
FONTS = {
    "Fraunces-VariableFont.ttf": [
        # 1. jsDelivr miroitant le dépôt officiel Undercase Type
        "https://cdn.jsdelivr.net/gh/undercasetype/Fraunces@master/fonts/variable/Fraunces%5Bopsz%2Cwght%5D.ttf",
        # 2. Dépôt officiel direct
        "https://github.com/undercasetype/Fraunces/raw/master/fonts/variable/Fraunces%5Bopsz%2Cwght%5D.ttf",
        # 3. Fallback : version statique Regular depuis Google Fonts
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/fraunces/static/Fraunces-Regular.ttf",
        # 4. Alternative : Lora (serif similaire, même rôle éditorial)
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/lora/static/Lora-Regular.ttf",
    ],
    "Nunito-VariableFont_wght.ttf": [
        "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nunito/Nunito%5Bwght%5D.ttf",
        "https://github.com/google/fonts/raw/main/ofl/nunito/Nunito%5Bwght%5D.ttf",
    ],
}

HEADERS = {"User-Agent": "Nyavodroid/1.0 (font-downloader)"}
MIN_SIZE = 50_000  # 50 Ko min (Fraunces static fait ~80 Ko)

def download_from_urls(final_name: str, urls: list) -> bool:
    dest = FONT_DIR / final_name
    if dest.exists() and dest.stat().st_size > MIN_SIZE:
        print(f"✅ {final_name} déjà présent ({dest.stat().st_size:,} o)")
        return True

    print(f"⬇️  {final_name}...")
    tmp = FONT_DIR / (final_name + ".tmp")
    last_error = None

    for i, url in enumerate(urls, 1):
        try:
            print(f"   Tentative {i}/{len(urls)} : {url[:80]}...")
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            size = tmp.stat().st_size
            if size < MIN_SIZE:
                tmp.unlink(missing_ok=True)
                print(f"   ⚠️  Fichier trop petit ({size:,} o)")
                continue
            tmp.replace(dest)
            print(f"✅ {final_name} ({size:,} o) via source {i}")
            return True
        except Exception as e:
            last_error = e
            tmp.unlink(missing_ok=True)
            print(f"   ⚠️  Source {i} échec : {e}")
            continue

    print(f"❌ {final_name} : toutes les sources ont échoué ({last_error})")
    return False

def main():
    ok_count = 0
    for final_name, urls in FONTS.items():
        if download_from_urls(final_name, urls):
            ok_count += 1
    print(f"\n🎉 {ok_count}/{len(FONTS)} polices installées dans {FONT_DIR}/")
    if ok_count < len(FONTS):
        print("⚠️  Certaines polices manquantes → get_font basculera sur DejaVu")

if __name__ == "__main__":
    main()
