#!/usr/bin/env python3
"""
Nyavo Channel — publication multi-formats.
  - 📝 Texte seul     (POST /feed)
  - 🖼️  Image + Texte  (POST /photos)
  - 🎬 Reel vidéo     (POST /video_reels — storytelling 3 actes)

Texte : Mistral → fallback Gemini [content]
Images : Gemini Interactions → fallback Pollinations anonyme
Vidéo : ffmpeg

Projet Gemini : nyavo-content (clé dédiée GEMINI_API_KEY_CONTENT)
Secrets : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_CONTENT, MISTRAL_API_KEY (opt.)
Dépendances : requests>=2.31.0 | ffmpeg + fonts-dejavu-core
"""

import base64
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone

import requests

from content_config import (
    PILLAR_KEYS,
    PILLAR_WEIGHTS,
    PILLARS,
    STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX,
    SUJETS_PAR_PILIER,
    TON_EDITORIAL,
)


# ──────────────────────────────────────────────
# Nettoyage
# ──────────────────────────────────────────────
def _nettoyer_secret(valeur: str) -> str:
    return valeur.encode("ascii", "ignore").decode("ascii").strip()


def _nettoyer_texte(texte: str) -> str:
    texte = re.sub(
        r'[\u200e\u200f\u200b\u200c\u200d\ufeff\u00ad\u2060\u180e\u202a-\u202e\u2066-\u2069]',
        '', texte,
    )
    texte = texte.replace('**', '').replace('*', '')
    texte = ''.join(c for c in texte if c.isprintable() or c in '\n\t')
    return texte.strip()


# ──────────────────────────────────────────────
# Variables d'environnement (NETTOYÉES)
# ──────────────────────────────────────────────
FB_PAGE_ID = _nettoyer_secret(os.environ["FB_PAGE_ID"])
FB_PAGE_ACCESS_TOKEN = _nettoyer_secret(os.environ["FB_PAGE_ACCESS_TOKEN"])
GEMINI_API_KEY = _nettoyer_secret(os.environ["GEMINI_API_KEY_CONTENT"])
MISTRAL_API_KEY = _nettoyer_secret(os.environ.get("MISTRAL_API_KEY", ""))

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"
IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
AUDIO_PATH = "background_music.mp3"

MISTRAL_TEXT_URL = "https://api.mistral.ai/v1/chat/completions"
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)
GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"

POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/"
POLLINATIONS_WIDTH, POLLINATIONS_HEIGHT = 1080, 1920

MAX_RETRIES = 4
RETRY_DELAY = 30
TIMEOUT = 60
DELAY_ENTRE_IMAGES = 30

# ──────────────────────────────────────────────
# Structure narrative du Reel (storytelling 3 actes)
# ──────────────────────────────────────────────
STRUCTURE_REEL = [
    {
        "acte": "ACCROCHE",
        "role": "Scène d'ouverture — capte l'attention immédiatement",
        "ambiance": "calme, mystérieuse, contemplative",
        "consigne_texte": "Une phrase d'accroche qui pose le décor ou une question",
        "consigne_image": (
            "Plan large, ambiance calme et mystérieuse, "
            "le sujet est vu de loin ou partiellement caché, "
            "atmosphère contemplative, lumière douce"
        ),
    },
    {
        "acte": "TENSION",
        "role": "Développement — crée la surprise ou la tension",
        "ambiance": "dynamique, intense, inattendue",
        "consigne_texte": "Un fait surprenant, un chiffre choc ou une révélation",
        "consigne_image": (
            "Plan rapproché, ambiance dynamique et intense, "
            "le sujet est au centre de l'action, "
            "éléments visuels percutants, contraste élevé"
        ),
    },
    {
        "acte": "RÉVÉLATION",
        "role": "Chute — la révélation finale qui marque l'esprit",
        "ambiance": "épique, lumineuse, mémorable",
        "consigne_texte": "La chute, la prédiction ou le message final percutant",
        "consigne_image": (
            "Plan final épique, ambiance lumineuse et mémorable, "
            "le sujet est révélé dans toute sa puissance, "
            "effet dramatique, lumière néon intense"
        ),
    },
]


# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════
def _requete_avec_retry(
    methode: str, url: str, *,
    headers: dict | None = None, json_data: dict | None = None,
    data: dict | None = None, files: dict | None = None,
    timeout: int = TIMEOUT, stream: bool = False,
) -> requests.Response:
    derniere_erreur: Exception | None = None
    for tentative in range(1, MAX_RETRIES + 1):
        try:
            reponse = requests.request(
                method=methode, url=url, headers=headers,
                json=json_data, data=data, files=files,
                timeout=timeout, stream=stream,
            )
            if reponse.status_code == 429 or reponse.status_code >= 500:
                attente = RETRY_DELAY * tentative
                print(f"  ⚠️  HTTP {reponse.status_code} — retry dans {attente}s ({tentative}/{MAX_RETRIES})")
                derniere_erreur = requests.exceptions.HTTPError(
                    f"HTTP {reponse.status_code}", response=reponse
                )
                time.sleep(attente)
                continue
            reponse.raise_for_status()
            return reponse
        except requests.exceptions.Timeout as e:
            derniere_erreur = e
            print(f"  ⚠️  Timeout — retry dans {RETRY_DELAY * tentative}s")
            time.sleep(RETRY_DELAY * tentative)
        except requests.exceptions.ConnectionError as e:
            derniere_erreur = e
            print(f"  ⚠️  Connexion — retry dans {RETRY_DELAY * tentative}s")
            time.sleep(RETRY_DELAY * tentative)
        except requests.exceptions.HTTPError:
            raise
    raise derniere_erreur  # type: ignore[misc]


def _erreur_facebook(e: requests.exceptions.HTTPError, contexte: str) -> RuntimeError:
    corps, code = "", "N/A"
    if e.response is not None:
        code = e.response.status_code
        try:
            err = e.response.json().get("error", {})
            corps = f"[{err.get('type','?')}] {err.get('message','?')} (code {err.get('code','?')})"
        except Exception:
            corps = e.response.text[:400]
    return RuntimeError(f"Facebook Graph ({contexte}, HTTP {code}) : {corps}")


def _extraire_image_base64(resultat: dict) -> str:
    if "output_image" in resultat:
        oi = resultat["output_image"]
        if isinstance(oi, dict) and "data" in oi:
            return oi["data"]
        if isinstance(oi, str):
            return oi
    if "output" in resultat:
        for item in resultat["output"]:
            if isinstance(item, dict):
                if item.get("type") == "image" and "data" in item:
                    return item["data"]
                if "inlineData" in item:
                    return item["inlineData"]["data"]
                if "inline_data" in item:
                    return item["inline_data"]["data"]
    if "candidates" in resultat:
        for part in resultat["candidates"][0]["content"]["parts"]:
            if "inlineData" in part:
                return part["inlineData"]["data"]
            if "inline_data" in part:
                return part["inline_data"]["data"]
    raise ValueError(f"Impossible d'extraire l'image. Clés : {list(resultat.keys())}")


# ══════════════════════════════════════════════
#  GÉNÉRATION IMAGE : Gemini → fallback Pollinations
# ══════════════════════════════════════════════
def _image_gemini(prompt: str, chemin: str) -> None:
    reponse = _requete_avec_retry(
        "POST", GEMINI_IMAGE_URL,
        headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
        json_data={
            "model": GEMINI_IMAGE_MODEL,
            "input": [{"type": "text", "text": prompt}],
            "response_format": {"type": "image", "aspect_ratio": "9:16", "image_size": "1K"},
        },
        timeout=120,
    )
    image_b64 = _extraire_image_base64(reponse.json())
    with open(chemin, "wb") as f:
        f.write(base64.b64decode(image_b64))


def _image_pollinations(prompt: str, chemin: str) -> None:
    encoded = urllib.parse.quote(prompt)
    url = (
        f"{POLLINATIONS_IMAGE_URL}{encoded}"
        f"?width={POLLINATIONS_WIDTH}&height={POLLINATIONS_HEIGHT}&nologo=true"
    )
    reponse = _requete_avec_retry(
        "GET", url,
        headers={"User-Agent": "NyavoChannel/1.0"},
        timeout=120,
        stream=True,
    )
    with open(chemin, "wb") as f:
        for chunk in reponse.iter_content(chunk_size=8192):
            f.write(chunk)


