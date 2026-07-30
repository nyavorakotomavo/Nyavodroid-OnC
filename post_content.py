#!/usr/bin/env python3
"""
Nyavo Channel — publication multi-formats.
  - 📝 Texte seul     (POST /feed)
  - 🖼️  Image + Texte  (POST /photos)
  - 🎬 Reel vidéo     (POST /video_reels — upload 3 phases)

La Story est gérée séparément par post_story.py (Projet Gemini A).

Rotation selon l'heure UTC :
  07h → texte_seul | 09h → image_texte | 17h → reel
  workflow_dispatch → aléatoire pondéré

Texte : Mistral → fallback Gemini [content]
Images : Gemini [content] — modèle gemini-3.1-flash-image-preview
Vidéo : ffmpeg (assemblage local)

Projet Gemini : nyavo-content (clé dédiée GEMINI_API_KEY_CONTENT)
Secrets : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_CONTENT, MISTRAL_API_KEY (opt.)
Dépendances : requests>=2.31.0 | ffmpeg + fonts-dejavu-core
"""

import base64
import os
import random
import subprocess
import sys
import time
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
# Variables d'environnement
# ──────────────────────────────────────────────
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY_CONTENT"]
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"
IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
NB_IMAGES_REEL = 5
DUREE_PAR_IMAGE = 2.5
AUDIO_PATH = "background_music.mp3"

MISTRAL_TEXT_URL = "https://api.mistral.ai/v1/chat/completions"
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)
# ✅ Modèle image corrigé : gemini-3.1-flash-image-preview
#    (supporte generationConfig.imageConfig.aspectRatio)
GEMINI_IMAGE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.1-flash-image-preview:generateContent"
)

MAX_RETRIES = 5
RETRY_DELAY = 20
TIMEOUT = 60
DELAY_ENTRE_IMAGES = 15


# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════
def _requete_avec_retry(
    methode: str,
    url: str,
    *,
    headers: dict | None = None,
    json_data: dict | None = None,
    data: dict | None = None,
    files: dict | None = None,
    timeout: int = TIMEOUT,
) -> requests.Response:
    """Requête HTTP avec retries sur 429 / 5xx / timeout / connexion."""
    derniere_erreur: Exception | None = None

    for tentative in range(1, MAX_RETRIES + 1):
        try:
            reponse = requests.request(
                method=methode,
                url=url,
                headers=headers,
                json=json_data,
                data=data,
                files=files,
                timeout=timeout,
            )

            if reponse.status_code == 429 or reponse.status_code >= 500:
                attente = RETRY_DELAY * tentative
                print(
                    f"  ⚠️  HTTP {reponse.status_code} — retry dans {attente}s "
                    f"({tentative}/{MAX_RETRIES})"
                )
                derniere_erreur = requests.exceptions.HTTPError(
                    f"HTTP {reponse.status_code}", response=reponse
                )
                time.sleep(attente)
                continue

            reponse.raise_for_status()
            return reponse

        except requests.exceptions.Timeout as e:
            derniere_erreur = e
            attente = RETRY_DELAY * tentative
            print(f"  ⚠️  Timeout — retry dans {attente}s ({tentative}/{MAX_RETRIES})")
            time.sleep(attente)

        except requests.exceptions.ConnectionError as e:
            derniere_erreur = e
            attente = RETRY_DELAY * tentative
            print(f"  ⚠️  Connexion — retry dans {attente}s ({tentative}/{MAX_RETRIES})")
            time.sleep(attente)

        except requests.exceptions.HTTPError:
            raise

    raise derniere_erreur  # type: ignore[misc]


def _erreur_facebook(e: requests.exceptions.HTTPError, contexte: str) -> RuntimeError:
    """Extrait un message clair d'une erreur Facebook Graph."""
    corps, code = "", "N/A"
    if e.response is not None:
        code = e.response.status_code
        try:
            err = e.response.json().get("error", {})
            corps = (
                f"[{err.get('type', '?')}] "
                f"{err.get('message', '?')} "
                f"(code {err.get('code', '?')})"
            )
        except Exception:
            corps = e.response.text[:400]
    return RuntimeError(f"Facebook Graph ({contexte}, HTTP {code}) : {corps}")


