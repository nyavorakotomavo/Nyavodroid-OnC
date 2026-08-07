#!/usr/bin/env python3
"""
VIS — Polices définitives : Inter Bold (titres) + Nunito (texte).
Inter est fourni par download_fonts.py (déjà présent dans le repo).
Ce script vérifie Inter et télécharge Nunito uniquement si absent.
"""
import os
import urllib.request
import shutil
from pathlib import Path

FONT_DIR = Path("assets/fonts")
FONT_DIR.mkdir(parents=True, exist_ok=True)

# Inter : fourni par download_fonts.py — simple vérification
for f in ("Inter-Regular.ttf", "Inter-Bold.ttf"):
    p = FONT_DIR / f
    if p.exists() and p.stat().st_size > 100_000:
        print(f"✅ {f} déjà présent ({p.stat().st_size:,} o)")
    else:
        print(f"❌ {f} manquant → lance d'abord : python3 download_fonts.py")

# Nunito : téléchargement si absent
NUNITO = FONT_DIR / "Nunito-VariableFont_wght.ttf"
if NUNITO.exists() and NUNITO.stat().st_size > 100_000:
    print(f"✅ Nunito déjà présent ({NUNITO.stat().st_size:,} o)")
else:
    url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nunito/Nunito%5Bwght%5D.ttf"
    print("⬇️  Nunito-VariableFont_wght.ttf...")
    tmp = FONT_DIR / "nunito.tmp"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Nyavodroid/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(NUNITO)
        print(f"✅ Nunito ({NUNITO.stat().st_size:,} o)")
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f"❌ Nunito : {e}")
