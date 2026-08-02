#!/usr/bin/env python3
"""
Nyavodroid — STORY avec hiérarchie de texte dynamique, emoji en image,
watermark double (expression + profil), style Infographie Narrative d'Expert.
"""

import os
import random
import subprocess
import sys
import json

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    HOOK_FONTSIZE, EXPL_FONTSIZE, DETAIL_FONTSIZE, MARGIN,
    EXPRESSIONS_DIR, PROFILE_IMAGE_PATH, EMOJIS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])

STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920


# ══════════════════════════════════════════════
#  UTILITAIRES (identiques à ceux de post_content)
# ══════════════════════════════════════════════
def wrap_text(text: str, max_chars: int = 26) -> str:
    if not text:
        return ""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line = f"{current_line} {word}".strip()
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    if len(lines) == 1 and len(lines[0]) > max_chars:
        s = lines[0]
        lines = [s[i:i+max_chars] for i in range(0, len(s), max_chars)]
    return "\n".join(lines)


def escape_text(t: str) -> str:
    return t.replace("'", "\\'").replace(":", "\\:").replace("%", "%%").replace("\\", "\\\\")


def clean_backslash(t: str) -> str:
    return t.replace("\\", "")


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + 1


def _get_emoji_path(emoji_char: str) -> str | None:
    """Cherche une image PNG correspondant à l'emoji dans assets/emojis/."""
    emoji_filename = emoji_char + ".png"
    path = os.path.join(EMOJIS_DIR, emoji_filename)
    if os.path.isfile(path):
        return path
    # fallback : premier emoji trouvé
    if os.path.isdir(EMOJIS_DIR):
        for f in os.listdir(EMOJIS_DIR):
            if f.endswith(".png"):
                return os.path.join(EMOJIS_DIR, f)
    return None


# ══════════════════════════════════════════════
#  GÉNÉRATION DE TEXTE HIÉRARCHISÉ (JSON)
# ══════════════════════════════════════════════
def generer_texte_story():
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        "Tu es Nyavodroid, la page tech premium.\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\n\n"
        "Génère UNIQUEMENT un objet JSON avec les clés :\n"
        '  "hook" : phrase d\'accroche choc (max 10 mots), commence par un emoji pertinent\n'
        '  "explication" : 2-3 lignes développant le hook, en langage simple\n'
        '  "detail" : une précision chiffrée, une source ou une note courte (1 ligne)\n\n'
        "Règles :\n"
        "- Pas de texte autour du JSON.\n"
        "- Ton : " + TON_EDITORIAL + "\n"
        "- Compréhensible par tous.\n"
    )
    print(f"  📝 Génération texte hiérarchique...\n     Axe   : {PILLARS[pilier]['label']}\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]
    try:
        data = json.loads(brut)
        hook = data.get("hook", "")
        explication = data.get("explication", "")
        detail = data.get("detail", "")
    except Exception:
        print("  ⚠️ JSON invalide, utilisation du texte brut comme hook.")
        hook = brut
        explication = ""
        detail = ""

    hook = M.clean_text(hook)
    explication = M.clean_text(explication)
    detail = M.clean_text(detail)

    # Ajouter un emoji si absent du hook
    if hook and not any(ord(c) > 127 for c in hook[:3]):
        emojis = ["💡", "🔍", "⚡", "🧠", "🤖", "🛡️", "🌐", "🔐", "💻", "🚀", "📡", "🧬"]
        hook = random.choice(emojis) + " " + hook

    print(f"  ✅ Hook      : {hook}")
    if explication:
        print(f"     Explication : {explication}")
    if detail:
        print(f"     Détail      : {detail}")
    return pilier, sujet, hook, explication, detail


# ══════════════════════════════════════════════
#  IMAGE DE FOND
# ══════════════════════════════════════════════
def generer_image_story(pilier: str, sujet: str, chemin: str) -> None:
    """Génère l'image 9:16 avec le style premium (via IA)."""
    prompt = M.clean_text(
        f"Illustration verticale 9:16 pour le sujet : {sujet}\n"
        f"Axe : {PILLARS[pilier]['label']}\nStyle : {STYLE_IMAGE_SUFFIX}"
    )
    M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin, size=(1080, 1920))