#!/usr/bin/env python3
"""
Nyavodroid — module média partagé (texte + image + audio).
Chaînes de fallback robustes, zéro duplication entre post_content / post_story.

  TEXTE : Mistral → Together (Mixtral) → Gemini (multi-modèles) → Hugging Face
  IMAGE : Gemini → Hugging Face → Together (FLUX) → Fal.ai → Cloudflare → Pollinations
         + Pexels pour les sujets non-tech
  AUDIO : Free.ai → Replicate (nateraw/musicgen) → Hugging Face (musicgen-small) → muet

Règle "fiable" : un 429 (quota) fait basculer IMMÉDIATEMENT au fournisseur suivant.
Seuls les 5xx / timeouts / coupures réseau sont retentés brièvement.
Les clés absentes = fournisseur sauté silencieusement.
"""

import base64
import os
import re
import subprocess
import time
import urllib.parse
import random
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

from content_config import (
    COLORS, BOX_BG, FONT_REGULAR_PATH, FONT_BOLD_PATH,
    get_font, wrap_text_pillow, MAX_TEXT_WIDTH_POST, MAX_TEXT_WIDTH_STORY,
    ACCROCHE_FONTSIZE, FAIT_CHOC_FONTSIZE, CONSEQUENCE_FONTSIZE, SOURCE_FONTSIZE,
    BOX_BORDER, LINE_SPACING, MARGIN, EMOJIS_DIR, PROFILE_IMAGE_PATH,
    EXPRESSIONS_DIR, CANVAS_SIZE_TEXTE_SEUL, BACKGROUND_GRADIENT,
    CANVAS_MARGIN_TEXTE_SEUL
)

# ──────────────────────────────────────────────
# Nettoyage
# ──────────────────────────────────────────────
def clean(v: str) -> str:
    return v.encode("ascii", "ignore").decode("ascii").strip()


def clean_text(t: str) -> str:
    t = re.sub(
        r'[\u200e\u200f\u200b\u200c\u200d\ufeff\u00ad\u2060\u180e\u202a-\u202e\u2066-\u2069]',
        '', t,
    )
    t = t.replace('**', '').replace('*', '')
    t = ''.join(c for c in t if c.isprintable() or c in '\n\t')
    return t.strip()


def sanitize_log(text: str) -> str:
    """Masque les clés API et tokens dans les logs pour éviter les fuites."""
    # Masquer key=... dans URLs
    text = re.sub(r'(key=)[A-Za-z0-9_-]+', r'\1***', text)
    # Masquer Bearer ...
    text = re.sub(r'(Bearer )[A-Za-z0-9_-]+', r'\1***', text)
    # Masquer Token ...
    text = re.sub(r'(Token )[A-Za-z0-9_-]+', r'\1***', text)
    # Masquer Authorization: ...
    text = re.sub(r'(Authorization: )[^\s]+', r'\1***', text)
    return text


# ──────────────────────────────────────────────
# Secrets
# ──────────────────────────────────────────────
FB_PAGE_ID = clean(os.environ.get("FB_PAGE_ID", ""))
FB_PAGE_ACCESS_TOKEN = clean(os.environ.get("FB_PAGE_ACCESS_TOKEN", ""))
MISTRAL_API_KEY = clean(os.environ.get("MISTRAL_API_KEY", ""))
TOGETHER_API_KEY = clean(os.environ.get("TOGETHER_API_KEY", ""))
HF_TOKEN = clean(os.environ.get("HF_TOKEN", ""))
REPLICATE_API_TOKEN = clean(os.environ.get("REPLICATE_API_TOKEN", ""))
FAL_API_KEY = clean(os.environ.get("FAL_API_KEY", ""))
CLOUDFLARE_ACCOUNT_ID = clean(os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""))
CLOUDFLARE_API_TOKEN = clean(os.environ.get("CLOUDFLARE_API_TOKEN", ""))
FREEAI_API_KEY = clean(os.environ.get("FREEAI_API_KEY", ""))
PEXELS_API_KEY = clean(os.environ.get("PEXELS_API_KEY", ""))
# ──────────────────────────────────────────────
# Cloudflare multi-comptes (round-robin + fallback)
# ──────────────────────────────────────────────
CLOUDFLARE_CREDS = []

# Compte principal
if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
    CLOUDFLARE_CREDS.append((CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN))

# Compte 2 (fallback)
cf_acc_2 = clean(os.environ.get("CLOUDFLARE_ACCOUNT_ID_2", ""))
cf_tok_2 = clean(os.environ.get("CLOUDFLARE_API_TOKEN_2", ""))
if cf_acc_2 and cf_tok_2:
    CLOUDFLARE_CREDS.append((cf_acc_2, cf_tok_2))

# Compte 3 (fallback)
cf_acc_3 = clean(os.environ.get("CLOUDFLARE_ACCOUNT_ID_3", ""))
cf_tok_3 = clean(os.environ.get("CLOUDFLARE_API_TOKEN_3", ""))
if cf_acc_3 and cf_tok_3:
    CLOUDFLARE_CREDS.append((cf_acc_3, cf_tok_3))

# Index round-robin pour alterner
# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"

MISTRAL_TEXT_URL = "https://api.mistral.ai/v1/chat/completions"
TOGETHER_TEXT_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_IMAGE_URL = "https://api.together.xyz/v1/images/generations"
HF_INFER_URL = "https://router.huggingface.co/hf-inference/models/"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent"
GEMINI_TEXT_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
FAL_IMAGE_URL = "https://fal.run/fal-ai/flux/dev"
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# Modèles texte
TOGETHER_TEXT_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TEXT_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"

# Modèles image (corrigés)
TOGETHER_IMAGE_MODEL = "black-forest-labs/FLUX.1-dev"
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
CLOUDFLARE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
CLOUDFLARE_NEGATIVE = "deformed, distorted geometry, broken perspective, disconnected edges, asymmetric cube"

# Modèles audio
REPLICATE_AUDIO_MODEL = "nateraw/musicgen"
HF_AUDIO_MODEL = "facebook/musicgen-small"
FREEAI_MUSIC_URL = "https://api.free.ai/v1/music/generate/"

# Dimensions
DEFAULT_IMG_SIZE = (1024, 1792)
POLL_W, POLL_H = 1080, 1920
AUDIO_SECONDS = 11

# Modèles texte Gemini essayés dans l'ordre
GEMINI_TEXT_MODELS = ["gemini-flash-latest", "gemini-pro-latest", "gemini-2.5-pro", "gemini-2.5-flash"]
# Cascade de modèles Gemini image (si le premier échoue)
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.0-flash-exp", "gemini-1.5-flash"]

TIMEOUT = 60