def generer_image(prompt: str, chemin: str) -> None:
    """Génère une image 9:16 : Gemini d'abord, Pollinations en fallback."""
    prompt_propre = _nettoyer_texte(prompt)

    try:
        print(f"  🖼️  Image via Gemini...")
        _image_gemini(prompt_propre, chemin)
        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(f"Image suspecte ({taille} octets)")
        print(f"  ✅ Image Gemini : {chemin} ({taille:,} octets)")
        return
    except Exception as e:
        print(f"  ⚠️  Gemini image échec : {e}")

    try:
        print(f"  🖼️  Fallback image via Pollinations...")
        _image_pollinations(prompt_propre, chemin)
        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(f"Image Pollinations suspecte ({taille} octets)")
        print(f"  ✅ Image Pollinations : {chemin} ({taille:,} octets)")
    except Exception as e2:
        raise RuntimeError(
            f"Gemini ET Pollinations ont échoué.\n"
            f"Gemini : {e}\nPollinations : {e2}"
        ) from e2


# ══════════════════════════════════════════════
#  CHOIX DU TYPE DE CONTENU
# ══════════════════════════════════════════════
def choisir_type_contenu() -> str:
    heure = datetime.now(timezone.utc).hour
    if 6 <= heure < 8:
        return "texte_seul"
    elif 8 <= heure < 12:
        return "image_texte"
    elif 16 <= heure < 20:
        return "reel"
    else:
        return random.choices(["reel", "image_texte", "texte_seul"], weights=[40, 35, 25], k=1)[0]


def choisir_pilier() -> str:
    return random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]


# ══════════════════════════════════════════════
#  GÉNÉRATION TEXTE (Mistral → fallback Gemini B)
# ══════════════════════════════════════════════
def _texte_mistral(prompt: str) -> str:
    reponse = _requete_avec_retry(
        "POST", MISTRAL_TEXT_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json_data={
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300, "temperature": 0.9,
        },
        timeout=30,
    )
    return _nettoyer_texte(reponse.json()["choices"][0]["message"]["content"])


def _texte_gemini(prompt: str) -> str:
    reponse = _requete_avec_retry(
        "POST", f"{GEMINI_TEXT_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json_data={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 300, "temperature": 0.9},
        },
        timeout=30,
    )
    return _nettoyer_texte(reponse.json()["candidates"][0]["content"]["parts"][0]["text"])


def generer_texte(prompt: str, contexte: str = "") -> str:
    if MISTRAL_API_KEY:
        try:
            print(f"  📝 Texte via Mistral {contexte}...")
            return _texte_mistral(prompt)
        except Exception as e:
            print(f"  ⚠️  Mistral échec : {e}")
    try:
        print(f"  📝 Texte via Gemini [content] {contexte}...")
        return _texte_gemini(prompt)
    except Exception as e:
        raise RuntimeError(f"Texte impossible (Mistral + Gemini KO) : {e}") from e


