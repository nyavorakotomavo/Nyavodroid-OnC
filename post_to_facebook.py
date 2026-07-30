#!/usr/bin/env python3
"""
Nyavo Channel — publication FEED (posts photo/vidéo).
Les Stories sont gérées par post_story.py (script séparé).

Secrets requis : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN
"""

import json
import os
import random
import re
import subprocess
import sys
import urllib.parse
import urllib.request

import requests

from content_config import (
    CTA_QUESTIONS,
    FORMAT_WEIGHTS,
    HASHTAGS,
    HISTORY_WINDOW,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MAX_HOOK_CHARS,
    PILLAR_KEYS,
    PILLAR_WEIGHTS,
    PILLARS,
    STYLE_IMAGE_SUFFIX,
    VIDEO_DURATION_SECONDS,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)

FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
GRAPH_API_VERSION = "v21.0"
HISTORY_FILE = "history.json"
PROBA_SUJET_DYNAMIQUE = 0.3


# ---------------------------------------------------------------------------
# HISTORIQUE
# ---------------------------------------------------------------------------
def charger_historique() -> list:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def sauver_historique(historique: list) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historique[-50:], f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CHOIX DU CONTENU
# ---------------------------------------------------------------------------
def choisir_pilier() -> str:
    poids = [PILLAR_WEIGHTS[k] for k in PILLAR_KEYS]
    return random.choices(PILLAR_KEYS, weights=poids, k=1)[0]


def choisir_sujet(pilier: str, historique: list) -> str:
    recents = {h["sujet"] for h in historique[-HISTORY_WINDOW:]}
    if random.random() < PROBA_SUJET_DYNAMIQUE:
        sujet = generer_sujet_ia(pilier, recents)
        if sujet:
            return sujet
    candidats = [t for t in PILLARS[pilier]["topics"] if t not in recents]
    if not candidats:
        candidats = PILLARS[pilier]["topics"]
    return random.choice(candidats)


def _appeler_pollinations_texte(prompt: str) -> str:
    url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text.strip()


def generer_sujet_ia(pilier: str, recents: set) -> str:
    label = PILLARS[pilier]["label"]
    exclusions = " / ".join(list(recents)[:8]) if recents else "aucun"
    prompt = (
        f"Propose UN sujet original et accrocheur (une seule phrase courte, "
        f"en français, sans numérotation ni guillemets) pour un post de la "
        f"catégorie '{label}' sur une page tech/science. "
        f"Ne reprends pas ces sujets déjà utilisés : {exclusions}."
    )
    try:
        sujet = _appeler_pollinations_texte(prompt).strip('"').split("\n")[0]
        return sujet if 10 < len(sujet) < 200 else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# LÉGENDE STRUCTURÉE : hook < 80 car. / contexte 1 phrase / question / hashtags
# ---------------------------------------------------------------------------
def generer_legende(pilier: str, sujet: str) -> dict:
    hook_style = PILLARS[pilier]["hook_style"]
    prompt = (
        f"Sur le sujet '{sujet}', style {hook_style}, réponds STRICTEMENT "
        f"dans ce format, en français, sans rien ajouter d'autre :\n"
        f"HOOK: [une phrase choc de moins de {MAX_HOOK_CHARS} caractères, "
        f"1 emoji au début]\n"
        f"CONTEXTE: [une seule phrase qui appuie ou explique le hook]"
    )
    reponse = _appeler_pollinations_texte(prompt)

    hook_match = re.search(r"HOOK:\s*(.+)", reponse)
    contexte_match = re.search(r"CONTEXTE:\s*(.+)", reponse)

    hook = hook_match.group(1).strip() if hook_match else sujet.capitalize()
    contexte = contexte_match.group(1).strip() if contexte_match else ""

    hook = hook[:MAX_HOOK_CHARS]
    return {"hook": hook, "contexte": contexte}


def assembler_legende(pilier: str, hook: str, contexte: str) -> str:
    question = random.choice(CTA_QUESTIONS)
    hashtags = " ".join(HASHTAGS[pilier])
    return f"{hook}\n\n{contexte}\n\n👇 {question}\n\n{hashtags}"


# ---------------------------------------------------------------------------
# IMAGE / VIDÉO
# ---------------------------------------------------------------------------
def generer_url_image(sujet: str) -> str:
    prompt = f"{sujet}, {STYLE_IMAGE_SUFFIX}"
    encoded = urllib.parse.quote(prompt)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}&nologo=true"
    )


def telecharger_image(url: str, chemin: str) -> None:
    urllib.request.urlretrieve(url, chemin)


def fabriquer_video(image_path: str, hook: str, video_path: str) -> None:
    """Zoom progressif + hook en sous-titre bold, format 9:16, ~9s."""
    texte = hook.replace("'", "\\'").replace(":", "\\:")
    frames = VIDEO_DURATION_SECONDS * VIDEO_FPS
    filtre = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"zoompan=z='min(zoom+0.0015,1.3)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT},"
        "format=yuv420p,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{texte}':fontcolor=0x00E5FF:fontsize=50:"
        "x=(w-text_w)/2:y=h-350:box=1:boxcolor=0x0D0D0D@0.65:boxborderw=26:"
        "line_spacing=10"
    )
    subprocess.run(
        [
            "ffmpeg", "-loop", "1", "-i", image_path,
            "-vf", filtre, "-t", str(VIDEO_DURATION_SECONDS),
            "-r", str(VIDEO_FPS), "-y", video_path,
        ],
        check=True,
    )


# ---------------------------------------------------------------------------
# PUBLICATION
# ---------------------------------------------------------------------------
def publier_photo(caption: str, image_url: str) -> dict:
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    payload = {"url": image_url, "caption": caption, "access_token": FB_PAGE_ACCESS_TOKEN}
    resp = requests.post(endpoint, data=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def publier_video(caption: str, video_path: str) -> dict:
    endpoint = f"https://graph-video.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/videos"
    with open(video_path, "rb") as f:
        files = {"source": f}
        data = {"description": caption, "access_token": FB_PAGE_ACCESS_TOKEN}
        resp = requests.post(endpoint, data=data, files=files, timeout=180)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    historique = charger_historique()
    pilier = choisir_pilier()
    sujet = choisir_sujet(pilier, historique)
    format_choisi = random.choices(
        list(FORMAT_WEIGHTS.keys()), weights=list(FORMAT_WEIGHTS.values()), k=1
    )[0]

    print(f"Pilier : {PILLARS[pilier]['label']}")
    print(f"Sujet : {sujet}")
    print(f"Format : {format_choisi}")

    parties = generer_legende(pilier, sujet)
    caption = assembler_legende(pilier, parties["hook"], parties["contexte"])
    image_url = generer_url_image(sujet)

    if format_choisi == "photo":
        resultat = publier_photo(caption, image_url)
    else:
        telecharger_image(image_url, "post_image.png")
        fabriquer_video("post_image.png", parties["hook"], "post_video.mp4")
        resultat = publier_video(caption, "post_video.mp4")

    print(f"Publié avec succès : {resultat}")
    historique.append({"pilier": pilier, "sujet": sujet, "format": format_choisi})
    sauver_historique(historique)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