# ──────────────────────────────────────────────
#  REQUÊTE HTTP
# ──────────────────────────────────────────────
def _req(
    method: str, url: str, *,
    headers: dict | None = None, json_data: dict | None = None,
    data: dict | None = None, files: dict | None = None,
    timeout: int = TIMEOUT, stream: bool = False,
    max_retries: int = 2, retry_delay: int = 6,
) -> requests.Response:
    derniere: Exception | None = None
    for tentative in range(1, max_retries + 1):
        try:
            r = requests.request(
                method=method, url=url, headers=headers,
                json=json_data, data=data, files=files,
                timeout=timeout, stream=stream,
            )
            if r.status_code == 429:
                r.raise_for_status()
            if r.status_code >= 500:
                derniere = requests.exceptions.HTTPError(f"HTTP {r.status_code}", response=r)
                print(f"    ↻ {r.status_code} — retry {tentative}/{max_retries} dans {retry_delay}s")
                time.sleep(retry_delay)
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.Timeout as e:
            derniere = e
            print(f"    ↻ timeout — retry {tentative}/{max_retries}")
            time.sleep(retry_delay)
        except requests.exceptions.ConnectionError as e:
            derniere = e
            print(f"    ↻ connexion — retry {tentative}/{max_retries}")
            time.sleep(retry_delay)
    raise derniere  # type: ignore[misc]


# ──────────────────────────────────────────────
#  FACEBOOK
# ──────────────────────────────────────────────
def fb_error(e: requests.exceptions.HTTPError, ctx: str) -> RuntimeError:
    corps, code = "", "N/A"
    if e.response is not None:
        code = e.response.status_code
        try:
            err = e.response.json().get("error", {})
            corps = f"[{err.get('type','?')}] {err.get('message','?')} (code {err.get('code','?')})"
        except Exception:
            corps = e.response.text[:400]
    if corps == "[?] ? (code ?)" or corps.startswith("[?]"):
        corps = f"Réponse brute : {e.response.text[:400]}"
    return RuntimeError(f"Facebook Graph ({ctx}, HTTP {code}) : {corps}")

def verify_fb_token() -> None:
    try:
        r = requests.get(
            f"https://graph.facebook.com/{GRAPH_API_VERSION}/me",
            params={"access_token": FB_PAGE_ACCESS_TOKEN, "fields": "id,name"},
            timeout=15,
        )
        if r.status_code != 200:
            err = r.json().get("error", {})
            raise RuntimeError(
                f"Token Facebook invalide/expiré : {err.get('message','?')}\n"
                f"Vérifiez FB_PAGE_ID={FB_PAGE_ID} et le token Page."
            )
        info = r.json()
        print(f"  ✅ Token FB valide — Page : {info.get('name','?')} (ID: {info.get('id','?')})")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Impossible de vérifier le token Facebook : {e}") from e
# ──────────────────────────────────────────────
#  TEXTE — fournisseurs
# ──────────────────────────────────────────────
def _t_mistral(prompt: str) -> str:
    r = _req(
        "POST", MISTRAL_TEXT_URL,
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json_data={"model": "mistral-small-latest",
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 500, "temperature": 0.4},
        timeout=30,
    )
    return clean_text(r.json()["choices"][0]["message"]["content"])


def _t_together(prompt: str) -> str:
    r = _req(
        "POST", TOGETHER_TEXT_URL,
        headers={"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"},
        json_data={"model": TOGETHER_TEXT_MODEL,
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 500, "temperature": 0.4},
        timeout=30,
    )
    return clean_text(r.json()["choices"][0]["message"]["content"])


