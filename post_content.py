#!/usr/bin/env python3
"""
Nyavodroid — publication multi-formats (texte / image+texte / Reel).
Intégration Pexels vs IA, rendu texte Pillow (lisibilité garantie), watermark double.
"""

import os
import random
import subprocess
import sys
import time
import json
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    MARGIN, DETAIL_FONTSIZE,
    POST_WIDTH, POST_HEIGHT, STORY_WIDTH, STORY_HEIGHT,
    EXPRESSIONS_DIR, PROFILE_IMAGE_PATH, EMOJIS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])

IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
AUDIO_PATH = "background_music.mp3"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
DELAY_ENTRE_IMAGES = 30

STRUCTURE_REEL = [
    {"acte": "ACCROCHE", "role": "Scène d'ouverture — capte l'attention immédiatement",
     "ambiance": "calme, mystérieuse, contemplative",
     "consigne_texte": "Une phrase d'accroche qui pose le décor ou une question",
     "consigne_image": "Plan large, ambiance calme et mystérieuse, le sujet vu de loin ou partiellement caché, atmosphère contemplative, lumière douce"},
    {"acte": "TENSION", "role": "Développement — crée la surprise ou la tension",
     "ambiance": "dynamique, intense, inattendue",
     "consigne_texte": "Un fait surprenant, un chiffre choc ou une révélation",
     "consigne_image": "Plan rapproché, ambiance dynamique et intense, le sujet au centre de l'action, éléments visuels percutants, contraste élevé"},
    {"acte": "RÉVÉLATION", "role": "Chute — la révélation finale qui marque l'esprit",
     "ambiance": "épique, lumineuse, mémorable",
     "consigne_texte": "La chute, la prédiction ou le message final percutant",
     "consigne_image": "Plan final épique, ambiance lumineuse et mémorable, le sujet révélé dans toute sa puissance, effet dramatique, lumière néon intense"},
]


# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════
def clean_backslash(t: str) -> str:
    """Supprime les backslashes parasites qui pourraient apparaître dans le texte."""
    return t.replace("\\", "")


def choisir_type_contenu() -> str:
    h = datetime.now(timezone.utc).hour
    if 6 <= h < 8:
        return "texte_seul"
    if 8 <= h < 12:
        return "image_texte"
    if 16 <= h < 20:
        return "reel"
    return random.choices(["reel", "image_texte", "texte_seul"], weights=[40, 35, 25], k=1)[0]


def choisir_pilier() -> str:
    return random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]


# ══════════════════════════════════════════════
#  FORMAT 1 : TEXTE SEUL (fond Pillow)
# ══════════════════════════════════════════════
def generer_post_texte_seul(pilier: str) -> (str, str):
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français et EXTRÊMEMENT COURT :\n"
        "1 phrase de contexte + 1 fait choc avec un chiffre, maximum 15 mots.\n"
        f"Sujet : {sujet}. {TON_EDITORIAL}"
    )
    print(f"  📝 Génération texte post seul...\n     Sujet : {sujet}")
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post texte)")
    texte = M.clean_text(texte)
    texte = clean_backslash(texte)
    print(f"  ✅ Texte : « {texte} »")

    chemin_image = "post_text_image.png"
    M.generer_fond_texte_seul(texte, chemin_image)   # fond violet avec le texte centré
    return texte, chemin_image


def publier_texte_seul(pilier: str) -> dict:
    texte, image_path = generer_post_texte_seul(pilier)
    # Légende minimale avec #Nyavodroid
    legende = f"{texte}\n\n#Nyavodroid"

    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : (post texte seul)\n📌 Texte : {texte}\n")

    # Publication comme photo
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(image_path, "rb") as f:
            r = M._req("POST", ep,
                       data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(image_path), f, "image/png")},
                       timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Post texte (image) publié — ID : {res['id']}")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "post texte") from e
    except OSError as e:
        raise RuntimeError(f"Fichier image illisible : {e}") from e