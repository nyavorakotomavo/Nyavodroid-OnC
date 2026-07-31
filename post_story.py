#!/usr/bin/env python3
"""
Nyavo Channel — publication STORY (image courte, texte minimal).
Projet Gemini : nyavo-story (clé dédiée GEMINI_API_KEY_STORY)
Fallback image : Pollinations anonyme (si Gemini 429)
Secrets requis : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_STORY
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
GEMINI_API_KEY = _nettoyer_secret(os.environ["GEMINI_API_KEY_STORY"])

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"
STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920

# ✅ Modèle texte corrigé : gemini-2.5-flash-lite (remplace gemini-2.5-flash déprécié)
GEMINI_TEXT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash-lite:generateContent"
)
GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"

POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/"

MAX_RETRIES = 4
RETRY_DELAY = 30
TIMEOUT = 60


# ──────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────
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


def verifier_token_facebook() -> None:
    """Vérifie que le token FB a les bonnes permissions avant de continuer."""
    try:
        reponse = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/me",
            params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "id,name"},
            timeout=15,
        )
        if reponse.status_code != 200:
            err = reponse.json().get("error", {})
            raise RuntimeError(
                f"Token Facebook invalide ou expiré.\n"
                f"Erreur : {err.get('message', '?')}\n"
                f"Action : Régénérez un token système avec les permissions "
                f"pages_manage_posts, pages_read_engagement, publish_video."
            )
        info = reponse.json()
        print(f"  ✅ Token FB valide — Page : {info.get('name', '?')} (ID: {info.get('id', '?')})")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Impossible de vérifier le token Facebook : {e}") from e


# ──────────────────────────────────────────────
# Génération du texte (Gemini)
# ──────────────────────────────────────────────
def generer_texte_story() -> tuple[str, str, str]:
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
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
        f"- Pas de guillemets, pas de titre, pas de Markdown, juste la phrase\n"
        f"- Interdit : généralités, banalités, hors-sujet\n"
    )

    try:
        print(f"  📝 Texte via Gemini [story]...")
        print(f"     Axe   : {PILLARS[pilier]['label']}")
        print(f"     Sujet : {sujet}")
        reponse = _requete_avec_retry(
            "POST", f"{GEMINI_TEXT_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json_data={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 50, "temperature": 0.9},
            },
            timeout=30,
        )
        texte = reponse.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"').split("\n")[0]
        texte = _nettoyer_texte(texte)
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
# Génération image : Gemini → fallback Pollinations
# ──────────────────────────────────────────────
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
    url = f"{POLLINATIONS_IMAGE_URL}{encoded}?width={STORY_WIDTH}&height={STORY_HEIGHT}&nologo=true"
    reponse = _requete_avec_retry(
        "GET", url, headers={"User-Agent": "NyavoChannel/1.0"},
        timeout=120, stream=True,
    )
    with open(chemin, "wb") as f:
        for chunk in reponse.iter_content(chunk_size=8192):
            f.write(chunk)


def generer_image_story(pilier: str, texte: str, chemin: str) -> None:
    prompt = _nettoyer_texte(
        f"Illustration verticale 9:16 pour ce texte : {texte}\n"
        f"Axe : {PILLARS[pilier]['label']}\n"
        f"Style : {STYLE_IMAGE_SUFFIX}\n"
        f"L'image doit refléter visuellement le contenu du texte."
    )
    try:
        print("  🖼️  Image via Gemini [story]...")
        _image_gemini(prompt, chemin)
        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(f"Image suspecte ({taille} octets).")
        print(f"  ✅ Image Gemini : {chemin} ({taille:,} octets)")
        return
    except Exception as e:
        print(f"  ⚠️  Gemini image échec : {e}")

    try:
        print("  🖼️  Fallback image via Pollinations [story]...")
        _image_pollinations(prompt, chemin)
        taille = os.path.getsize(chemin)
        if taille < 1024:
            raise ValueError(f"Image Pollinations suspecte ({taille} octets).")
        print(f"  ✅ Image Pollinations : {chemin} ({taille:,} octets)")
    except Exception as e2:
        raise RuntimeError(f"Gemini ET Pollinations ont échoué.\nGemini : {e}\nPollinations : {e2}") from e2


# ──────────────────────────────────────────────
# Incrustation du texte (ffmpeg)
# ──────────────────────────────────────────────
def incruster_texte(image_in: str, texte: str, image_out: str) -> None:
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
            check=True, capture_output=True, text=True,
        )
        print(f"  ✅ Image finale : {image_out}")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:500]}") from e


# ──────────────────────────────────────────────
# Facebook Graph API
# ──────────────────────────────────────────────
def uploader_photo_non_publiee(image_path: str) -> str:
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photos"
    try:
        print("  📤 Upload photo Facebook...")
        with open(image_path, "rb") as f:
            reponse = _requete_avec_retry(
                "POST", endpoint,
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
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{FB_PAGE_ID}/photo_stories"
    try:
        print("  🚀 Publication story...")
        reponse = _requete_avec_retry(
            "POST", endpoint,
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

    verifier_token_facebook()

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