def _t_gemini(prompt: str, gemini_key: str) -> str:
    derniere: Exception | None = None
    for modele in GEMINI_TEXT_MODELS:
        url = f"{GEMINI_TEXT_BASE}{modele}:generateContent?key={gemini_key}"
        try:
            r = _req(
                "POST", url, headers={"Content-Type": "application/json"},
                json_data={"contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {"maxOutputTokens": 500, "temperature": 0.4}},
                timeout=30,
            )
            data = r.json()
            cands = data.get("candidates") or []
            if not cands:
                raise ValueError(f"pas de candidates")
            parts = cands[0].get("content", {}).get("parts") or []
            fin = cands[0].get("finishReason", "")
            if not parts or fin in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                raise ValueError(f"réponse vide/bloquée (finish={fin})")
            txt = parts[0].get("text", "")
            if not txt:
                raise ValueError("texte vide")
            return clean_text(txt)
        except Exception as e:
            derniere = e
            print(f"    ⚠️ Gemini {modele} : {sanitize_log(str(e))}")
            continue
    raise RuntimeError(f"Gemini texte KO (tous modèles) : {sanitize_log(str(derniere))}")


def _t_hf(prompt: str) -> str:
    body = {"inputs": prompt,
            "parameters": {"max_new_tokens": 500, "temperature": 0.4, "return_full_text": False}}
    if "instruct" in HF_TEXT_MODEL.lower():
        body["inputs"] = f"[INST] {prompt} [/INST]"
    r = _req(
        "POST", f"{HF_INFER_URL}{HF_TEXT_MODEL}",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json_data=body, timeout=60, max_retries=2, retry_delay=8,
    )
    j = r.json()
    txt = j[0]["generated_text"] if isinstance(j, list) else j.get("generated_text", "")
    if "[/INST]" in txt:
        txt = txt.split("[/INST]", 1)[1]
    txt = clean_text(txt)
    if not txt:
        raise ValueError("texte HF vide")
    return txt


def texte_avec_fallback(prompt: str, gemini_key: str, tag: str = "") -> str:
    if MISTRAL_API_KEY:
        try:
            print(f"  📝 Texte via Mistral {tag}...")
            return _t_mistral(prompt)
        except Exception as e:
            print(f"    ⚠️ Mistral : {e}")
    if TOGETHER_API_KEY:
        try:
            print(f"  📝 Texte via Together {tag}...")
            return _t_together(prompt)
        except Exception as e:
            print(f"    ⚠️ Together : {e}")
    try:
        print(f"  📝 Texte via Gemini {tag}...")
        return _t_gemini(prompt, gemini_key)
    except Exception as e:
        print(f"    ⚠️ Gemini : {e}")
    if HF_TOKEN:
        try:
            print(f"  📝 Texte via Hugging Face {tag}...")
            return _t_hf(prompt)
        except Exception as e:
            print(f"    ⚠️ Hugging Face : {e}")
    raise RuntimeError("Texte impossible : tous les fournisseurs ont échoué.")

# ══════════════════════════════════════════════
#  IMAGE — fournisseurs (Gemini cascade, HF corrigé, Cloudflare neg prompt, Pexels)
# ══════════════════════════════════════════════
def _extract_b64(res: dict) -> str:
    if "output_image" in res:
        oi = res["output_image"]
        if isinstance(oi, dict) and "data" in oi:
            return oi["data"]
        if isinstance(oi, str):
            return oi
    if "output" in res:
        for it in res["output"]:
            if isinstance(it, dict):
                if it.get("type") == "image" and "data" in it:
                    return it["data"]
                if "inlineData" in it:
                    return it["inlineData"]["data"]
                if "inline_data" in it:
                    return it["inline_data"]["data"]
    if "candidates" in res:
        for p in res["candidates"][0]["content"]["parts"]:
            if "inlineData" in p:
                return p["inlineData"]["data"]
            if "inline_data" in p:
                return p["inline_data"]["data"]
    raise ValueError(f"image Gemini introuvable. Clés : {list(res.keys())}")


def _i_gemini(prompt: str, chemin: str, gemini_key: str, size: tuple[int, int]) -> None:
    """Essaie plusieurs modèles Gemini image en cascade (429 / erreur = suivant)."""
    derniere = None
    for modele in GEMINI_IMAGE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent?key={gemini_key}"
        try:
            r = _req(
                "POST", url,
                headers={"Content-Type": "application/json"},
                json_data={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
                },
                timeout=120,
            )
            data = r.json()
            if "candidates" in data:
                for part in data["candidates"][0]["content"]["parts"]:
                    if "inlineData" in part:
                        b64 = part["inlineData"]["data"]
                        break
                else:
                    raise ValueError("pas de partie image")
            else:
                raise ValueError(f"réponse inattendue : {data}")
            with open(chemin, "wb") as f:
                f.write(base64.b64decode(b64))
            return
        except Exception as e:
            derniere = e
            print(f"    ⚠️ Gemini {modele} : {sanitize_log(str(e))}")
            continue
    raise RuntimeError(f"Gemini image KO (tous modèles) : {sanitize_log(str(derniere))}")
def _i_hf(prompt: str, chemin: str, size: tuple[int, int]) -> None:
    w, h = size
    r = _req(
        "POST", f"{HF_INFER_URL}{HF_IMAGE_MODEL}",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json_data={"inputs": prompt, "parameters": {"width": w, "height": h}},
        timeout=120, max_retries=2, retry_delay=8,
    )
    ct = r.headers.get("Content-Type", "")
    if "image" not in ct:
        raise ValueError(f"réponse non-image ({ct}) : {r.text[:200]}")
    with open(chemin, "wb") as f:
        f.write(r.content)


def _i_together(prompt: str, chemin: str, size: tuple[int, int]) -> None:
    w, h = size
    r = _req(
        "POST", TOGETHER_IMAGE_URL,
        headers={"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"},
        json_data={"model": TOGETHER_IMAGE_MODEL, "prompt": prompt,
                   "width": w, "height": h, "n": 1, "response_format": "b64_json"},
        timeout=120,
    )
    b64 = r.json()["data"][0]["b64_json"]
    with open(chemin, "wb") as f:
        f.write(base64.b64decode(b64))


def _i_fal(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", FAL_IMAGE_URL,
        headers={"Authorization": f"Key {FAL_API_KEY}", "Content-Type": "application/json"},
        json_data={
            "prompt": prompt,
            "image_size": "square_hd",
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": False,
        },
        timeout=120,
    )
    data = r.json()
    img_url = data.get("images", [None])[0]
    if not img_url or not img_url.get("url"):
        raise ValueError(f"Fal.ai réponse invalide : {data}")
    img_data = requests.get(img_url["url"], timeout=60).content
    with open(chemin, "wb") as f:
        f.write(img_data)


def _i_cloudflare(prompt: str, chemin: str) -> None:
    """Image Cloudflare : lit les comptes elle-même + round-robin + bascule si 429."""
    creds = []
    for suffix in ("", "_2", "_3"):
        acc = clean(os.environ.get(f"CLOUDFLARE_ACCOUNT_ID{suffix}", ""))
        tok = clean(os.environ.get(f"CLOUDFLARE_API_TOKEN{suffix}", ""))
        if acc and tok:
            creds.append((acc, tok))
    if not creds:
        raise ValueError("Aucun identifiant Cloudflare configuré")

    if not hasattr(_i_cloudflare, "idx"):
        _i_cloudflare.idx = 0
    n = len(creds)
    derniere = None

    for i in range(n):
        idx = (_i_cloudflare.idx + i) % n
        acc, tok = creds[idx]
        url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{CLOUDFLARE_MODEL}"
        try:
            r = _req(
                "POST", url,
                headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                json_data={
                    "prompt": prompt,
                    "num_steps": 4,
                    "negative_prompt": "no text, no letters, no numbers, no typography, no watermark, no logo, no captions",
                },
                timeout=60,
                max_retries=1,
            )
            data = r.json()
            if not data.get("success"):
                raise ValueError(f"Cloudflare erreur : {data}")
            b64 = data.get("result", {}).get("image")
            if not b64:
                raise ValueError(f"Cloudflare pas d'image : {data}")
            with open(chemin, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"    ☁️ Cloudflare compte #{idx + 1}/{n} OK")
            _i_cloudflare.idx = (idx + 1) % n
            return
        except Exception as e:
            derniere = e
            print(f"    ⚠️ Cloudflare compte #{idx + 1}/{n} : {sanitize_log(str(e))} → compte suivant")
            continue

    _i_cloudflare.idx = (_i_cloudflare.idx + 1) % n
    raise RuntimeError(f"Cloudflare KO (tous comptes) : {sanitize_log(str(derniere))}")

def _i_pollinations(prompt: str, chemin: str) -> None:
    encoded = urllib.parse.quote(prompt, safe='')
    url = f"{POLLINATIONS_URL}{encoded}?width={POLL_W}&height={POLL_H}&nologo=true&enhance=true"
    r = _req("GET", url, headers={"User-Agent": "Nyavodroid/1.0"}, timeout=120, stream=True)
    with open(chemin, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


# ══════════════════════════════════════════════
#  PEXELS — recherche de photos réelles
# ══════════════════════════════════════════════
def search_pexels(query: str, orientation: str = "portrait", per_page: int = 5) -> list[dict]:
    if not PEXELS_API_KEY:
        return []
    try:
        r = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": orientation, "per_page": per_page},
            timeout=15,
        )
        if r.status_code != 200:
            print(f"    ⚠️ Pexels erreur {r.status_code} : {r.text[:200]}")
            return []
        data = r.json()
        return data.get("photos", [])
    except Exception as e:
        print(f"    ⚠️ Pexels exception : {e}")
        return []


def download_pexels_image(photo: dict, chemin: str, size: tuple[int, int] | None = None) -> bool:
    try:
        img_url = photo["src"]["original"]
        r = requests.get(img_url, timeout=30)
        if r.status_code != 200:
            return False
        with open(chemin, "wb") as f:
            f.write(r.content)
        if size:
            crop_to_ratio(chemin, chemin, target_size=size)
        return True
    except Exception as e:
        print(f"    ⚠️ Pexels download : {e}")
        return False


def _clean_pexels_query(query: str) -> str:
    """Extrait les mots concrets pour Pexels (vire les mots vides français)."""
    stop = {"comment", "pourquoi", "les", "des", "une", "un", "le", "la", "de", "du", "en", "et",
            "au", "aux", "sur", "secrets", "fonctionnement", "coulisses", "explique", "simplement",
            "vraiment", "reellement", "fonctionne", "marche", "quel", "quelle", "est", "sont",
            "ou", "on", "qu", "l", "d", "s", "cache", "mecanismes", "vrai", "duel", "ou", "en"}
    mots = re.findall(r"[\w]+", query, flags=re.UNICODE)
    kept = [m for m in mots if m.lower() not in stop and len(m) > 2]
    return " ".join(kept[:4]) or query

def get_image_from_pexels(query: str, chemin: str, size: tuple[int, int] | None = None) -> bool:
    for q in dict.fromkeys([query, _clean_pexels_query(query)]):
        photos = search_pexels(q)
        for photo in photos:
            if download_pexels_image(photo, chemin, size):
                print(f"    ✅ Pexels OK (requête : {q})")
                return True
    return False
# ══════════════════════════════════════════════
#  CROP vers un ratio cible
# ══════════════════════════════════════════════
def crop_to_ratio(input_path: str, output_path: str, target_size: tuple[int, int]) -> None:
    w_target, h_target = target_size
    filtre = (
        f"scale={w_target}:{h_target}:force_original_aspect_ratio=increase,"
        f"crop={w_target}:{h_target}"
    )
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-vf", filtre, "-frames:v", "1", "-y", output_path],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        raise RuntimeError("ffmpeg absent.")


def _check_img(chemin: str, expected_size: tuple[int, int] | None = None) -> None:
    taille = os.path.getsize(chemin)
    if taille < 1024:
        raise ValueError(f"image suspecte ({taille} octets)")
    if expected_size:
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0", chemin
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, check=True)
            w, h = out.stdout.strip().split(",")
            w, h = int(w), int(h)
            ratio_obtenu = w / h
            ratio_attendu = expected_size[0] / expected_size[1]
            if abs(ratio_obtenu - ratio_attendu) > 0.05:
                print(f"    ⚠️ Ratio image {w}x{h} (attendu {expected_size[0]}x{expected_size[1]}), possible déformation.")
        except Exception:
            pass


