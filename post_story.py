#!/usr/bin/env python3
"""
Nyavo Channel — publication STORY (image courte, texte minimal).
⚠️ LIMITE API IMPORTANTE : l'API Graph ne permet PAS d'ajouter des
stickers interactifs (sondage, question, quiz) par automatisation — ces
éléments n'existent que dans l'app Facebook manuelle. Ce script publie
donc une image avec le fait/chiffre/question écrit directement dessus,
ce qui reproduit l'esprit de l'interactivité sans le sticker natif.

Secrets requis : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY
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
)

# ──────────────────────────────────────────────
# Variables d'environnement
# ──────────────────────────────────────────────
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

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
GEMINI_IMAGE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash-image:generateContent"
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
    """Requête HTTP avec retries (429 / 5xx / timeout)."""
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


# ──────────────────────────────────────────────
# Génération du texte (Gemini)
# ──────────────────────────────────────────────
def generer_texte_story() -> tuple[str, str]:
    """Génère une phrase courte via Gemini. Retourne (pilier, texte)."""
    pilier = random.choices(
        PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1
    )[0]
    style_prompt = random.choice(STORY_PROMPTS)

    prompt = (
        f"Écris {style_prompt}, en français, une seule phrase courte "
        f"(moins de 15 mots), sans guillemets, pour la catégorie "
        f"'{PILLARS[pilier]['label']}'."
    )

    try:
        print(f"  📝 Appel API texte Gemini (pilier : {PILLARS[pilier]['label']})...")
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

        print(f"  ✅ Texte généré : « {texte} »")
        return pilier, texte

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        corps = e.response.text[:400] if e.response is not None else ""
        raise RuntimeError(
            f"Erreur API texte Gemini (HTTP {code}) : {corps}"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API texte Gemini injoignable : {e}") from e


# ──────────────────────────────────────────────
# Génération de l'image (Gemini)
# ──────────────────────────────────────────────
def generer_image_story(pilier: str, chemin: str) -> None:
    """Génère une image verticale via Gemini et la sauvegarde en PNG."""
    prompt = f"{PILLARS[pilier]['label']}, {STYLE_IMAGE_SUFFIX}, vertical composition"

    try:
        print("  🖼️  Génération de l'image via Gemini...")
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
        image_b64 = resultat["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]

        with open(chemin, "wb") as f:
            f.write(base64.b64decode(image_b64))

        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(f"Image suspecte ({taille} octets).")

        print(f"  ✅ Image sauvegardée : {chemin} ({taille:,} octets)")

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        corps = e.response.text[:400] if e.response is not None else ""
        raise RuntimeError(
            f"Erreur API image Gemini (HTTP {code}) : {corps}"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API image Gemini injoignable : {e}") from e

    except (KeyError, IndexError) as e:
        raise RuntimeError(
            f"Réponse Gemini image inattendue (pas de données image) : {e}"
        ) from e


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
        print("  🎨 Incrustation du texte via ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", image_out],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✅ Image avec texte : {image_out}")

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
    """Upload une photo en mode non publié, retourne son photo_id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"

    try:
        print("  📤 Upload photo Facebook (non publiée)...")
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

        print(f"  ✅ Photo uploadée — ID : {photo_id}")
        return photo_id

    except requests.exceptions.HTTPError as e:
        corps = ""
        if e.response is not None:
            try:
                err = e.response.json().get("error", {})
                corps = f"[{err.get('type','?')}] {err.get('message','?')}"
            except Exception:
                corps = e.response.text[:300]
        raise RuntimeError(f"Facebook upload photo : {corps}") from e

    except OSError as e:
        raise RuntimeError(f"Fichier image illisible '{image_path}' : {e}") from e


def publier_story(photo_id: str) -> dict:
    """Publie la story à partir du photo_id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photo_stories"

    try:
        print("  🚀 Publication de la story...")
        reponse = _requete_avec_retry(
            "POST",
            endpoint,
            data={"photo_id": photo_id, "access_token": FB_PAGE_ACCESS_TOKEN},
            timeout=TIMEOUT,
        )

        resultat = reponse.json()
        if "id" not in resultat:
            raise ValueError(f"Réponse FB inattendue : {resultat}")

        print("  ✅ Story publiée avec succès !")
        return resultat

    except requests.exceptions.HTTPError as e:
        corps = ""
        if e.response is not None:
            try:
                err = e.response.json().get("error", {})
                corps = f"[{err.get('type','?')}] {err.get('message','?')}"
            except Exception:
                corps = e.response.text[:300]
        raise RuntimeError(f"Facebook publication story : {corps}") from e


# ──────────────────────────────────────────────
# Fonction principale
# ──────────────────────────────────────────────
def main() -> None:
    print("=" * 50)
    print("🎬 Nyavo Channel — Génération de Story")
    print("=" * 50)

    # Étape 1 : Texte
    pilier, texte = generer_texte_story()
    print(f"\n📌 Pilier : {PILLARS[pilier]['label']}")
    print(f"📌 Texte  : {texte}\n")

    # Étape 2 : Image
    generer_image_story(pilier, "story_raw.png")

    # Étape 3 : Incrustation texte
    incruster_texte("story_raw.png", texte, STORY_IMAGE_PATH)

    # Étape 4 : Upload + publication
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