# ══════════════════════════════════════════════
#  FORMAT 1 : TEXTE SEUL
# ══════════════════════════════════════════════
def publier_texte_seul(pilier: str) -> dict:
    style = random.choice(STORY_PROMPTS)
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    prompt = (
        f"Tu es Nyavo Channel, une chaîne tech qui révèle les mécanismes "
        f"cachés du monde numérique.\n\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\nFormat : {style}\n\n"
        f"Consignes :\n"
        f"- Écris un post Facebook de 3-5 lignes en français\n"
        f"- Ton : {TON_EDITORIAL}\n"
        f"- Inclus 2-3 termes techniques précis\n"
        f"- Termine par 2-3 hashtags pertinents\n"
        f"- Pas de guillemets, pas de titre, pas de Markdown\n"
        f"- Interdit : généralités, banalités, hors-sujet\n"
    )
    texte = generer_texte(prompt, "(post texte)")
    print(f"\n📌 Axe    : {PILLARS[pilier]['label']}")
    print(f"📌 Sujet  : {sujet}")
    print(f"📌 Texte  :\n{texte}\n")

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/feed"
    try:
        reponse = _requete_avec_retry(
            "POST", endpoint,
            data={"message": texte, "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=TIMEOUT,
        )
        resultat = reponse.json()
        if "id" not in resultat:
            raise ValueError(f"Réponse FB inattendue : {resultat}")
        print(f"  ✅ Post texte publié — ID : {resultat['id']}")
        return resultat
    except requests.exceptions.HTTPError as e:
        raise _erreur_facebook(e, "post texte") from e


# ══════════════════════════════════════════════
#  FORMAT 2 : IMAGE + TEXTE
# ══════════════════════════════════════════════
def publier_image_texte(pilier: str) -> dict:
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt_legende = (
        f"Tu es Nyavo Channel.\nAxe : {label}\nSujet : {sujet}\n"
        f"Écris une légende Facebook de 2-3 lignes en français.\n"
        f"Ton : {TON_EDITORIAL}\nInclus 2-3 hashtags. Pas de guillemets, pas de Markdown."
    )
    legende = generer_texte(prompt_legende, "(légende)")

    prompt_image = f"Illustration verticale 9:16 sur le sujet : {sujet}\nAxe : {label}\nStyle : {STYLE_IMAGE_SUFFIX}"
    print("  🖼️  Génération image...")
    generer_image(prompt_image, IMAGE_PATH)

    print(f"\n📌 Axe     : {label}")
    print(f"📌 Sujet   : {sujet}")
    print(f"📌 Légende :\n{legende}\n")

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    try:
        with open(IMAGE_PATH, "rb") as f:
            reponse = _requete_avec_retry(
                "POST", endpoint,
                data={"caption": legende, "access_token": FB_PAGE_ACCESS_TOKEN},
                files={"source": (os.path.basename(IMAGE_PATH), f, "image/png")},
                timeout=TIMEOUT,
            )
        resultat = reponse.json()
        if "id" not in resultat:
            raise ValueError(f"Réponse FB inattendue : {resultat}")
        print(f"  ✅ Image+Texte publié — ID : {resultat['id']}")
        return resultat
    except requests.exceptions.HTTPError as e:
        raise _erreur_facebook(e, "photo + légende") from e
    except OSError as e:
        raise RuntimeError(f"Fichier image illisible : {e}") from e


# ══════════════════════════════════════════════
#  FORMAT 3 : REEL VIDÉO — STORYTELLING 3 ACTES
# ══════════════════════════════════════════════
def _generer_phrases_reel(pilier: str) -> tuple[str, list[str]]:
    """
    Génère une mini-histoire en 3 actes pour le Reel.
    Retourne (sujet, [phrase_acte1, phrase_acte2, phrase_acte3]).
    """
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # Construire la description des 3 actes pour le prompt
    actes_desc = ""
    for i, acte in enumerate(STRUCTURE_REEL, 1):
        actes_desc += (
            f"Acte {i} — {acte['acte']} : {acte['role']}\n"
            f"  → {acte['consigne_texte']}\n"
        )

    prompt = (
        f"Tu es Nyavo Channel, une chaîne tech immersive spécialisée dans le "
        f"storytelling technologique.\n\n"
        f"Axe : {label}\n"
        f"Sujet imposé : {sujet}\n\n"
        f"MISSION : Raconte une MINI-HISTOIRE en exactement {NB_IMAGES_REEL} actes.\n"
        f"Les {NB_IMAGES_REEL} phrases doivent former une narration cohérente "
        f"avec une progression dramatique, PAS des faits isolés.\n\n"
        f"Structure narrative :\n{actes_desc}\n"
        f"Consignes :\n"
        f"- Chaque phrase : moins de 10 mots\n"
        f"- Numérotées de 1 à {NB_IMAGES_REEL}, une par ligne\n"
        f"- Ton : {TON_EDITORIAL}\n"
        f"- Les 3 phrases doivent se suivre comme une histoire : "
        f"début → tension → chute\n"
        f"- Le lecteur doit avoir envie de voir la scène suivante\n"
        f"- PAS de Markdown, PAS d'astérisques\n"
        f"- Interdit : faits isolés sans lien, généralités, hors-sujet\n\n"
        f"Exemple de structure (ne pas copier, juste le format) :\n"
        f"1. [Accroche] En 2024, un serveur a disparu sans trace\n"
        f"2. [Tension] 48h plus tard, 3 millions de comptes étaient vides\n"
        f"3. [Révélation] Le coupable ? Une seule ligne de code\n\n"
        f"Format :\n1. Phrase une\n2. Phrase deux\n3. Phrase trois"
    )

    texte_brut = generer_texte(prompt, f"(Reel storytelling : {sujet})")

    phrases = []
    for ligne in texte_brut.split("\n"):
        ligne = _nettoyer_texte(ligne)
        if ligne and ligne[0].isdigit() and "." in ligne:
            phrase = _nettoyer_texte(ligne.split(".", 1)[1].strip())
            if phrase:
                phrases.append(phrase)

    if len(phrases) < NB_IMAGES_REEL:
        raise ValueError(
            f"Phrases insuffisantes ({len(phrases)}/{NB_IMAGES_REEL}) : {texte_brut}"
        )
    return sujet, phrases[:NB_IMAGES_REEL]


def _generer_images_reel(pilier: str, phrases: list[str], sujet: str) -> list[str]:
    """
    Génère les 3 images du Reel avec continuité narrative.
    Chaque image est une scène qui suit la précédente.
    """
    label = PILLARS[pilier]["label"]
    chemins = []

    for i, (phrase, acte) in enumerate(zip(phrases, STRUCTURE_REEL), 1):
        chemin = f"reel_img_{i}.png"

        # Contexte narratif pour la cohérence visuelle
        contexte_narratif = ""
        if i > 1:
            contexte_narratif += f"Scène précédente : « {phrases[i-2]} »\n"
        if i < len(phrases):
            contexte_narratif += f"Scène suivante : « {phrases[i]} »\n"

        prompt = (
            f"Scène {i}/{NB_IMAGES_REEL} d'une mini-histoire visuelle en 3 actes.\n"
            f"Sujet global : {sujet}\n"
            f"Axe : {label}\n\n"
            f"ACTE {i} — {acte['acte']} : {acte['role']}\n"
            f"Texte de cette scène : « {phrase} »\n"
            f"Ambiance : {acte['ambiance']}\n"
            f"Cadrage : {acte['consigne_image']}\n\n"
        )

        if contexte_narratif:
            prompt += f"Continuité narrative :\n{contexte_narratif}\n"

        prompt += (
            f"Style : {STYLE_IMAGE_SUFFIX}\n"
            f"IMPORTANT : Cette image doit être visuellement cohérente avec "
            f"les autres scènes de l'histoire. Même univers, même palette "
            f"de couleurs, même ambiance générale. La progression visuelle "
            f"doit refléter la progression narrative."
        )

        if i > 1:
            pause = DELAY_ENTRE_IMAGES + random.uniform(0, 10)
            print(f"  ⏳ Pause anti-rate-limit : {pause:.0f}s...")
            time.sleep(pause)

        print(f"  🖼️  Scène {i}/{NB_IMAGES_REEL} [{acte['acte']}]...")
        generer_image(prompt, chemin)
        chemins.append(chemin)

    return chemins


def _assembler_video(images: list[str], textes: list[str], sortie: str) -> None:
    """Assemble les 3 scènes en vidéo avec texte animé et transitions."""
    audio_existe = os.path.exists(AUDIO_PATH)
    if not audio_existe:
        print(f"  ⚠️  '{AUDIO_PATH}' absent → vidéo sans son.")

    inputs: list[str] = []
    for img in images:
        inputs += ["-loop", "1", "-t", str(DUREE_PAR_IMAGE), "-i", img]
    if audio_existe:
        inputs += ["-i", AUDIO_PATH]

    n = len(images)

    # Concaténation avec transitions fondu entre les scènes
    # Chaque scène a un fade in/out de 0.5s pour la fluidité narrative
    filtres = []

    # Appliquer un léger zoom progressif sur chaque scène (effet Ken Burns)
    for i in range(n):
        t0 = 0
        t1 = DUREE_PAR_IMAGE
        # Zoom lent de 100% à 108% sur la durée de la scène
        filtres.append(
            f"[{i}:v]scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={STORY_WIDTH}:{STORY_HEIGHT},"
            f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(DUREE_PAR_IMAGE * 25)}:s={STORY_WIDTH}x{STORY_HEIGHT}:fps=25,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={DUREE_PAR_IMAGE - 0.5}:d=0.5"
            f"[scene{i}]"
        )

    # Concaténer les scènes
    concat_inputs = "".join(f"[scene{i}]" for i in range(n))
    filtres.append(f"{concat_inputs}concat=n={n}:v=1:a=0[slideshow]")

    # Texte animé par scène avec indicateur d'acte
    txt_chain = "[slideshow]"
    for i, (texte, acte) in enumerate(zip(textes, STRUCTURE_REEL)):
        t_esc = texte.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")
        t0 = i * DUREE_PAR_IMAGE
        t1 = (i + 1) * DUREE_PAR_IMAGE

        # Fade in/out du texte
        alpha = (
            f"if(lt(t-{t0},0.6),min((t-{t0})/0.6,1),"
            f"if(gt(t,{t1}-0.6),max(1-({t1}-t)/0.6,0),1))"
        )

        # Texte principal (phrase de la scène)
        txt_chain += (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{t_esc}':fontcolor=0x00E5FF:fontsize=56:"
            f"x=(w-text_w)/2:y=h*0.78:box=1:boxcolor=0x0D0D0D@0.75:boxborderw=28:"
            f"alpha='{alpha}':"
            f"enable='between(t,{t0 + 0.3},{t1 - 0.3})'"
        )

        # Petit indicateur d'acte en haut (ex: "1/3 — ACCROCHE")
        acte_label = f"{i + 1}/{NB_IMAGES_REEL}"
        txt_chain += (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{acte_label}':fontcolor=0x00E5FF@0.5:fontsize=28:"
            f"x=(w-text_w)/2:y=60:"
            f"alpha='{alpha}':"
            f"enable='between(t,{t0 + 0.3},{t1 - 0.3})'"
        )

    filtres.append(txt_chain + "[final]")

    # Mapping
    map_args = ["-map", "[final]"]
    if audio_existe:
        map_args += ["-map", f"{n}:a"]

    cmd = [
        "ffmpeg", *inputs,
        "-filter_complex", ";".join(filtres),
        *map_args,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest" if audio_existe else "-t", str(n * DUREE_PAR_IMAGE),
        "-y", sortie,
    ]
    try:
        print("  🎬 Assemblage vidéo ffmpeg (storytelling 3 actes)...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        taille = os.path.getsize(sortie)
        print(f"  ✅ Vidéo : {sortie} ({taille:,} octets)")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:800]}") from e


