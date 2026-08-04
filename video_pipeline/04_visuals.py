#!/usr/bin/env python3
"""
Phase 4 — Recherche/génération des visuels par scène.
Entrée  : scenes.json
Sortie  : video_pipeline/assets/scene_XXX.jpg (une image par scène)
          + mise à jour de scenes.json (champ image_source ajouté)

Stratégie :
- Pexels prioritaire (photos réelles, zéro texte parasite)
- Fallback IA documentaire si Pexels échoue
- Détection des requêtes dupliquées consécutives → variation automatique
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from content_config import STYLE_IMAGE_SUFFIX

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT
)


# ──────────────────────────────────────────────
#  Prompt IA anti-texte renforcé (fallback)
# ──────────────────────────────────────────────
def build_ai_prompt(visual_desc: str, search_query: str, is_variant: bool = False) -> str:
    """Construit un prompt IA documentaire sans texte parasite."""
    variant_note = (
        ", DIFFERENT ANGLE or COMPOSITION than previous scene" if is_variant else ""
    )
    return (
        f"Professional documentary photography, photorealistic, 8k, sharp focus{variant_note}. "
        f"Subject: {visual_desc}. Keywords: {search_query}. "
        f"Vertical composition (portrait orientation). "
        f"ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, "
        f"NO TYPOGRAPHY, NO WATERMARKS, NO LOGOS, NO CAPTIONS, NO SUBTITLES."
    )


# ──────────────────────────────────────────────
#  Téléchargement/génération d'une scène
# ──────────────────────────────────────────────
def download_scene_image(scene: dict, prev_query: str | None) -> str:
    """
    Télécharge/génère l'image d'une scène.
    Retourne "pexels", "ai" ou "failed" selon la source utilisée.
    """
    image_path = os.path.join(ASSETS_DIR, scene["image"])
    query = scene.get("search_query", "").strip()
    visual = scene.get("visual", "").strip()

    # Détection de requête dupliquée (pour varier les visuels)
    is_duplicate = prev_query and prev_query.lower() == query.lower()

    # ── 1. Pexels prioritaire ──
    if query:
        print(f"    🖼️  [Pexels] '{query}'")
        if M.get_image_from_pexels(query, image_path, size=(VIDEO_WIDTH, VIDEO_HEIGHT)):
            return "pexels"
        print(f"    ⚠️  Pexels KO")

    # ── 2. Fallback IA ──
    prompt = build_ai_prompt(visual or query or "abstract concept", query, is_variant=is_duplicate)
    print(f"    🎨 [IA] Fallback documentaire")
    try:
        M.image_avec_fallback(
            prompt,
            os.environ.get("GEMINI_API_KEY_CONTENT", ""),
            image_path,
            size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        )
        if os.path.isfile(image_path) and os.path.getsize(image_path) > 1024:
            return "ai"
    except Exception as e:
        print(f"    ❌ IA échec : {e}")

    return "failed"


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────
def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable — lance 03_analyze.py d'abord")
        sys.exit(1)

    os.makedirs(ASSETS_DIR, exist_ok=True)

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)

    scenes = doc.get("scenes", [])
    if not scenes:
        print("❌ scenes.json vide")
        sys.exit(1)

    print(f"\n🖼️  [04_visuals] {len(scenes)} scènes à illustrer\n")

    stats = {"pexels": 0, "ai": 0, "failed": 0}
    prev_query = None

    for scene in scenes:
        idx = scene.get("scene", "?")
        query = scene.get("search_query", "")
        print(f"  [{idx}/{len(scenes)}] {scene.get('spoken_text', '')[:50]}...")

        source = download_scene_image(scene, prev_query)
        scene["image_source"] = source
        stats[source] += 1
        prev_query = query

        status = "✅" if source != "failed" else "❌"
        print(f"    {status} {source}\n")

    # Mise à jour de scenes.json avec image_source
    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)

    print("─" * 50)
    print(f"📊 Bilan :")
    print(f"   Pexels : {stats['pexels']}")
    print(f"   IA     : {stats['ai']}")
    print(f"   Échec  : {stats['failed']}")
    print(f"   Total  : {len(scenes)}")
    print(f"\n✅ {SCENES_FILE} mis à jour")


if __name__ == "__main__":
    main()