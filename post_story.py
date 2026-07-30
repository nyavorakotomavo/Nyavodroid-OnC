#!/usr/bin/env python3
"""
Nyavo Channel — publication STORY (image courte, texte minimal).
⚠️ LIMITE API IMPORTANTE : l'API Graph ne permet PAS d'ajouter des
stickers interactifs (sondage, question, quiz) par automatisation — ces
éléments n'existent que dans l'app Facebook manuelle. Ce script publie
donc une image avec le fait/chiffre/question écrit directement dessus,
ce qui reproduit l'esprit de l'interactivité sans le sticker natif.

Secrets requis (GitHub Secrets) :
  - FB_PAGE_ID
  - FB_PAGE_ACCESS_TOKEN
  - POLLINATIONS_API_KEY

Dépendances (requirements.txt) :
  requests>=2.31.0

Dépendances système (ubuntu-latest) :
  ffmpeg
  fonts-dejavu-core
"""

import os
import random
import subprocess
import sys
import time
import urllib.parse

import requests

from content_config import (
    PILLAR_KEYS,
    PILLAR_WEIGHTS,
    PILLARS,
    STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX,
)

# ──────────────────────────────────────────────
# Variables d'environnement (GitHub Secrets)
# ──────────────────────────────────────────────
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_ACCESS_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
POLLINATIONS_API_KEY = os.environ["POLLINATIONS_API_KEY"]

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"  # Mis à jour : v21.0 → v25.0 (stable, exp. 07/2028)
STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920

# Endpoints Pollinations (nouveau base URL unifié)
POLLINATIONS_TEXT_URL = "https://text.pollinations.ai/"
POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/"

# Headers d'authentification Pollinations
POLLINATIONS_HEADERS = {
    "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
    "User-Agent": "NyavoChannel/1.0",
}

# Configuration des retries
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
REQUEST_TIMEOUT = 60


# ──────────────────────────────────────────────
# Fonctions utilitaires
# ──────────────────────────────────────────────
def _requete_avec_retry(
    methode: str,
    url: str,
    *,
    headers: dict | None = None,
    params: dict | None = None,
    data: dict | None = None,
    files: dict | None = None,
    timeout: int = REQUEST_TIMEOUT,
    stream: bool = False,
) -> requests.Response:
    """
    Effectue une requête HTTP avec retries automatiques et gestion d'erreurs.
    """
    derniere_erreur = None
    for tentative in range(1, MAX_RETRIES + 1):
        try:
            reponse = requests.request(
                method=methode,
                url=url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                timeout=timeout,
                stream=stream,
            )
            # Si 429 (rate limit) ou 5xx, on retry
            if reponse.status_code == 429 or reponse.status_code >= 500:
                attente = RETRY_DELAY_SECONDS * tentative
                print(
                    f"  ⚠️  HTTP {reponse.status_code} — nouvelle tentative "
                    f"dans {attente}s ({tentative}/{MAX_RETRIES})"
                )
                time.sleep(attente)
                derniere_erreur = requests.exceptions.HTTPError(
                    f"HTTP {reponse.status_code}", response=reponse
                )
                continue

            reponse.raise_for_status()
            return reponse

        except requests.exceptions.Timeout as e:
            derniere_erreur = e
            attente = RETRY_DELAY_SECONDS * tentative
            print(
                f"  ⚠️  Timeout — nouvelle tentative dans {attente}s "
                f"({tentative}/{MAX_RETRIES})"
            )
            time.sleep(attente)

        except requests.exceptions.ConnectionError as e:
            derniere_erreur = e
            attente = RETRY_DELAY_SECONDS * tentative
            print(
                f"  ⚠️  Erreur de connexion — nouvelle tentative dans {attente}s "
                f"({tentative}/{MAX_RETRIES})"
            )
            time.sleep(attente)

        except requests.exceptions.HTTPError:
            # Erreur 4xx (sauf 429) : pas de retry, on lève directement
            raise

    # Toutes les tentatives ont échoué
    raise derniere_erreur  # type: ignore[misc]


