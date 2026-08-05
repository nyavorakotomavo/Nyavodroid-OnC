#!/usr/bin/env python3
"""
Phase 4 — Visuels au style Nyavodroid (3D clay/toy, charte stricte).
Toutes les images sont générées en IA dans le style de la marque
(fond bleu ciel, objets saturés, AUCUN texte sur les objets).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
)

STYLE_NYAVODROID = (
    "3D clay/toy render style (Cinema4D/Blender, premium claymation), "
    "soft light sky-blue gradient background (#B8DCE8 to #D4E8EE), "
    "subject rendered as colorful saturated 3D objects "
    "(brick red #C94A3C, docker blue #1E88C9, mustard yellow #E8B84B, emerald green), "
    "glossy plastic and matte brushed metal materials, rounded reinforced corners, "
    "soft diffuse studio lighting from above, light ground shadows, "
    "slight 3/4 top-down camera angle, vertical 9:16 composition, "
    "subject in the upper-to-middle third, dark gradient in the bottom third for text space, "
    "ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, NO LABELS, NO LOGOS, "
    "no text on objects, no watermark."
)


def generate_scene_image(scene: dict, is_variant: bool) -> str:
    visual = scene.get("visual", "") or scene.get("search_query", "")
    variant = ", DIFFERENT angle and composition than previous scene" if is_variant else ""
    prompt = f"{STYLE_NYAVODROID} Subject: {visual}.{variant}"
    image_path = os.path.join(ASSETS_DIR, scene["image"])
    try:
        M.image_avec_fallback(
            prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""),
            image_path, size=(VIDEO_WIDTH, VIDEO_HEIGHT),
        )
        if os.path.isfile(image_path) and os.path.getsize(image_path) > 1024:
            return "ai"
    except Exception as e:
        print(f"    ❌ IA échec : {e}")
    return "failed"


def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable — lance 03_analyze.py d'abord")
        sys.exit(1)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scenes = doc.get("scenes", [])
    print(f"\n️  [04_visuals] {len(scenes)} scènes (style Nyavodroid 3D)\n")

    stats = {"ai": 0, "failed": 0}
    prev = None
    for scene in scenes:
        print(f"  [{scene.get('scene')}] {scene.get('spoken_text','')[:40]}...")
        src = generate_scene_image(scene, is_variant=(prev == scene.get("search_query")))
        scene["image_source"] = src
        stats[src] += 1
        prev = scene.get("search_query")
        print(f"    {'✅' if src!='failed' else '❌'} {src}\n")

    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"📊 IA : {stats['ai']} | Échec : {stats['failed']}")


if __name__ == "__main__":
    main()