# ══════════════════════════════════════════════
#  FALLBACK PRINCIPAL — avec choix IA vs Pexels
# ══════════════════════════════════════════════
def image_avec_fallback(prompt: str, gemini_key: str, chemin: str,
                        size: tuple[int, int] | None = None,
                        use_pexels: bool = False, pexels_query: str = "") -> None:
    if size is None:
        size = DEFAULT_IMG_SIZE

    prompt = clean_text(prompt) + (
        ", high quality, sharp focus, photorealistic, "
        "ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, NO TYPOGRAPHY, NO CAPTIONS, NO LABELS, NO WATERMARKS, "
        "NO FAKE TEXT, NO GIBBERISH TEXT, NO CODE SNIPPETS, NO UI ELEMENTS WITH TEXT. "
        "If the concept involves language/code/translation, show abstract visual metaphors ONLY "
        "(glowing nodes, light beams, flowing data streams, neural networks) — NEVER render any characters or symbols."
    )
    erreurs = []
    tentatives = 0

    if use_pexels and pexels_query:
        print(f"    🖼️ Pexels (recherche : {pexels_query})...")
        if get_image_from_pexels(pexels_query, chemin, size):
            _check_img(chemin, size)
            print(f"    ✅ Image Pexels ({os.path.getsize(chemin):,} o)")
            return
        else:
            print("    ⚠️ Pexels échoué, fallback IA.")

    # 1. Gemini (cascade)
    try:
        tentatives += 1
        print("    🖼️ Gemini image...")
        _i_gemini(prompt, chemin, gemini_key, size)
        _check_img(chemin, size)
        print(f"    ✅ Image Gemini ({os.path.getsize(chemin):,} o)")
        print(f"    📊 Fournisseur utilisé : Gemini après {tentatives} tentative(s)")
        return
    except Exception as e:
        erreurs.append(f"Gemini={e}"); print(f"    ⚠️ Gemini image : {e}")

    # 2. Cloudflare (multi-comptes round-robin)
    if CLOUDFLARE_CREDS:
        try:
            tentatives += 1
            print("    🖼️ Cloudflare image (carré → crop)...")
            raw = chemin + ".raw.png"
            _i_cloudflare(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Cloudflare ({os.path.getsize(chemin):,} o)")
            print(f"    📊 Fournisseur utilisé : Cloudflare après {tentatives} tentative(s)")
            return
        except Exception as e:
            erreurs.append(f"Cloudflare={e}"); print(f"    ⚠️ Cloudflare : {e}")

    # 3. Hugging Face
    if HF_TOKEN:
        try:
            tentatives += 1
            print("    🖼️ Hugging Face image...")
            _i_hf(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image HF ({os.path.getsize(chemin):,} o)")
            print(f"    📊 Fournisseur utilisé : Hugging Face après {tentatives} tentative(s)")
            return
        except Exception as e:
            erreurs.append(f"HF={e}"); print(f"    ⚠️ HF image : {e}")

    # 4. Together
    if TOGETHER_API_KEY:
        try:
            tentatives += 1
            print("    🖼️ Together image...")
            _i_together(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image Together ({os.path.getsize(chemin):,} o)")
            print(f"    📊 Fournisseur utilisé : Together après {tentatives} tentative(s)")
            return
        except Exception as e:
            erreurs.append(f"Together={e}"); print(f"    ⚠️ Together : {e}")

    # 5. Fal.ai
    if FAL_API_KEY:
        try:
            tentatives += 1
            print("    🖼️ Fal.ai image (carré → crop)...")
            raw = chemin + ".raw.png"
            _i_fal(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Fal.ai ({os.path.getsize(chemin):,} o)")
            print(f"    📊 Fournisseur utilisé : Fal.ai après {tentatives} tentative(s)")
            return
        except Exception as e:
            erreurs.append(f"Fal.ai={e}"); print(f"    ⚠️ Fal.ai : {e}")

    # 6. Pollinations
    try:
        tentatives += 1
        print("    🖼️ Pollinations image (dernier recours)...")
        _i_pollinations(prompt, chemin)
        _check_img(chemin)
        print(f"    ✅ Image Pollinations ({os.path.getsize(chemin):,} o)")
        print(f"    📊 Fournisseur utilisé : Pollinations après {tentatives} tentative(s)")
        return
    except Exception as e:
        erreurs.append(f"Pollinations={e}"); print(f"    ⚠️ Pollinations image : {e}")

    raise RuntimeError("Image impossible (tous fournisseurs KO) :\n  " + "\n  ".join(erreurs))

# ══════════════════════════════════════════════
#  AUDIO — fournisseurs (Free.ai, Replicate, HF)
# ══════════════════════════════════════════════
def _a_freeai(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", FREEAI_MUSIC_URL,
        headers={"Authorization": f"Bearer {FREEAI_API_KEY}", "Content-Type": "application/json"},
        json_data={"prompt": prompt, "duration": AUDIO_SECONDS},
        timeout=60,
    )
    data = r.json()
    audio_url = data.get("audio_url")
    if not audio_url:
        raise ValueError(f"Free.ai pas d'URL audio : {data}")
    audio = requests.get(audio_url, timeout=60).content
    with open(chemin, "wb") as f:
        f.write(audio)


def _a_replicate(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", f"https://api.replicate.com/v1/models/{REPLICATE_AUDIO_MODEL}/predictions",
        headers={"Authorization": f"Token {REPLICATE_API_TOKEN}", "Content-Type": "application/json"},
        json_data={"input": {"prompt": prompt, "duration": AUDIO_SECONDS}},
        timeout=30,
    )
    pred = r.json()
    get_url = pred.get("urls", {}).get("get")
    if not get_url:
        raise ValueError(f"pas d'url de polling : {pred}")
    out_url = None
    for _ in range(40):
        time.sleep(3)
        s = requests.get(get_url, headers={"Authorization": f"Token {REPLICATE_API_TOKEN}"}, timeout=20).json()
        st = s.get("status")
        if st == "succeeded":
            out = s.get("output")
            out_url = out[0] if isinstance(out, list) else out
            break
        if st in ("failed", "canceled"):
            raise ValueError(f"Replicate {st} : {s.get('error')}")
    if not out_url:
        raise ValueError("Replicate : timeout polling")
    audio = requests.get(out_url, timeout=60).content
    with open(chemin, "wb") as f:
        f.write(audio)


def _a_hf(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", f"{HF_INFER_URL}{HF_AUDIO_MODEL}",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json_data={"inputs": prompt},
        timeout=120, max_retries=2, retry_delay=8,
    )
    ct = r.headers.get("Content-Type", "")
    if "audio" not in ct:
        raise ValueError(f"réponse non-audio ({ct}) : {r.text[:200]}")
    with open(chemin, "wb") as f:
        f.write(r.content)


def audio_avec_fallback(prompt: str, chemin: str) -> bool:
    if FREEAI_API_KEY:
        try:
            print("    🎵 Audio via Free.ai...")
            _a_freeai(prompt, chemin)
            print(f"    ✅ Audio Free.ai ({os.path.getsize(chemin):,} o)")
            return True
        except Exception as e:
            print(f"    ⚠️ Free.ai : {e}")
    if REPLICATE_API_TOKEN:
        try:
            print("    🎵 Audio via Replicate...")
            _a_replicate(prompt, chemin)
            print(f"    ✅ Audio Replicate ({os.path.getsize(chemin):,} o)")
            return True
        except Exception as e:
            print(f"    ⚠️ Replicate audio : {e}")
    if HF_TOKEN:
        try:
            print("    🎵 Audio via Hugging Face...")
            _a_hf(prompt, chemin)
            print(f"    ✅ Audio HF ({os.path.getsize(chemin):,} o)")
            return True
        except Exception as e:
            print(f"    ⚠️ HF audio : {e}")
    print("    🔇 Aucun audio généré → Reel sans son.")
    return False


# ══════════════════════════════════════════════
#  WATERMARK DOUBLE (expression + photo profil)
# ══════════════════════════════════════════════
def overlay_watermark(image_in: str, image_out: str, source_text: str = "") -> None:
    """Expression aléatoire en bas à droite (hors zone UI). Logo géré par _apply_logo."""
    temp = image_out + ".tmp.png"
    inputs = ["-i", image_in]
    filter_parts = []
    main_stream = "[0:v]"

    if os.path.isdir(EXPRESSIONS_DIR):
        emos = [f for f in os.listdir(EXPRESSIONS_DIR) if f.lower().endswith('.png')]
        if emos:
            emo_path = os.path.join(EXPRESSIONS_DIR, random.choice(emos))
            inputs += ["-i", emo_path]
            try:
                cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                       "-show_entries", "stream=width,height", "-of", "csv=p=0", emo_path]
                out = subprocess.run(cmd, capture_output=True, text=True, check=True)
                w_emo, h_emo = map(int, out.stdout.strip().split(','))
            except Exception:
                w_emo, h_emo = 100, 100
            max_dim = 120
            if w_emo > h_emo:
                new_w, new_h = max_dim, int(h_emo * max_dim / w_emo)
            else:
                new_h, new_w = max_dim, int(w_emo * max_dim / h_emo)
            filter_parts.append(f"[1:v]scale={new_w}:{new_h},format=rgba[emo]")
            filter_parts.append(f"{main_stream}[emo]overlay=main_w-{new_w}-40:main_h-{new_h}-{BOT_SAFE}[tmp2]")
            main_stream = "[tmp2]"

    if source_text:
        src_clean = source_text.replace("'", "'\\\\''")
        filter_parts.append(
            f"{main_stream}drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{src_clean}':fontcolor=0xCCCCCC:fontsize=22:x=40:y=main_h-{BOT_SAFE}[tmp3]"
        )
        main_stream = "[tmp3]"

    filter_parts.append(f"{main_stream}null[out]")
    try:
        subprocess.run(
            ["ffmpeg", *inputs, "-filter_complex", ";".join(filter_parts),
             "-map", "[out]", "-frames:v", "1", "-y", temp],
            check=True, capture_output=True, text=True
        )
        os.replace(temp, image_out)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg watermark échec : {e.stderr[:500]}")
# ══════════════════════════════════════════════
#  FOND PILLOW POUR POST TEXTE SEUL
# ══════════════════════════════════════════════
def generer_fond_texte_seul(texte: str, chemin: str) -> None:
    """Génère une image carrée 1080x1080 avec dégradé violet et texte centré (marges réelles)."""
    w, h = CANVAS_SIZE_TEXTE_SEUL
    c1 = BACKGROUND_GRADIENT[0]  # violet profond
    c2 = BACKGROUND_GRADIENT[2]  # bleu nuit

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    for y in range(h):
        t = y / h
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Wrap mesuré + réduction auto de la police → zéro débordement
    max_width = w - 2 * CANVAS_MARGIN_TEXTE_SEUL
    texte_propre = clean_text(texte)
    font_size = 54
    lines = [texte_propre]
    font = get_font(font_size, bold=True)
    line_stride = 0
    total_h = 0
    while font_size >= 30:
        font = get_font(font_size, bold=True)
        lines = wrap_text_pillow(texte_propre, font, max_width)
        ascent, descent = font.getmetrics()
        line_stride = (ascent + descent) + 12
        total_h = (ascent + descent) * len(lines) + 12 * (len(lines) - 1)
        if total_h <= h - 2 * CANVAS_MARGIN_TEXTE_SEUL:
            break
        font_size -= 4

    y = (h - total_h) // 2
    for ln in lines:
        ln_w = draw.textlength(ln, font=font)
        x = (w - ln_w) // 2
        draw.text((x, y), ln, font=font, fill=COLORS["blanc"])
        y += line_stride

    img.save(chemin)


# ══════════════════════════════════════════════
#  RENDU TEXTE PILLOW — gestion des emojis
# ══════════════════════════════════════════════
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+"
)


def _split_emojis(s: str) -> list:
    """Découpe une chaîne en segments ('text', ...) et ('emoji', ...)."""
    segments = []
    last = 0
    for m in EMOJI_PATTERN.finditer(s):
        if m.start() > last:
            segments.append(("text", s[last:m.start()]))
        segments.append(("emoji", m.group()))
        last = m.end()
    if last < len(s):
        segments.append(("text", s[last:]))
    return segments


def _get_emoji_path(emoji_char: str) -> str | None:
    """Retourne le chemin du PNG correspondant à l'emoji, ou None si absent."""
    if not os.path.isdir(EMOJIS_DIR):
        return None
    candidate = emoji_char + ".png"
    path = os.path.join(EMOJIS_DIR, candidate)
    if os.path.isfile(path):
        return path
    # Séquence multi-codepoints : on tente avec le premier codepoint
    if len(emoji_char) > 1:
        path2 = os.path.join(EMOJIS_DIR, emoji_char[0] + ".png")
        if os.path.isfile(path2):
            return path2
    return None


def _render_line_with_emojis(img, draw, x_center: float, y: float, line: str,
                             font, fill, line_height: int) -> None:
    """Dessine une ligne centrée en remplaçant les emojis par leurs PNG (sinon retirés)."""
    segments = _split_emojis(line)
    ascent, descent = font.getmetrics()
    text_h = ascent + descent
    emo_size = int(text_h * 0.95)

    # Largeur totale pour centrer la ligne
    total_w = 0.0
    for kind, val in segments:
        if kind == "text":
            total_w += draw.textlength(val, font=font)
        else:
            total_w += emo_size + 4

    x = x_center - total_w / 2
    for kind, val in segments:
        if kind == "text":
            draw.text((x, y), val, font=font, fill=fill)
            x += draw.textlength(val, font=font)
        else:
            emo_path = _get_emoji_path(val)
            if emo_path:
                try:
                    emo_img = Image.open(emo_path).convert("RGBA")
                    emo_img = emo_img.resize((emo_size, emo_size), Image.LANCZOS)
                    y_emoji = y + (text_h - emo_size) // 2
                    img.paste(emo_img, (int(x), int(y_emoji)), emo_img)
                except Exception:
                    pass
            x += emo_size + 4


def draw_text_block(img, draw, lines: list, font, x_center: float, y: float,
                    text_color, box_color=None, padding: int = BOX_BORDER) -> int:
    """Dessine un bloc de texte (boîte optionnelle + lignes) et retourne la hauteur consommée."""
    if not lines:
        return 0
    ascent, descent = font.getmetrics()
    text_line_h = ascent + descent
    line_stride = text_line_h + LINE_SPACING

    widths = [draw.textlength(ln, font=font) for ln in lines]
    max_w = max(widths)
    total_h = text_line_h * len(lines) + LINE_SPACING * (len(lines) - 1)

    if box_color is not None:
        bx1 = x_center - max_w / 2 - padding
        by1 = y - padding
        bx2 = x_center + max_w / 2 + padding
        by2 = y + total_h + padding
        draw.rectangle([bx1, by1, bx2, by2], fill=box_color)

    cy = y
    for ln in lines:
        _render_line_with_emojis(img, draw, x_center, cy, ln, font, text_color, text_line_h)
        cy += line_stride

    return int(total_h + 2 * padding)
# ══════════════════════════════════════════════
#  REDIMENSIONNEMENT + CENTRAGE (équivalent ffmpeg scale/crop)
# ══════════════════════════════════════════════
def _crop_resize_pillow(img, target_size):
    """Recadre au ratio cible puis redimensionne (remplit le cadre, coupe le surplus)."""
    tw, th = target_size
    w, h = img.size
    target_ratio = tw / th
    img_ratio = w / h
    if abs(img_ratio - target_ratio) > 0.02:
        if img_ratio > target_ratio:
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))
    return img.resize((tw, th), Image.LANCZOS)