# ──────────────────────────────────────────────
# Génération du texte (Pollinations Text API)
# ──────────────────────────────────────────────
def generer_texte_story() -> tuple[str, str]:
    """
    Génère une phrase courte via l'API texte Pollinations.
    Retourne (pilier, texte).
    """
    pilier = random.choices(
        PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1
    )[0]
    style_prompt = random.choice(STORY_PROMPTS)

    prompt = (
        f"Écris {style_prompt}, en français, une seule phrase courte "
        f"(moins de 15 mots), sans guillemets, pour la catégorie "
        f"'{PILLARS[pilier]['label']}'."
    )

    url = POLLINATIONS_TEXT_URL + urllib.parse.quote(prompt)

    try:
        print(f"  📝 Appel API texte Pollinations (pilier : {PILLARS[pilier]['label']})...")
        reponse = _requete_avec_retry(
            "GET",
            url,
            headers=POLLINATIONS_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        texte = reponse.text.strip().strip('"').split("\n")[0]

        if not texte:
            raise ValueError("L'API texte a retourné une réponse vide.")

        print(f"  ✅ Texte généré : « {texte} »")
        return pilier, texte

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        corps = ""
        if e.response is not None:
            corps = e.response.text[:300]
        raise RuntimeError(
            f"Erreur API texte Pollinations (HTTP {code}) : {corps}"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Impossible de joindre l'API texte Pollinations : {e}"
        ) from e


# ──────────────────────────────────────────────
# Génération de l'image (Pollinations Image API)
# ──────────────────────────────────────────────
def generer_url_image_story(pilier: str) -> str:
    """
    Construit l'URL de génération d'image Pollinations avec authentification.
    """
    prompt = f"{PILLARS[pilier]['label']}, {STYLE_IMAGE_SUFFIX}, vertical composition"
    encoded = urllib.parse.quote(prompt)
    # La clé API est passée en query param pour les endpoints GET image
    return (
        f"{POLLINATIONS_IMAGE_URL}{encoded}"
        f"?width={STORY_WIDTH}&height={STORY_HEIGHT}"
        f"&nologo=true&key={POLLINATIONS_API_KEY}"
    )


def telecharger_image(url: str, chemin: str) -> None:
    """
    Télécharge l'image générée et la sauvegarde localement.
    """
    try:
        print(f"  🖼️  Téléchargement de l'image...")
        reponse = _requete_avec_retry(
            "GET",
            url,
            headers={"User-Agent": "NyavoChannel/1.0"},
            timeout=120,  # La génération d'image peut être lente
            stream=True,
        )

        with open(chemin, "wb") as f:
            for chunk in reponse.iter_content(chunk_size=8192):
                f.write(chunk)

        # Vérification que le fichier n'est pas vide
        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(
                f"L'image téléchargée est suspecte ({taille} octets). "
                f"L'API a peut-être retourné une erreur."
            )

        print(f"  ✅ Image sauvegardée : {chemin} ({taille} octets)")

    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else "N/A"
        raise RuntimeError(
            f"Erreur API image Pollinations (HTTP {code}). "
            f"Vérifiez la clé API et le quota."
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Impossible de télécharger l'image : {e}"
        ) from e

    except OSError as e:
        raise RuntimeError(
            f"Erreur d'écriture du fichier image '{chemin}' : {e}"
        ) from e


# ──────────────────────────────────────────────
# Incrustation du texte sur l'image (ffmpeg)
# ──────────────────────────────────────────────
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

    try:
        print(f"  🎨 Incrustation du texte via ffmpeg...")
        resultat = subprocess.run(
            [
                "ffmpeg",
                "-i", image_in,
                "-vf", filtre,
                "-frames:v", "1",
                "-y",
                image_out,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  ✅ Image avec texte : {image_out}")

    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg n'est pas installé. "
            "Installez-le : sudo apt-get install -y ffmpeg fonts-dejavu-core"
        )

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg a échoué (code {e.returncode}).\n"
            f"STDERR : {e.stderr[:500]}"
        ) from e


# ──────────────────────────────────────────────
# Facebook Graph API — Upload photo non publiée
# ──────────────────────────────────────────────
def uploader_photo_non_publiee(image_path: str) -> str:
    """Upload une photo en mode non publié, retourne son photo_id."""
    endpoint = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    )

    try:
        print(f"  📤 Upload de la photo vers Facebook (non publiée)...")
        with open(image_path, "rb") as f:
            files = {"source": (os.path.basename(image_path), f, "image/png")}
            data = {
                "published": "false",
                "access_token": FB_PAGE_ACCESS_TOKEN,
            }
            reponse = _requete_avec_retry(
                "POST",
                endpoint,
                data=data,
                files=files,
                timeout=REQUEST_TIMEOUT,
            )

        resultat = reponse.json()
        photo_id = resultat.get("id")

        if not photo_id:
            raise ValueError(
                f"Réponse Facebook inattendue (pas de 'id') : {resultat}"
            )

        print(f"  ✅ Photo uploadée — ID : {photo_id}")
        return photo_id

    except requests.exceptions.HTTPError as e:
        corps = ""
        if e.response is not None:
            try:
                corps = e.response.json().get("error", {}).get("message", "")
            except Exception:
                corps = e.response.text[:300]
        raise RuntimeError(
            f"Erreur Facebook Graph API (upload photo) : {corps}"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Impossible de joindre Facebook Graph API (upload) : {e}"
        ) from e

    except OSError as e:
        raise RuntimeError(
            f"Impossible de lire le fichier image '{image_path}' : {e}"
        ) from e


