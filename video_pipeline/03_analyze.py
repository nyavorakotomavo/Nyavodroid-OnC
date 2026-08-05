#!/usr/bin/env python3
"""
Phase 3 — Découpage en scènes + correspondance phrase→visuel stricte.
Chaque image doit EXPLIQUER la phrase. Aucun visuel générique/aléatoire.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    DURATION_TARGET_SEC, SFX_LIBRARY
)

def analyser_phrase(phrase, sujet):
    sfx = ", ".join(sorted(SFX_LIBRARY.keys()))
    anims = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]
    prompt = (
        "Tu es directeur photo d'une vidéo Tech/Science premium.\n"
        f"Sujet global : {sujet}\nPhrase à illustrer : \"{phrase}\"\n\n"
        "Question obligatoire : qu'est-ce que cette image EXPLIQUE par rapport à cette phrase ?\n"
        "Si aucune réponse claire, choisis l'objet CONCRET nommé dans la phrase "
        "(batterie, laboratoire, chercheur, puce, télescope, prototype...).\n"
        "INTERDIT : visuel 'futuriste générique', personnage 3D aléatoire, objet sans rapport.\n\n"
        "Réponds UNIQUEMENT en JSON :\n"
        "{\n"
        '  "visual": "description courte (10 mots max) du visuel qui explique la phrase",\n'
        '  "search_query": "requête anglaise concrète (3-5 mots, objets réels)",\n'
        f'  "animation": "UNE de [{", ".join(anims)}]",\n'
        f'  "sfx": "UNE de [{sfx}] ou none",\n'
        '  "subtitle_text": "la phrase, tronquée à 10 mots max",\n'
        '  "highlight_words": ["mot1"] (max 1 mot clé)\n'
        "}\n"
    )
    brut = M.texte_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""), "[scene]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]
    try: return json.loads(brut)
    except Exception:
        return {"visual": phrase, "search_query": sujet, "animation": "zoom_in",
                "sfx": "none", "subtitle_text": phrase, "highlight_words": []}

def main():
    times_path = os.path.join(BASE_DIR, "phrase_times.json")
    meta_path = os.path.join(BASE_DIR, "metadata.json")
    if not os.path.isfile(times_path):
        print(f"❌ {times_path} introuvable — lance 02_voice.py"); sys.exit(1)
    with open(times_path, "r", encoding="utf-8") as f: timings = json.load(f)
    meta = {}
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)
    sujet = meta.get("sujet", "")

    print(f"\n🧠 [03_analyze] {len(timings['phrases'])} scènes...")
    scenes = []
    for p in timings["phrases"]:
        a = analyser_phrase(p["text"], sujet)
        scenes.append({
            "scene": p["index"], "start": p["start"], "end": p["end"], "duration": p["duration"],
            "spoken_text": p["text"], "visual": a.get("visual", p["text"]),
            "search_query": a.get("search_query", sujet), "animation": a.get("animation", "zoom_in"),
            "sfx": a.get("sfx", "none"), "subtitle_text": a.get("subtitle_text", p["text"]),
            "highlight_words": a.get("highlight_words", []),
            "image": f"scene_{p['index']:03d}.jpg",
        })

    doc = {"video": {"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT, "fps": VIDEO_FPS,
                     "total_duration": timings["total_duration"],
                     "duration_target": DURATION_TARGET_SEC},
           "metadata": meta, "scenes": scenes}
    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {SCENES_FILE} ({len(scenes)} scènes)")

if __name__ == "__main__":
    main()