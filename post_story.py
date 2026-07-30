#!/usr/bin/env python3
"""
Nyavo Channel — publication STORY (image courte, texte minimal).
⚠️ LIMITE API : l'API Graph ne permet PAS d'ajouter des stickers
interactifs (sondage, question, quiz) par automatisation. Ce script
publie une image avec le texte écrit directement dessus.

Projet Gemini : nyavo-story (clé dédiée GEMINI_API_KEY_STORY)
Secrets requis : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_STORY
Dépendances : requests>=2.31.0 | ffmpeg + fonts-dejavu-core
"""

import base64
import os
import random
import subprocess
import sys
import time

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
GEMINI_API_KEY = os.environ["GEMINI_API_KEY_STORY"]

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"
STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920

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

MAX_RETRIES = 4
RETRY_DELAY = 15
TIMEOUT = 60


# ──────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────
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


# ──────────────────────────────────────────────
# Génération du texte (Gemini — Projet A)
# ──────────────────────────────────────────────
def generer_texte_story() -> tuple[str, str, str]:
    """
    Génère une phrase courte via Gemini, alignée sur la niche Nyavo.
    Retourne (pilier, sujet, texte).
    """
    pilier = random.choices(
        PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1
    )[0]
    style_prompt = random.choice(STORY_PROMPTS)
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        f"Tu es Nyavo Channel, une chaîne tech qui révèle les mécanismes "
        f"cachés du monde numérique.\n\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\n"
        f"Format : {style_prompt}\n\n"
        f"Consignes :\n"
        f"- Écris UNE seule phrase en français (moins de 15 mots)\n"
        f"- Ton : {TON_EDITORIAL}\n"
        f"- Inclus au moins un terme technique précis\n"
        f"- Pas de guillemets, pas de titre, juste la phrase\n"
        f"- Interdit : généralités, banalités, hors-sujet\n"
    )

    try:
        print(f"  📝 Texte via Gemini [story]...")
        print(f"     Axe   : {PILLARS[pilier]['label']}")
        print(f"     Sujet : {sujet}")
        reponse = _requete_avec_retry(
            "POST",
            f"{GEMINI_TEXT_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json_data={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 50, "temperature": 0.9},
            },
            timeout=30,
        )

        texte = (
            reponse.json()["candidates"][0]["content"]["parts"][0]["text"]
            .strip()
            .strip('"')
            .split("\n")[0]
        )

        if not texte:
            raise ValueError("Réponse texte vide.")

        print(f"  ✅ Texte : « {texte} »")
        return pilier, sujet, texte

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        corps = e.response.text[:400] if e.response is not None else ""
        raise RuntimeError(f"Gemini texte [story] (HTTP {code}) : {corps}") from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Gemini texte [story] injoignable : {e}") from e


# ──────────────────────────────────────────────
# Génération de l'image (Gemini — Projet A)
# ──────────────────────────────────────────────
def generer_image_story(pilier: str, texte: str, chemin: str) -> None:
    """Génère une image verticale 9:16 liée au texte via Gemini."""
    prompt = (
        f"Illustration verticale 9:16 pour ce texte : « {texte} »\n"
        f"Axe : {PILLARS[pilier]['label']}\n"
        f"Style : {STYLE_IMAGE_SUFFIX}\n"
        f"L'image doit refléter visuellement le contenu du texte."
    )

    try:
        print("  🖼️  Image via Gemini [story]...")
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
            raise ValueError(f"Image suspecte ({taille} octets).")

        print(f"  ✅ Image : {chemin} ({taille:,} octets)")

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        corps = e.response.text[:400] if e.response is not None else ""
        raise RuntimeError(f"Gemini image [story] (HTTP {code}) : {corps}") from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Gemini image [story] injoignable : {e}") from e

    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Réponse Gemini image [story] invalide : {e}") from e


# ──────────────────────────────────────────────
# Incrustation du texte (ffmpeg)
# ──────────────────────────────────────────────
def incruster_texte(image_in: str, texte: str, image_out: str) -> None:
    """Superpose le texte (façon sticker) sur l'image via ffmpeg."""
    texte_ffmpeg = texte.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")
    filtre = (
        f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={STORY_WIDTH}:{STORY_HEIGHT},"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{texte_ffmpeg}':fontcolor=0x00E5FF:fontsize=58:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x0D0D0D@0.7:boxborderw=30:"
        "line_spacing=14"
    )

    try:
        print("  🎨 Incrustation texte via ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", image_out],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✅ Image finale : {image_out}")

    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:500]}") from e


# ──────────────────────────────────────────────
# Facebook Graph API
# ──────────────────────────────────────────────
def uploader_photo_non_publiee(image_path: str) -> str:
    """Upload une photo non publiée, retourne son photo_id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"

    try:
        print("  📤 Upload photo Facebook...")
        with open(image_path, "rb") as f:
            reponse = _requete_avec_retry(
                "POST",
                endpoint,
                data={"published": "false", "access_token": FB_PAGE_ACCESS_TOKEN},
                files={"source": (os.path.basename(image_path), f, "image/png")},
                timeout=TIMEOUT,
            )

        resultat = reponse.json()
        photo_id = resultat.get("id")
        if not photo_id:
            raise ValueError(f"Réponse FB inattendue : {resultat}")

        print(f"  ✅ Photo ID : {photo_id}")
        return photo_id

    except requests.exceptions.HTTPError as e:
        raise _erreur_facebook(e, "upload photo") from e
    except OSError as e:
        raise RuntimeError(f"Fichier illisible '{image_path}' : {e}") from e


def publier_story(photo_id: str) -> dict:
    """Publie la story à partir du photo_id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photo_stories"

    try:
        print("  🚀 Publication story...")
        reponse = _requete_avec_retry(
            "POST",
            endpoint,
            data={"photo_id": photo_id, "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=TIMEOUT,
        )

        resultat = reponse.json()
        if "id" not in resultat:
            raise ValueError(f"Réponse FB inattendue : {resultat}")

        print("  ✅ Story publiée !")
        return resultat

    except requests.exceptions.HTTPError as e:
        raise _erreur_facebook(e, "publication story") from e


# ──────────────────────────────────────────────
# Fonction principale
# ──────────────────────────────────────────────
def main() -> None:
    print("=" * 50)
    print("🎬 Nyavo Channel — Story [Projet Gemini A]")
    print("=" * 50)

    pilier, sujet, texte = generer_texte_story()
    print(f"\n📌 Axe    : {PILLARS[pilier]['label']}")
    print(f"📌 Sujet  : {sujet}")
    print(f"📌 Texte  : {texte}\n")

    generer_image_story(pilier, texte, "story_raw.png")
    incruster_texte("story_raw.png", texte, STORY_IMAGE_PATH)

    photo_id = uploader_photo_non_publiee(STORY_IMAGE_PATH)
    resultat = publier_story(photo_id)

    print(f"\n{'=' * 50}")
    print(f"✅ TERMINÉ — Story ID : {resultat.get('id', 'N/A')}")
    print(f"{'=' * 50}")


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