# ──────────────────────────────────────────────
# Facebook Graph API — Publication de la Story
# ──────────────────────────────────────────────
def publier_story(photo_id: str) -> dict:
    """Publie la story à partir du photo_id uploadé."""
    endpoint = (
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photo_stories"
    )
    payload = {
        "photo_id": photo_id,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }

    try:
        print(f"  🚀 Publication de la story Facebook...")
        reponse = _requete_avec_retry(
            "POST",
            endpoint,
            data=payload,
            timeout=REQUEST_TIMEOUT,
        )

        resultat = reponse.json()

        if "id" not in resultat:
            raise ValueError(
                f"Réponse Facebook inattendue (pas de 'id') : {resultat}"
            )

        print(f"  ✅ Story publiée avec succès !")
        return resultat

    except requests.exceptions.HTTPError as e:
        corps = ""
        code = "N/A"
        if e.response is not None:
            code = e.response.status_code
            try:
                erreur_fb = e.response.json().get("error", {})
                corps = (
                    f"[{erreur_fb.get('type', '?')}] "
                    f"{erreur_fb.get('message', 'Message inconnu')} "
                    f"(code {erreur_fb.get('code', '?')})"
                )
            except Exception:
                corps = e.response.text[:300]
        raise RuntimeError(
            f"Erreur Facebook Graph API (publication story, HTTP {code}) : {corps}"
        ) from e

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Impossible de joindre Facebook Graph API (story) : {e}"
        ) from e


# ──────────────────────────────────────────────
# Fonction principale
# ──────────────────────────────────────────────
def main() -> None:
    """Orchestre la création et la publication de la story."""
    print("=" * 50)
    print("🎬 Nyavo Channel — Génération de Story")
    print("=" * 50)

    # Étape 1 : Générer le texte
    pilier, texte = generer_texte_story()
    print(f"\n📌 Pilier : {PILLARS[pilier]['label']}")
    print(f"📌 Texte  : {texte}\n")

    # Étape 2 : Générer et télécharger l'image
    image_url = generer_url_image_story(pilier)
    telecharger_image(image_url, "story_raw.png")

    # Étape 3 : Incruster le texte sur l'image
    incruster_texte("story_raw.png", texte, STORY_IMAGE_PATH)

    # Étape 4 : Uploader la photo (non publiée)
    photo_id = uploader_photo_non_publiee(STORY_IMAGE_PATH)

    # Étape 5 : Publier la story
    resultat = publier_story(photo_id)

    print(f"\n{'=' * 50}")
    print(f"✅ TERMINÉ — Story ID : {resultat.get('id', 'N/A')}")
    print(f"{'=' * 50}")


# ──────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(
            f"\n❌ Variable d'environnement manquante : {e}. "
            f"Vérifiez vos GitHub Secrets.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