# ══════════════════════════════════════════════
#  CHOIX DU TYPE DE CONTENU
# ══════════════════════════════════════════════
def choisir_type_contenu() -> str:
    """
    Détermine le format selon l'heure UTC.
      07h → texte_seul | 09h → image_texte | 17h → reel
      Sinon → aléatoire pondéré.
    """
    heure = datetime.now(timezone.utc).hour

    if 6 <= heure < 8:
        return "texte_seul"
    elif 8 <= heure < 12:
        return "image_texte"
    elif 16 <= heure < 20:
        return "reel"
    else:
        return random.choices(
            ["reel", "image_texte", "texte_seul"],
            weights=[40, 35, 25],
            k=1,
        )[0]


def choisir_pilier() -> str:
    """Tire un pilier aléatoire pondéré."""
    return random.choices(
        PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1
    )[0]


# ══════════════════════════════════════════════
#  GÉNÉRATION TEXTE (Mistral → fallback Gemini B)
# ══════════════════════════════════════════════
def _texte_mistral(prompt: str) -> str:
    """Appel Mistral API."""
    reponse = _requete_avec_retry(
        "POST",
        MISTRAL_TEXT_URL,
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        json_data={
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.9,
        },
        timeout=30,
    )
    return reponse.json()["choices"][0]["message"]["content"].strip()


