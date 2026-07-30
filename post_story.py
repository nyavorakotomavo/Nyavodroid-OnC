#!/usr/bin/env python3
"""
Nyavo Channel — publication STORY (image courte, texte minimal).

⚠️ LIMITE API IMPORTANTE : l'API Graph ne permet PAS d'ajouter des
stickers interactifs (sondage, question, quiz) par automatisation — ces
éléments n'existent que dans l'app Facebook manuelle. Ce script publie
donc une image avec le fait/chiffre/question écrit directement dessus,
ce qui reproduit l'esprit de l'interactivité sans le sticker natif.

Secrets requis : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
"""

import os
import random
import subprocess
import sys
import urllib.parse
import urllib.request

import requests

from content_config import PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS, STYLE_IMAGE_SUFFIX

FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
GRAPH_API_VERSION = "v21.0"
STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920


def generer_texte_story() -> tuple[str, str]:
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    style_prompt = random.choice(STORY_PROMPTS)
    prompt = (
        f"Écris {style_prompt}, en français, une seule phrase courte "
        f"(moins de 15 mots), sans guillemets, pour la catégorie "
        f"'{PILLARS[pilier]['label']}'."
    )
    url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return pilier, resp.text.strip().strip('"').split("\n")[0]


def generer_url_image_story(pilier: str) -> str:
    prompt = f"{PILLARS[pilier]['label']}, {STYLE_IMAGE_SUFFIX}, vertical composition"
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={STORY_WIDTH}&height={STORY_HEIGHT}&nologo=true"
    )


def telecharger_image(url: str, chemin: str) -> None:
    urllib.request.urlretrieve(url, chemin)


def incruster_texte(image_in: str, texte: str, image_out: str) -> None:
    """Superpose le texte (façon sticker) sur l'image via ffmpeg."""
    texte_ffmpeg = texte.replace("'", "\\'").replace(":", "\\:")
    filtre = (
        f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={STORY_WIDTH}:{STORY_HEIGHT},"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{texte_ffmpeg}':fontcolor=0x00E5FF:fontsize=58:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x0D0D0D@0.7:boxborderw=30:"
        f"line_spacing=14"
    )
    subprocess.run(
        ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", image_out],
        check=True,
    )


def uploader_photo_non_publiee(image_path: str) -> str:
    """Upload une photo en mode non publié, retourne son photo_id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        data = {"published": "false", "access_token": FB_PAGE_ACCESS_TOKEN}
        resp = requests.post(endpoint, data=data, files=files, timeout=60)
    resp.raise_for_status()
    return resp.json()["id"]


def publier_story(photo_id: str) -> dict:
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photo_stories"
    payload = {"photo_id": photo_id, "access_token": FB_PAGE_ACCESS_TOKEN}
    resp = requests.post(endpoint, data=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    pilier, texte = generer_texte_story()
    print(f"Pilier : {PILLARS[pilier]['label']}")
    print(f"Texte story : {texte}")

    image_url = generer_url_image_story(pilier)
    telecharger_image(image_url, "story_raw.png")
    incruster_texte("story_raw.png", texte, STORY_IMAGE_PATH)

    photo_id = uploader_photo_non_publiee(STORY_IMAGE_PATH)
    resultat = publier_story(photo_id)
    print(f"Story publiée avec succès : {resultat}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
