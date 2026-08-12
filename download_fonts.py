#!/usr/bin/env python3
"""
Nyavodroid — Téléchargement des polices premium (Inter + Nunito v4).
Ce script unifié remplace download_fonts.py et download_fonts_vis.py.
"""
import os
import shutil
import zipfile
from pathlib import Path

FONT_DIR = Path("assets/fonts")
FONT_DIR.mkdir(parents=True, exist_ok=True)

# ── Inter (Regular + Bold) ──
# Source : release officielle v4.1 sur GitHub
ZIP_PATH = FONT_DIR / "Inter-4.1.zip"
TARGETS = {"Inter-Regular.ttf", "Inter-Bold.ttf"}
extracted = set()

# Télécharger l'archive si absente
if not ZIP_PATH.exists():
    print("⬇️  Téléchargement d'Inter v4.1...")
    import requests
    url = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(ZIP_PATH, "wb") as f:
            f.write(r.content)
        print("✅ Archive téléchargée.")
    except Exception as e:
        print(f"❌ Erreur téléchargement : {e}")
        raise SystemExit(1)
else:
    print("✅ Archive déjà présente.")

# Extraire Regular et Bold
with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    for name in z.namelist():
        basename = os.path.basename(name)
        if basename in TARGETS and basename not in extracted:
            dest = FONT_DIR / basename
            with z.open(name) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            print(f"✅ {basename} extrait.")
            extracted.add(basename)

# Compléter les fichiers manquants depuis le repo
missing = TARGETS - extracted
for f in missing:
    src = Path(f"./assets/fonts/{f}")  # fallback : fichier déjà présent dans repo
    if src.exists():
        shutil.copy2(src, FONT_DIR / f)
        print(f"✅ {f} copié depuis le repo.")
        extracted.add(f)

if missing - extracted:
    print(f"⚠️ Fichiers non trouvés : {missing - extracted}")

print("🎉 Polices Inter installées avec succès !")

# ── Nunito (uniquement pour la marque VIS) ──
import os
if os.environ.get("BRAND", "nyavo").strip().lower() == "vis":
    NUNITO = FONT_DIR / "Nunito-VariableFont_wght.ttf"
    if not NUNITO.exists() or NUNITO.stat().st_size < 100_000:
        print("⬇️  Téléchargement de Nunito (marque VIS)...")
        url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/nunito/Nunito%5Bwght%5D.ttf"
        try:
            import urllib.request
            tmp = FONT_DIR / "nunito.tmp"
            req = urllib.request.Request(url, headers={"User-Agent": "Nyavodroid/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(NUNITO)
            print(f"✅ Nunito ({NUNITO.stat().size:,} o)")
        except Exception as e:
            tmp.unlink(missing_ok=True)
            print(f"❌ Nunito : {e}")
    else:
        print("✅ Nunito déjà présent.")
else:
    print("ℹ️  Marque nyavo : Nunito non requis.")