def _measure_block_height(lines, font, padding):
    if not lines:
        return 0
    ascent, descent = font.getmetrics()
    text_line_h = ascent + descent
    total_h = text_line_h * len(lines) + LINE_SPACING * (len(lines) - 1)
    return int(total_h + 2 * padding)

# ══════════════════════════════════════════════
#  MOTEUR PRINCIPAL — HIÉRARCHIE + LOGO NYAVODROID (v2 corrigée)
# ══════════════════════════════════════════════
TOP_SAFE = 170   # zone haute couverte par l'UI Facebook
BOT_SAFE = 190   # zone basse couverte par l'UI Facebook

def _apply_logo(img, size=120):
    """Colle le logo rond (assets/profile.png) en haut à gauche, hors zone UI."""
    if os.path.isfile(PROFILE_IMAGE_PATH):
        try:
            logo = Image.open(PROFILE_IMAGE_PATH).convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
            img.paste(logo, (MARGIN, TOP_SAFE), mask)
        except Exception as e:
            print(f"⚠️ Logo : {e}")
    else:
        print(f"⚠️ Logo introuvable : {PROFILE_IMAGE_PATH}")
    return img

def _clean_keep_stars(t):
    """Nettoie les caractères invisibles MAIS conserve les ** du surlignage."""
    # Les tirets - sont placés en FIN de classe pour éviter l'erreur "bad character range"
    t = re.sub(r'[‎‏‍‌‬\ufeff\u00ad⁠᠎‪‮⁦⁨⁩-]', '', t or "")
    return ''.join(c for c in t if c.isprintable() or c in '\n\t').strip()