def publier_reel(pilier: str) -> dict:
    """Publie un Reel vidéo storytelling 3 actes."""
    sujet, phrases = _generer_phrases_reel(pilier)

    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}")
    print(f"📌 Sujet : {sujet}")
    print(f"📌 Storytelling Reel ({NB_IMAGES_REEL} actes) :")
    for i, (p, acte) in enumerate(zip(phrases, STRUCTURE_REEL), 1):
        print(f"   {i}. [{acte['acte']}] {p}")

    images = _generer_images_reel(pilier, phrases, sujet)
    _assembler_video(images, phrases, REEL_VIDEO_PATH)

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/video_reels"
    try:
        print("  📤 Reel — phase 1/3 (start)...")
        r1 = _requete_avec_retry(
            "POST", endpoint,
            data={"upload_phase": "start", "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=TIMEOUT,
        )
        init = r1.json()
        video_id = init.get("video_id")
        upload_url = init.get("upload_url")
        if not video_id or not upload_url:
            raise ValueError(f"Phase start échouée : {init}")

        print("  📤 Reel — phase 2/3 (transfer)...")
        with open(REEL_VIDEO_PATH, "rb") as f:
            _requete_avec_retry(
                "POST", upload_url,
                data={"upload_phase": "transfer", "video_id": video_id, "access_token": FB_PAGE_ACCESS_TOKEN},
                files={"video_file": (os.path.basename(REEL_VIDEO_PATH), f, "video/mp4")},
                timeout=300,
            )

        print("  📤 Reel — phase 3/3 (finish)...")
        r3 = _requete_avec_retry(
            "POST", endpoint,
            data={"upload_phase": "finish", "video_id": video_id, "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=TIMEOUT,
        )
        resultat = r3.json()
        print(f"  ✅ Reel publié — Video ID : {video_id}")
        return resultat
    except requests.exceptions.HTTPError as e:
        raise _erreur_facebook(e, "Reel vidéo") from e
    except OSError as e:
        raise RuntimeError(f"Fichier vidéo illisible : {e}") from e


# ══════════════════════════════════════════════
#  FONCTION PRINCIPALE
# ══════════════════════════════════════════════
def main() -> None:
    print("=" * 60)
    print("🎬 Nyavo Channel — Multi-formats [Projet Gemini B]")
    print("=" * 60)

    type_contenu = choisir_type_contenu()
    pilier = choisir_pilier()

    labels = {"texte_seul": "📝 Texte seul", "image_texte": "🖼️  Image + Texte", "reel": "🎬 Reel vidéo"}
    print(f"\n📌 Format : {labels[type_contenu]}")
    print(f"📌 Pilier : {PILLARS[pilier]['label']}")
    print(f"📌 Heure  : {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n")

    if type_contenu == "texte_seul":
        resultat = publier_texte_seul(pilier)
    elif type_contenu == "image_texte":
        resultat = publier_image_texte(pilier)
    elif type_contenu == "reel":
        resultat = publier_reel(pilier)
    else:
        raise ValueError(f"Type inconnu : {type_contenu}")

    print(f"\n{'=' * 60}")
    print(f"✅ TERMINÉ — {labels[type_contenu]}")
    print(f"   ID : {resultat.get('id', resultat.get('video_id', 'N/A'))}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"\n❌ Secret manquant : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Inattendu : {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)