#!/usr/bin/env python3
"""
Phase 4 — Visuels premium Tech/Science, cohérents avec la narration.
IA (style clay) en priorité ; fallback Pexels si l'IA échoue
(une vraie photo cohérente vaut mieux qu'aucune image).
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
    "Premium tech/science 3D render, modern clean futuristic cinematic minimalist, "
    "soft light sky-blue gradient background (#B8DCE8 to #D4E8EE), "
    "colorful saturated 3D objects (brick red #C94A3C, docker blue #1E88C9, mustard yellow #E8B84B), "
    "glossy plastic and matte metal, soft diffuse studio lighting, slight 3/4 top-down angle, "
    "vertical 9:16, subject in upper-middle third, dark gradient bottom third, "
    "consistent lighting and palette across all scenes, "
    "ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO LABELS, no text on objects."
)

def generate_scene_image(scene, variant):
    visual = scene.get("visual") or scene.get("search_query") or "technology concept"
    query = scene.get("search_query") or visual
    path = os.path.join(ASSETS_DIR, scene["image"])
    v = ", DIFFERENT angle/composition than previous scene" if variant else ""

    # 1) IA (style clay) en priorité
    prompt = f"{STYLE_NYAVODROID} Show EXACTLY this concrete subject: {visual}.{v}"
    try:
        M.image_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""),
                              path, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        if os.path.isfile(path) and os.path.getsize(path) > 1024:
            return "ai"
    except Exception as e:
        print(f"    ⚠️ IA échec : {e}")

    # 2) Fallback Pexels (photo réelle cohérente)
    print(f"    🖼️  Fallback Pexels : '{query}'")
    if M.get_image_from_pexels(query, path, size=(VIDEO_WIDTH, VIDEO_HEIGHT)):
        return "pexels"

    return "failed"

def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable — lance 03_analyze.py"); sys.exit(1)
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(SCENES_FILE, "r", encoding="utf-8") as f: doc = json.load(f)
    scenes = doc.get("scenes", [])
    print(f"\n🖼️  [04_visuals] {len(scenes)} scènes (IA + fallback Pexels)\n")

    stats = {"ai": 0, "pexels": 0, "failed": 0}
    prev = None
    for s in scenes:
        print(f"  [{s.get('scene')}] {s.get('spoken_text','')[:40]}...")
        src = generate_scene_image(s, variant=(prev == s.get("search_query")))
        s["image_source"] = src
        stats[src] += 1
        prev = s.get("search_query")
        print(f"    {'✅' if src != 'failed' else '❌'} {src}\n")

    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"📊 IA : {stats['ai']} | Pexels : {stats['pexels']} | Échec : {stats['failed']}")

    if stats["failed"] == len(scenes):
        print("❌ Aucune image générée → le pipeline s'arrêtera proprement.")

if __name__ == "__main__":
    main()