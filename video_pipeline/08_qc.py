#!/usr/bin/env python3
"""
Phase 8 — Contrôle qualité avant publication.
- Bloquant : niche Tech/Science + confiance (forte/moyenne) + vidéo/scènes valides.
- NON bloquant : source manquante (simple avertissement).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import BASE_DIR, SCENES_FILE, FINAL_VIDEO


def check_file(path, min_size=1024 * 1024):
    if not os.path.isfile(path):
        return False, f"Fichier absent : {path}"
    size = os.path.getsize(path)
    if size < min_size:
        return False, f"Fichier trop petit : {size} octets (min {min_size})"
    return True, "OK"


def check_metadata():
    meta_path = os.path.join(BASE_DIR, "metadata.json")
    ok, msg = check_file(meta_path, min_size=100)
    if not ok:
        return False, msg
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if not meta.get("niche_ok"):
        return False, "niche_ok = false"
    if meta.get("confiance") not in ("forte", "moyenne"):
        return False, f"confiance invalide : {meta.get('confiance')}"

    # Source : avertissement seulement, ne bloque PAS
    if not meta.get("source"):
        print("    ⚠️ Source absente (non bloquant)")
        return True, "OK (sans source)"

    return True, f"Source : {meta['source']} | confiance : {meta['confiance']}"


def check_scenes():
    if not os.path.isfile(SCENES_FILE):
        return False, f"{SCENES_FILE} absent"
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scenes = doc.get("scenes", [])
    if not scenes:
        return False, "Aucune scène"
    failed = sum(1 for s in scenes if s.get("image_source") == "failed")
    if failed > 0:
        return False, f"{failed} scène(s) sans image"
    return True, f"{len(scenes)} scènes OK"


def check_final_video():
    return check_file(FINAL_VIDEO, min_size=1024 * 1024)


def main():
    print("\n🔍 [08_qc] Contrôle qualité\n")
    checks = [
        ("Metadata", check_metadata),
        ("Scènes", check_scenes),
        ("Vidéo finale", check_final_video),
    ]
    all_ok = True
    for name, fn in checks:
        ok, msg = fn()
        status = "✅" if ok else "❌"
        print(f"  {status} {name} : {msg}")
        if not ok:
            all_ok = False

    if not all_ok:
        print("\n❌ QC BLOQUANT : vidéo non publiée (exit 3)")
        sys.exit(3)
    print("\n✅ QC OK : publication autorisée")


if __name__ == "__main__":
    main()