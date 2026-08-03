#!/usr/bin/env python3
"""
Nyavodroid — Téléchargement des polices premium (Inter v4).
Crée le dossier assets/fonts/ si nécessaire et récupère les fichiers .ttf.
"""
import os
import requests

FONT_DIR = "assets/fonts"
# Liens corrigés vers Inter v4.1 (release officielle)
FONTS = {
    "Inter-Regular.ttf": "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip",
}

def main():
    if not os.path.exists(FONT_DIR):
        os.makedirs(FONT_DIR)
        print(f"📁 Dossier '{FONT_DIR}' créé.")

    zip_path = os.path.join(FONT_DIR, "Inter-4.1.zip")
    
    # Télécharger l'archive complète (plus fiable que les liens directs)
    if not os.path.exists(zip_path):
        print("⬇️  Téléchargement de Inter v4.1...")
        try:
            r = requests.get(FONTS["Inter-Regular.ttf"], timeout=60)
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                f.write(r.content)
            print("✅ Archive téléchargée.")
        except Exception as e:
            print(f"❌ Erreur : {e}")
            return
    else:
        print("✅ Archive déjà présente.")

    # Extraire uniquement Regular et Bold
    import zipfile
    targets = {"Inter-Regular.ttf", "Inter-Bold.ttf"}
    extracted = set()
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            basename = os.path.basename(name)
            if basename in targets and basename not in extracted:
                dest = os.path.join(FONT_DIR, basename)
                with z.open(name) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                print(f"✅ {basename} extrait.")
                extracted.add(basename)
    
    # Nettoyage
    missing = targets - extracted
    if missing:
        print(f"⚠️ Fichiers non trouvés dans l'archive : {missing}")
    else:
        print("🎉 Polices installées avec succès !")
        # Optionnel : supprimer le zip après extraction
        # os.remove(zip_path)

if __name__ == "__main__":
    main()