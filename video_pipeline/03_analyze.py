#!/usr/bin/env python3
"""
Phase 3 — Analyse de la narration → scenes.json (cerveau).
Entrée  : phrase_times.json + metadata.json
Sortie  : scenes.json (lu par les phases 4, 5, 6, 7)

Pour chaque phrase on demande à l'IA :
- quel visuel montrer (description + requête Pexels)
- quelle animation (zoom_in, zoom_out, pan_left, pan_right, pan_up, pan_down)
- quel SFX déclencher (whoosh, impact, click, glitch, explosion, transition, pop, none)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from content_config import PILLARS

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    DURATION_TARGET_SEC, SFX_LIBRARY
)


def analyser_phrase(phrase: str, sujet: str) -> dict:
    """Demande à l'IA comment illustrer une phrase."""
    sfx_choices = ", ".join(sorted(SFX_LIBRARY.keys()))
    animations = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]

    prompt = (
        "Tu es un directeur photo de vidéo verticale courte.\n"
        f"Sujet global : {sujet}\n"
        f"Phrase à illustrer : \"{phrase}\"\n\n"
        "Réponds UNIQUEMENT en JSON (sans markdown) :\n"
        "{\n"
        "  \"visual\": \"description courte (10 mots max) du visuel à afficher\",\n"
        "  \"search_query\": \"requête Pexels en anglais (3-5 mots concrets)\",\n"
        f"  \"animation\": \"UNE de [{', '.join(animations)}]\",\n"
        f"  \"sfx\": \"UNE de [{sfx_choices}] ou 'none'\",\n"
        "  \"subtitle_text\": \"texte à afficher à l'écran (la phrase, éventuellement tronquée à 8 mots)\",\n"
        "  \"highlight_words\": [\"mot1\", \"mot2\"] (max 2 mots à surligner en jaune)\n"
        "}\n"
    )

    brut = M.texte_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""), "[scene analyze]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]

    try:
        return json.loads(brut)
    except json.JSONDecodeError:
        # Fallback minimal si LLM sort n'importe quoi
        return {
            "visual": phrase,
            "search_query": sujet,
            "animation": "zoom_in",
            "sfx": "none",
            "subtitle_text": phrase,
            "highlight_words": [],
        }


def main():
    times_path = os.path.join(BASE_DIR, "phrase_times.json")
    meta_path = os.path.join(BASE_DIR, "metadata.json")
    if not os.path.isfile(times_path):
        print(f"❌ {times_path} introuvable — lance 02_voice.py d'abord")
        sys.exit(1)

    with open(times_path, "r", encoding="utf-8") as f:
        timings = json.load(f)
    meta = {}
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    sujet = meta.get("sujet", "")
    print(f"\n🧠 [03_analyze] Analyse de {len(timings['phrases'])} phrases...")

    scenes = []
    for p in timings["phrases"]:
        print(f"  🔍 Phrase {p['index']} : {p['text'][:50]}...")
        analyse = analyser_phrase(p["text"], sujet)
        scenes.append({
            "scene": p["index"],
            "start": p["start"],
            "end": p["end"],
            "duration": p["duration"],
            "spoken_text": p["text"],
            "visual": analyse.get("visual", p["text"]),
            "search_query": analyse.get("search_query", sujet),
            "animation": analyse.get("animation", "zoom_in"),
            "sfx": analyse.get("sfx", "none"),
            "subtitle_text": analyse.get("subtitle_text", p["text"]),
            "highlight_words": analyse.get("highlight_words", []),
            "image": f"scene_{p['index']:03d}.jpg",
        })

    scenes_doc = {
        "video": {
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "fps": VIDEO_FPS,
            "total_duration": timings["total_duration"],
            "duration_target": DURATION_TARGET_SEC,
        },
        "metadata": meta,
        "scenes": scenes,
    }

    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(scenes_doc, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ scenes.json généré ({len(scenes)} scènes, {timings['total_duration']:.1f}s)")
    print(f"  ✅ {SCENES_FILE}")


if __name__ == "__main__":
    main()