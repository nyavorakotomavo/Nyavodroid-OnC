#!/usr/bin/env python3
"""
Nyavodroid — Téléchargement des polices premium (Inter).
Crée le dossier assets/fonts/ si nécessaire et récupère les fichiers .ttf.
"""
import os
import requests

FONT_DIR = "assets/fonts"
FONTS = {
    "Inter-Regular.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Regular.ttf",
    "Inter-Bold.ttf": "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Bold.ttf",
}

def main():
    if not os.path.exists(FONT_DIR):
        os.makedirs(FONT_DIR)
        print(f"📁 Dossier '{FONT_DIR}' créé.")

    for filename, url in FONTS.items():
        path = os.path.join(FONT_DIR, filename)
        if os.path.exists(path):
            print(f"✅ {filename} déjà présent.")
            continue
        
        print(f"⬇️  Téléchargement de {filename}...")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"✅ {filename} téléchargé avec succès.")
        except Exception as e:
            print(f"❌ Erreur pour {filename} : {e}")

if __name__ == "__main__":
    main()