def _texte_gemini(prompt: str) -> str:
    """Appel Gemini API [content]."""
    reponse = _requete_avec_retry(
        "POST",
        f"{GEMINI_TEXT_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json_data={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 300, "temperature": 0.9},
        },
        timeout=30,
    )
    return reponse.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def generer_texte(prompt: str, contexte: str = "") -> str:
    """Génère du texte : Mistral d'abord, Gemini [content] en fallback."""
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
#  GÉNÉRATION IMAGE (Gemini B)
# ══════════════════════════════════════════════
def generer_image(prompt: str, chemin: str) -> None:
    """Génère une image 9:16 via Gemini [content] et sauvegarde en PNG."""
    reponse = _requete_avec_retry(
        "POST",
        f"{GEMINI_IMAGE_URL}?key={GEMINI_API_KEY}",
        headers={"Content-Type": "application/json"},
        json_data={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": "9:16"},
            },
        },
        timeout=120,
    )

    resultat = reponse.json()

    # Extraire l'image base64 de la réponse
    image_b64 = None
    for part in resultat["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            image_b64 = part["inlineData"]["data"]
            break

    if not image_b64:
        raise ValueError("Pas de données image dans la réponse Gemini.")

    with open(chemin, "wb") as f:
        f.write(base64.b64decode(image_b64))

    taille = os.path.getsize(chemin)
    if taille < 1024:
        raise ValueError(f"Image suspecte ({taille} octets)")
    print(f"  ✅ Image : {chemin} ({taille:,} octets)")


# ══════════════════════════════════════════════
#  FORMAT 1 : TEXTE SEUL
# ══════════════════════════════════════════════
def publier_texte_seul(pilier: str) -> dict:
    """Publie un post texte simple aligné sur la niche. POST /{page-id}/feed"""
    style = random.choice(STORY_PROMPTS)
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        f"Tu es Nyavo Channel, une chaîne tech qui révèle les mécanismes "
        f"cachés du monde numérique.\n\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\n"
        f"Format : {style}\n\n"
        f"Consignes :\n"
        f"- Écris un post Facebook de 3-5 lignes en français\n"
        f"- Ton : {TON_EDITORIAL}\n"
        f"- Inclus 2-3 termes techniques précis\n"
        f"- Termine par 2-3 hashtags pertinents\n"
        f"- Pas de guillemets, pas de titre\n"
        f"- Interdit : généralités, banalités, hors-sujet\n"
    )

    texte = generer_texte(prompt, "(post texte)")
    print(f"\n📌 Axe    : {PILLARS[pilier]['label']}")
    print(f"📌 Sujet  : {sujet}")
    print(f"📌 Texte  :\n{texte}\n")

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/feed"

    try:
        reponse = _requete_avec_retry(
            "POST",
            endpoint,
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
    """Publie une photo avec légende alignée sur la niche. POST /{page-id}/photos"""
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # Légende
    prompt_legende = (
        f"Tu es Nyavo Channel.\n"
        f"Axe : {label}\n"
        f"Sujet : {sujet}\n"
        f"Écris une légende Facebook de 2-3 lignes en français.\n"
        f"Ton : {TON_EDITORIAL}\n"
        f"Inclus 2-3 hashtags. Pas de guillemets."
    )
    legende = generer_texte(prompt_legende, "(légende)")

    # Image liée au sujet
    prompt_image = (
        f"Illustration verticale 9:16 sur le sujet : {sujet}\n"
        f"Axe : {label}\n"
        f"Style : {STYLE_IMAGE_SUFFIX}"
    )
    print("  🖼️  Génération image...")
    generer_image(prompt_image, IMAGE_PATH)

    print(f"\n📌 Axe     : {label}")
    print(f"📌 Sujet   : {sujet}")
    print(f"📌 Légende :\n{legende}\n")

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"

    try:
        with open(IMAGE_PATH, "rb") as f:
            reponse = _requete_avec_retry(
                "POST",
                endpoint,
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
#  FORMAT 3 : REEL VIDÉO
# ══════════════════════════════════════════════
def _generer_phrases_reel(pilier: str) -> tuple[str, list[str]]:
    """
    Génère les phrases du Reel alignées sur la niche.
    Retourne (sujet, [phrase_1, ..., phrase_N]).
    """
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    style = random.choice(STORY_PROMPTS)

    prompt = (
        f"Tu es Nyavo Channel, une chaîne tech immersive.\n\n"
        f"Axe : {label}\n"
        f"Sujet imposé : {sujet}\n"
        f"Format : {style}\n\n"
        f"Consignes :\n"
        f"- Génère exactement {NB_IMAGES_REEL} phrases très courtes "
        f"(moins de 8 mots chacune)\n"
        f"- Numérotées de 1 à {NB_IMAGES_REEL}, une par ligne\n"
        f"- Ton : {TON_EDITORIAL}\n"
        f"- Chaque phrase doit être un fait/chiffre/question percutant\n"
        f"- Progression narrative : accroche → développement → révélation\n"
        f"- Interdit : généralités, hors-sujet\n"
        f"Format :\n1. Phrase une\n2. Phrase deux\n..."
    )

    texte_brut = generer_texte(prompt, f"(Reel : {sujet})")

    phrases = []
    for ligne in texte_brut.split("\n"):
        ligne = ligne.strip()
        if ligne and ligne[0].isdigit() and "." in ligne:
            phrase = ligne.split(".", 1)[1].strip()
            if phrase:
                phrases.append(phrase)

    if len(phrases) < NB_IMAGES_REEL:
        raise ValueError(
            f"Phrases insuffisantes ({len(phrases)}/{NB_IMAGES_REEL}) : {texte_brut}"
        )
    return sujet, phrases[:NB_IMAGES_REEL]


def _generer_images_reel(pilier: str, phrases: list[str]) -> list[str]:
    """Génère les images du Reel, chacune liée à sa phrase."""
    label = PILLARS[pilier]["label"]
    chemins = []

    for i, phrase in enumerate(phrases, 1):
        chemin = f"reel_img_{i}.png"
        prompt = (
            f"Illustration verticale 9:16, scène {i}/{NB_IMAGES_REEL}.\n"
            f"Texte de la scène : « {phrase} »\n"
            f"Axe : {label}\n"
            f"Style : {STYLE_IMAGE_SUFFIX}\n"
            f"L'image doit illustrer visuellement cette phrase précise."
        )

        # Pause entre les images pour éviter le rate limit
        if i > 1:
            pause = DELAY_ENTRE_IMAGES + random.uniform(0, 5)
            print(f"  ⏳ Pause anti-rate-limit : {pause:.0f}s...")
            time.sleep(pause)

        print(f"  🖼️  Image Reel {i}/{NB_IMAGES_REEL}...")
        generer_image(prompt, chemin)
        chemins.append(chemin)

    return chemins


def _assembler_video(images: list[str], textes: list[str], sortie: str) -> None:
    """Assemble les images en vidéo avec texte animé via ffmpeg."""
    audio_existe = os.path.exists(AUDIO_PATH)
    if not audio_existe:
        print(f"  ⚠️  '{AUDIO_PATH}' absent → vidéo sans son.")

    # Inputs
    inputs: list[str] = []
    for img in images:
        inputs += ["-loop", "1", "-t", str(DUREE_PAR_IMAGE), "-i", img]
    if audio_existe:
        inputs += ["-i", AUDIO_PATH]

    # Filtres
    n = len(images)
    concat = "".join(f"[{i}:v]" for i in range(n))
    filtres = [f"{concat}concat=n={n}:v=1:a=0[slideshow]"]

    txt_chain = "[slideshow]"
    for i, texte in enumerate(textes):
        t_esc = texte.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")
        t0 = i * DUREE_PAR_IMAGE
        t1 = (i + 1) * DUREE_PAR_IMAGE
        alpha = (
            f"if(lt(t-{t0},0.5),min((t-{t0})/0.5,1),"
            f"if(gt(t,{t1}-0.5),max(1-({t1}-t)/0.5,0),1))"
        )
        txt_chain += (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{t_esc}':fontcolor=0x00E5FF:fontsize=58:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x0D0D0D@0.7:"
            f"boxborderw=30:alpha='{alpha}':"
            f"enable='between(t,{t0},{t1})'"
        )
    filtres.append(txt_chain + "[final]")

    # Mapping
    map_args = ["-map", "[final]"]
    if audio_existe:
        map_args += ["-map", f"{n}:a"]

    cmd = [
        "ffmpeg",
        *inputs,
        "-filter_complex", ";".join(filtres),
        *map_args,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest" if audio_existe else "-t", str(n * DUREE_PAR_IMAGE),
        "-y", sortie,
    ]

    try:
        print("  🎬 Assemblage vidéo ffmpeg...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        taille = os.path.getsize(sortie)
        print(f"  ✅ Vidéo : {sortie} ({taille:,} octets)")

    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:800]}") from e


def publier_reel(pilier: str) -> dict:
    """Publie un Reel vidéo. POST /{page-id}/video_reels (3 phases)."""
    sujet, phrases = _generer_phrases_reel(pilier)
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}")
    print(f"📌 Sujet : {sujet}")
    print(f"📌 Phrases Reel :")
    for i, p in enumerate(phrases, 1):
        print(f"   {i}. {p}")

    images = _generer_images_reel(pilier, phrases)
    _assembler_video(images, phrases, REEL_VIDEO_PATH)

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/video_reels"

    try:
        # Phase 1 : start
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

        # Phase 2 : transfer
        print("  📤 Reel — phase 2/3 (transfer)...")
        with open(REEL_VIDEO_PATH, "rb") as f:
            _requete_avec_retry(
                "POST", upload_url,
                data={
                    "upload_phase": "transfer",
                    "video_id": video_id,
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                },
                files={"video_file": (os.path.basename(REEL_VIDEO_PATH), f, "video/mp4")},
                timeout=300,
            )

        # Phase 3 : finish
        print("  📤 Reel — phase 3/3 (finish)...")
        r3 = _requete_avec_retry(
            "POST", endpoint,
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "access_token": FB_PAGE_ACCESS_TOKEN,
            },
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

    labels = {
        "texte_seul": "📝 Texte seul",
        "image_texte": "🖼️  Image + Texte",
        "reel": "🎬 Reel vidéo",
    }
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