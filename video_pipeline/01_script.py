#!/usr/bin/env python3
"""
Phase 1 — Générateur de narration.
Entrée  : sujet + pilier (choisis via content_config)
Sortie  : narration.txt + metadata.json (title, duration_target, style)

Réutilise M.texte_avec_fallback pour la génération LLM.
"""
import json
import os
import random
import sys

# Ajoute la racine au path pour importer les modules du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from content_config import PILLARS, PILLAR_KEYS, PILLAR_WEIGHTS, SUJETS_PAR_PILIER, TON_EDITORIAL

from video_pipeline.config_video import BASE_DIR, MAX_PHRASES


def choisir_sujet():
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    return pilier, sujet


def generer_narration(sujet: str, label_pilier: str) -> dict:
    """Demande au LLM une narration structurée en phrases courtes."""
    prompt = (
        "Tu es Nyavodroid. Tu écris la narration d'une vidéo YouTube/TikTok verticale.\n"
        f"Sujet : {sujet}\n"
        f"Axe éditorial : {label_pilier}\n\n"
        f"Contraintes :\n"
        f"- Français uniquement.\n"
        f"- Entre 5 et {MAX_PHRASES} phrases courtes (max 15 mots par phrase).\n"
        f"- La première phrase doit être une ACCROCHE choc (question ou fait surprenant).\n"
        f"- La dernière phrase doit être une RÉVÉLATION ou chute mémorable.\n"
        f"- Entre les deux : TENSION progressive (faits, chiffres, explications).\n"
        f"- Aucune phrase orpheline, aucun connecteur inutile ('En effet', 'Ainsi', ...).\n"
        f"- Style : percutant, direct, sans jargon.\n\n"
        f"Réponds UNIQUEMENT en JSON (sans markdown) :\n"
        f'{{\n'
        f'  "title": "Titre accrocheur de 6 mots max",\n'
        f'  "style": "documentaire dynamique",\n'
        f'  "voice_style": "mystérieux",\n'
        f'  "phrases": ["phrase 1", "phrase 2", ...]\n'
        f'}}\n'
    )

    print(f"  📝 Génération narration...")
    brut = M.texte_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""), "[video script]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]

    try:
        data = json.loads(brut)
    except json.JSONDecodeError:
        # Fallback : split sur les points
        phrases = [p.strip() for p in brut.replace("!", ".").replace("?", ".").split(".") if p.strip()]
        data = {"title": sujet, "style": "documentaire", "voice_style": "neutre", "phrases": phrases}

    # Validation / nettoyage
    phrases = [M.clean_text(p) for p in data.get("phrases", []) if p.strip()]
    if not phrases:
        phrases = [sujet]
    phrases = phrases[:MAX_PHRASES]

    return {
        "title": M.clean_text(data.get("title", sujet))[:60],
        "style": data.get("style", "documentaire dynamique"),
        "voice_style": data.get("voice_style", "mystérieux"),
        "phrases": phrases,
    }


def main():
    M.ensure_dirs() if hasattr(M, "ensure_dirs") else None
    os.makedirs(BASE_DIR, exist_ok=True)

    pilier, sujet = choisir_sujet()
    print(f"\n🎬 [01_script] Sujet : {sujet} (axe : {PILLARS[pilier]['label']})")

    meta = generer_narration(sujet, PILLARS[pilier]["label"])

    # Sauvegarde narration
    narration_path = os.path.join(BASE_DIR, "narration.txt")
    with open(narration_path, "w", encoding="utf-8") as f:
        f.write("\n".join(meta["phrases"]))
    print(f"  ✅ Narration : {len(meta['phrases'])} phrases → {narration_path}")

    # Sauvegarde metadata
    meta_path = os.path.join(BASE_DIR, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "sujet": sujet,
            "pilier": pilier,
            "title": meta["title"],
            "style": meta["style"],
            "voice_style": meta["voice_style"],
            "nb_phrases": len(meta["phrases"]),
        }, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Meta → {meta_path}")


if __name__ == "__main__":
    main()