def _truncate(t, max_chars):
    """Coupe à la dernière phrase complète qui tient. Jamais de '…' ni de coupe en plein mot."""
    t = (t or "").strip()
    if t.count("**") % 2 == 1:
        t = t.replace("**", "")
    if len(t) <= max_chars:
        return t
    phrases = re.split(r'(?<=[.!?])\s+', t)
    out = ""
    for ph in phrases:
        cand = (out + " " + ph).strip() if out else ph
        if len(cand) <= max_chars:
            out = cand
        else:
            break
    if not out:  # 1re phrase trop longue : coupe au dernier mot (rare, le prompt calibre avant)
        out = t[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:!?")
    return out

def _auto_highlight(t):
    """Surligne automatiquement les chiffres/valeurs si l'IA n'a pas mis de **."""
    if not t or "**" in t:
        return t
    
    # Regex améliorée : capture 10^30kg ou 10^30 kg comme un seul bloc cohérent
    # \d+(?:[.,]\d+)?      → nombre entier ou décimal (ex: 10, 3.14)
    # (?:\^\d+)?           → puissance optionnelle collée (ex: ^30)
    # \s*                  → espaces optionnels entre le nombre et l'unité
    # (?:%|€|$|kg|...)     → liste des unités connues
    pattern = r"(\d+(?:[.,]\d+)?(?:\^\d+)?\s*(?:%|€|\$|kg|km|m|cm|mm|To|Go|Mo|ms|s|min|h|ans|an|mois|jours|fois|°C)?)"
    
    t = re.sub(pattern, r" **\1** ", t)
    
    # Nettoie les doubles espaces créés par le remplacement
    return re.sub(r"\s+", " ", t).strip()

def incruster_texte_pillow(image_in, contexte, fait_choc, consequence, source,
                           image_out, target_size):
    w, h = target_size
    img = Image.open(image_in).convert("RGBA")
    img = _crop_resize_pillow(img, (w, h))

    # Dégradé noir en bas
    gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dg = ImageDraw.Draw(gradient)
    gh = int(h * 0.55)
    for yy in range(gh):
        a = int(250 * ((yy / gh) ** 1.2))
        dg.line([(0, h - gh + yy), (w, h - gh + yy)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img, gradient)
    img = _apply_logo(img, size=120)
    draw = ImageDraw.Draw(img)

    # Textes : plafond large + coupe UNIQUEMENT à la phrase complète
    fait_choc = _truncate(_auto_highlight(_clean_keep_stars(fait_choc or "")), 260)
    consequence = _truncate(_auto_highlight(_clean_keep_stars(consequence or "")), 200)
    source = clean_text(source or "")

    max_w = w - 2 * MARGIN
    top_text = TOP_SAFE + 140
    avail_h = h - BOT_SAFE - top_text
    tok_re = re.compile(r"\*\*[^*]+\*\*|\S+")

    def wrap_tokens(text, font):
        lines, cur, cur_w = [], [], 0
        for tok in tok_re.findall(text):
            hl = tok.startswith("**") and tok.endswith("**") and len(tok) > 4
            cw = tok.replace("**", "")
            ww = draw.textlength(cw, font=font) + (24 if hl else 0)
            if hl and ww > max_w:
                hl = False; ww = draw.textlength(cw, font=font)
            sp = draw.textlength(" ", font=font) if cur else 0
            if cur_w + ww + sp <= max_w or not cur:
                cur.append((cw, hl, ww)); cur_w += ww + sp
            else:
                lines.append(cur); cur, cur_w = [(cw, hl, ww)], ww
        if cur: lines.append(cur)
        return lines

    def layout(size):
        ft = get_font(size, bold=True)
        fd = get_font(max(24, int(size * 0.62)), bold=False)
        tl = wrap_tokens(fait_choc, ft) if fait_choc else []
        dl = wrap_tokens(consequence, fd) if consequence else []
        at, bt = ft.getmetrics(); lh_t = at + bt; st_t = lh_t + 14
        ad, bd = fd.getmetrics(); lh_d = ad + bd; st_d = lh_d + 10
        total = len(tl) * st_t + len(dl) * st_d + (30 if source else 0) + 36
        return {"ft": ft, "fd": fd, "tl": tl, "dl": dl,
                "lh_t": lh_t, "lh_d": lh_d, "st_t": st_t, "st_d": st_d, "total": total}

    # Police auto-ajustée : le texte COMPLET tient toujours, jamais coupé
    L = None
    for size in (52, 46, 42, 38, 34, 30):
        cand = layout(size)
        if cand["total"] <= avail_h:
            L = cand
            break
    if L is None:
        L = layout(30)

    y = max(top_text, h - BOT_SAFE - L["total"])

    for lines, font, lh, st in ((L["tl"], L["ft"], L["lh_t"], L["st_t"]),
                                (L["dl"], L["fd"], L["lh_d"], L["st_d"])):
        for line in lines:
            lw = sum(ww for _, _, ww in line) + 8 * (len(line) - 1)
            x = (w - lw) // 2
            for cw, hl, ww in line:
                if hl:
                    draw.rectangle([x - 2, y - 3, x + ww + 2, y + lh + 5], fill=COLORS["blanc"])
                    draw.text((x + 12, y), cw, font=font, fill=COLORS["noir"])
                else:
                    draw.text((x + 2, y + 2), cw, font=font, fill=(0, 0, 0, 160))
                    draw.text((x, y), cw, font=font, fill=COLORS["blanc"])
                x += ww + 8
            y += st
        y += 18

    if source:
        font_src = get_font(20, bold=False)
        stxt = f"Source : {source}"
        sw = draw.textlength(stxt, font=font_src)
        draw.text(((w - sw) // 2, h - BOT_SAFE), stxt, font=font_src, fill=COLORS["gris_clair"])

    img.convert("RGB").save(image_out)

# ══════════════════════════════════════════
# VIS — Cloudflare en priorité (zéro quota)
# ══════════════════════════════════════════
def image_cloudflare_first(prompt: str, gemini_key: str, chemin: str,
                           size: tuple[int, int] | None = None) -> None:
    """
    Spécial VIS : Cloudflare en priorité absolue (gratuit, illimité).
    Fallback : Gemini → HF → Together → Fal → Pollinations.
    Utilisé par post_vis.py pour éviter les 429 Gemini.
    """
    if size is None:
        size = DEFAULT_IMG_SIZE
    prompt = clean_text(prompt) + (
        ", high quality, sharp focus, "
        "ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, NO TYPOGRAPHY, NO CAPTIONS, "
        "NO LABELS, NO WATERMARKS, NO FAKE TEXT, NO GIBBERISH TEXT."
    )
    erreurs = []

    # 1. CLOUDFLARE (multi-comptes round-robin) — priorité absolue
    if CLOUDFLARE_CREDS:
        try:
            print("    ☁️  Cloudflare image (priorité VIS)...")
            raw = chemin + ".cf_raw.png"
            _i_cloudflare(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Cloudflare ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Cloudflare={e}")
            print(f"    ⚠️ Cloudflare : {sanitize_log(str(e))}")

    # 2. Fallback : Gemini (si CF down)
    try:
        print("    🖼️ Gemini image (fallback)...")
        _i_gemini(prompt, chemin, gemini_key, size)
        _check_img(chemin, size)
        print(f"    ✅ Image Gemini ({os.path.getsize(chemin):,} o)")
        return
    except Exception as e:
        erreurs.append(f"Gemini={e}")
        print(f"    ⚠️ Gemini : {e}")

    # 3. Hugging Face
    if HF_TOKEN:
        try:
            print("    🖼️ Hugging Face (fallback)...")
            _i_hf(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image HF ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"HF={e}")
            print(f"    ⚠️ HF : {e}")

    # 4. Together
    if TOGETHER_API_KEY:
        try:
            print("    🖼️ Together (fallback)...")
            _i_together(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image Together ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Together={e}")
            print(f"    ⚠️ Together : {e}")

    # 5. Fal.ai
    if FAL_API_KEY:
        try:
            print("    🖼️ Fal.ai (fallback)...")
            raw = chemin + ".raw.png"
            _i_fal(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Fal.ai ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Fal.ai={e}")
            print(f"    ⚠️ Fal.ai : {e}")

    # 6. Pollinations (dernier recours)
    try:
        print("    🖼️ Pollinations (dernier recours)...")
        _i_pollinations(prompt, chemin)
        _check_img(chemin)
        print(f"    ✅ Image Pollinations ({os.path.getsize(chemin):,} o)")
        return
    except Exception as e:
        erreurs.append(f"Pollinations={e}")
        print(f"    ⚠️ Pollinations : {e}")

    raise RuntimeError("Image impossible (tous fournisseurs KO) :\n  " + "\n  ".join(erreurs))


# ══════════════════════════════════════════
# TEXTE — Cloudflare Workers AI (priorité VIS)
# ══════════════════════════════════════════
CLOUDFLARE_TEXT_MODELS = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/meta/llama-3-8b-instruct",
    "@hf/thebloke/llama-2-13b-chat-awq",
    "@cf/mistral/mistral-7b-instruct-v0.1",
    "@cf/qwen/qwen1.5-7b-chat-awq",
]

def _t_cloudflare(prompt: str) -> str:
    """Texte via Cloudflare Workers AI (round-robin multi-comptes). Robuste à tout format."""
    creds = []
    for suffix in ("", "_2", "_3"):
        acc = clean(os.environ.get(f"CLOUDFLARE_ACCOUNT_ID{suffix}", ""))
        tok = clean(os.environ.get(f"CLOUDFLARE_API_TOKEN{suffix}", ""))
        if acc and tok:
            creds.append((acc, tok))
    if not creds:
        raise ValueError("Aucun identifiant Cloudflare")
    if not hasattr(_t_cloudflare, "idx"):
        _t_cloudflare.idx = 0
    n = len(creds)
    derniere = None
    for i in range(n):
        idx = (_t_cloudflare.idx + i) % n
        acc, tok = creds[idx]
        for model in CLOUDFLARE_TEXT_MODELS:
            url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
            try:
                r = _req(
                    "POST", url,
                    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                    json_data={"messages": [{"role": "user", "content": prompt}],
                               "max_tokens": 500, "temperature": 0.4},
                    timeout=30, max_retries=1,
                )
                data = r.json()
                if not data.get("success"):
                    raise ValueError(f"CF erreur : {data}")
                # ─── Extraction robuste du texte ───
                res = data.get("result")
                txt = _extract_cf_text(res)
                if not txt.strip():
                    raise ValueError(f"CF réponse vide : {data}")
                _t_cloudflare.idx = (idx + 1) % n
                print(f"    ☁️ Cloudflare texte OK (compte #{idx+1}/{n}, {model})")
                return clean_text(txt)
            except Exception as e:
                derniere = e
                print(f"    ⚠️ CF {model} (#{idx+1}/{n}) : {sanitize_log(str(e))}")
                continue
    _t_cloudflare.idx = (_t_cloudflare.idx + 1) % n
    raise RuntimeError(f"CF texte KO : {sanitize_log(str(derniere))}")


def _extract_cf_text(res) -> str:
    """Extrait le texte de n'importe quel format de réponse Cloudflare."""
    if res is None:
        return ""
    if isinstance(res, str):
        return res
    if isinstance(res, bytes):
        return res.decode("utf-8", errors="replace")
    if isinstance(res, list):
        # Certains modèles renvoient une liste de chunks
        parts = []
        for item in res:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("content", "") or item.get("text", "") or item.get("response", ""))
        return " ".join(p for p in parts if p)
    if isinstance(res, dict):
        # Cas courant : {"response": "..."} ou {"response": {"content": "..."}}
        for key in ("response", "content", "text", "output", "message"):
            if key in res:
                val = res[key]
                if isinstance(val, str):
                    return val
                if isinstance(val, dict):
                    for subkey in ("content", "text", "response"):
                        if subkey in val and isinstance(val[subkey], str):
                            return val[subkey]
                if isinstance(val, list):
                    return " ".join(str(x) for x in val if x)
        # Fallback : concatène toutes les valeurs string
        return " ".join(str(v) for v in res.values() if isinstance(v, str))
    return str(res)


# ══════════════════════════════════════════
# VIS — FOND STORY (1080x1920, brun aquarelle)
# ══════════════════════════════════════════
def generer_fond_story_vis(texte: str, chemin: str, logo_path: str = "") -> None:
    """Génère un fond de story 1080x1920 avec dégradé brun + texte crème + logo."""
    w, h = 1080, 1920
    # Dégradé vertical brun : mocha → chocolate → espresso
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    stops = [
        (0.0, (92, 64, 51)),    # mocha (haut)
        (0.5, (62, 39, 35)),    # chocolate (milieu)
        (1.0, (26, 18, 11)),    # espresso (bas)
    ]
    for y in range(h):
        t = y / h
        # Interpolation entre stops
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                r = int(c0[0] + (c1[0] - c0[0]) * f)
                g = int(c0[1] + (c1[1] - c0[1]) * f)
                b = int(c0[2] + (c1[2] - c0[2]) * f)
                draw.line([(0, y), (w, y)], fill=(r, g, b))
                break
    # Texte crème centré verticalement
    font_size = 58
    texte_propre = clean_text(texte)
    margin = 100
    max_w = w - 2 * margin
    while font_size >= 36:
        font = get_font(font_size, bold=True)
        lines = wrap_text_pillow(texte_propre, font, max_w)
        ascent, descent = font.getmetrics()
        stride = ascent + descent + 12
        total_h = stride * len(lines)
        if total_h <= h - 2 * margin:
            break
        font_size -= 4
    y = (h - total_h) // 2
    cream = (212, 196, 168)
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        x = (w - lw) // 2
        draw.text((x, y), ln, font=font, fill=cream)
        y += stride
    # Logo cercle plat en bas à droite
    if logo_path and os.path.isfile(logo_path):
        try:
            size = 140
            logo = Image.open(logo_path).convert("RGBA").resize((size, size), Image.LANCZOS)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
            img.paste(logo, (w - size - margin, h - size - margin - 200), mask)
        except Exception:
            pass
    img.save(chemin)
