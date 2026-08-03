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


# ──────────────────────────────────────────────
# Secrets
# ──────────────────────────────────────────────
FB_PAGE_ID = clean(os.environ["FB_PAGE_ID"])
FB_PAGE_ACCESS_TOKEN = clean(os.environ["FB_PAGE_ACCESS_TOKEN"])
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
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"          # nouveau modèle HF
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"                # nouveau modèle Gemini
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
            corps = e.response.text[:400]  # affiche le corps brut si JSON invalide
    # Si le message reste désespérément vide, on ajoute le texte brut
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
                   "max_tokens": 500, "temperature": 0.9},
        timeout=30,
    )
    return clean_text(r.json()["choices"][0]["message"]["content"])


def _t_together(prompt: str) -> str:
    r = _req(
        "POST", TOGETHER_TEXT_URL,
        headers={"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"},
        json_data={"model": TOGETHER_TEXT_MODEL,
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 500, "temperature": 0.9},
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
                           "generationConfig": {"maxOutputTokens": 500, "temperature": 0.9}},
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
            print(f"    ⚠️ Gemini {modele} : {e}")
            continue
    raise RuntimeError(f"Gemini texte KO (tous modèles) : {derniere}")


def _t_hf(prompt: str) -> str:
    body = {"inputs": prompt,
            "parameters": {"max_new_tokens": 500, "temperature": 0.9, "return_full_text": False}}
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
            # Extraction adaptée à la nouvelle structure
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
            print(f"    ⚠️ Gemini {modele} : {e}")
            continue
    raise RuntimeError(f"Gemini image KO (tous modèles) : {derniere}")


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
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}"
    r = _req(
        "POST", url,
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"},
        json_data={
            "prompt": prompt,
            "num_steps": 4,
            "negative_prompt": CLOUDFLARE_NEGATIVE,
        },
        timeout=60,
    )
    data = r.json()
    if not data.get("success"):
        raise ValueError(f"Cloudflare erreur : {data}")
    b64 = data.get("result", {}).get("image")
    if not b64:
        raise ValueError(f"Cloudflare pas d'image : {data}")
    with open(chemin, "wb") as f:
        f.write(base64.b64decode(b64))


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
    """Recherche des photos sur Pexels et retourne une liste de résultats."""
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
    """Télécharge une photo Pexels et l'enregistre, éventuellement recadrée."""
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


def get_image_from_pexels(query: str, chemin: str, size: tuple[int, int] | None = None) -> bool:
    """Recherche et télécharge la première photo Pexels disponible."""
    photos = search_pexels(query)
    for photo in photos:
        if download_pexels_image(photo, chemin, size):
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

    prompt = clean_text(prompt) + ", high quality, sharp focus, no stretching, no distortion, no text, no letters, no words, no typography"
    erreurs = []

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
        print("    🖼️ Gemini image...")
        _i_gemini(prompt, chemin, gemini_key, size)
        _check_img(chemin, size)
        print(f"    ✅ Image Gemini ({os.path.getsize(chemin):,} o)")
        return
    except Exception as e:
        erreurs.append(f"Gemini={e}"); print(f"    ⚠️ Gemini image : {e}")

    # 2. Hugging Face
    if HF_TOKEN:
        try:
            print("    🖼️ Hugging Face image...")
            _i_hf(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image HF ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"HF={e}"); print(f"    ⚠️ HF image : {e}")

    # 3. Together
    if TOGETHER_API_KEY:
        try:
            print("    🖼️ Together image...")
            _i_together(prompt, chemin, size)
            _check_img(chemin, size)
            print(f"    ✅ Image Together ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Together={e}"); print(f"    ⚠️ Together image : {e}")

    # 4. Fal.ai
    if FAL_API_KEY:
        try:
            print("    🖼️ Fal.ai image (carré → crop)...")
            raw = chemin + ".raw.png"
            _i_fal(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Fal.ai ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Fal.ai={e}"); print(f"    ⚠️ Fal.ai : {e}")

    # 5. Cloudflare
    if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
        try:
            print("    🖼️ Cloudflare image (carré → crop)...")
            raw = chemin + ".raw.png"
            _i_cloudflare(prompt, raw)
            _check_img(raw)
            crop_to_ratio(raw, chemin, target_size=size)
            _check_img(chemin, size)
            os.remove(raw)
            print(f"    ✅ Image Cloudflare ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Cloudflare={e}"); print(f"    ⚠️ Cloudflare : {e}")

    # 6. Pollinations
    try:
        print("    🖼️ Pollinations image (dernier recours)...")
        _i_pollinations(prompt, chemin)
        _check_img(chemin)
        print(f"    ✅ Image Pollinations ({os.path.getsize(chemin):,} o)")
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
def overlay_watermark(image_in: str, image_out: str) -> None:
    """
    Superpose :
    - Expression aléatoire en bas-droite
    - Photo de profil (assets/profile.png) en bas-gauche
    """
    expressions_dir = "assets/expressions"
    profile_path = "assets/profile.png"
    temp = image_out + ".tmp.png"

    # Préparer les entrées : image principale + expression + profile
    inputs = ["-i", image_in]

    # Expression
    emo_path = None
    if os.path.isdir(expressions_dir):
        emos = [f for f in os.listdir(expressions_dir) if f.lower().endswith('.png')]
        if emos:
            chosen = random.choice(emos)
            emo_path = os.path.join(expressions_dir, chosen)
            print(f"    🎭 Watermark expression : {chosen}")
            inputs += ["-i", emo_path]
        else:
            print("    ⚠️ Aucune expression trouvée.")
    else:
        print("    ⚠️ Dossier expressions introuvable.")

    # Profile
    use_profile = os.path.isfile(profile_path)
    if use_profile:
        inputs += ["-i", profile_path]

    if not emo_path and not use_profile:
        # Rien à superposer, copie simple
        subprocess.run(["cp", image_in, image_out], check=True)
        return

    # Construction du filter_complex
    parts = []
    idx = 0
    main = f"[{idx}:v]"
    idx += 1

    # Si expression présente
    if emo_path:
        # Redimensionnement adaptatif
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=p=0", emo_path]
            out = subprocess.run(cmd, capture_output=True, text=True, check=True)
            w_emo, h_emo = map(int, out.stdout.strip().split(','))
        except:
            w_emo, h_emo = 100, 100
        max_dim = 130
        if w_emo > h_emo:
            new_w = max_dim
            new_h = int(h_emo * max_dim / w_emo)
        else:
            new_h = max_dim
            new_w = int(w_emo * max_dim / h_emo)
        margin = 40
        parts.append(f"[{idx}:v]scale={new_w}:{new_h},format=rgba[emo]")
        parts.append(f"{main}[emo]overlay=main_w-{new_w}-{margin}:main_h-{new_h}-{margin}[tmp1]")
        main = "[tmp1]"
        idx += 1

    # Si profile
    if use_profile:
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=p=0", profile_path]
            out = subprocess.run(cmd, capture_output=True, text=True, check=True)
            w_pr, h_pr = map(int, out.stdout.strip().split(','))
        except:
            w_pr, h_pr = 100, 100
        max_dim = 100
        if w_pr > h_pr:
            new_w = max_dim
            new_h = int(h_pr * max_dim / w_pr)
        else:
            new_h = max_dim
            new_w = int(w_pr * max_dim / h_pr)
        margin = 40
        parts.append(f"[{idx}:v]scale={new_w}:{new_h},format=rgba[pfp]")
        parts.append(f"{main}[pfp]overlay={margin}:main_h-{new_h}-{margin}[out]")
        main = "[out]"
        idx += 1
    else:
        # Rien d'autre, on renomme le flux final
        parts.append(f"{main}null[out]")

    filter_complex = ";".join(parts)

    try:
        subprocess.run(
            ["ffmpeg", *inputs, "-filter_complex", filter_complex,
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
    """Génère une image carrée 1080x1080 avec dégradé violet et texte centré."""
    from content_config import BACKGROUND_GRADIENT, CANVAS_SIZE_TEXTE_SEUL
    w, h = CANVAS_SIZE_TEXTE_SEUL

    # Création d'un dégradé vertical entre deux couleurs de la palette
    c1 = BACKGROUND_GRADIENT[0]  # violet profond
    c2 = BACKGROUND_GRADIENT[2]  # bleu nuit
    img = Image.new("RGB", (w, h))
    for y in range(h):
        r = int(int(c1[1:3], 16) + (int(c2[1:3], 16) - int(c1[1:3], 16)) * y / h)
        g = int(int(c1[3:5], 16) + (int(c2[3:5], 16) - int(c1[3:5], 16)) * y / h)
        b = int(int(c1[5:7], 16) + (int(c2[5:7], 16) - int(c1[5:7], 16)) * y / h)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))

    draw = ImageDraw.Draw(img)
    # Police par défaut (DejaVu Sans Bold si disponible, sinon police système)
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 60)
    except OSError:
        font = ImageFont.load_default()

    # Wrapping et centrage
    max_chars = 30
    lignes = []
    for mot in texte.split():
        if not lignes or len(lignes[-1] + " " + mot) > max_chars:
            lignes.append(mot)
        else:
            lignes[-1] += " " + mot

    # Hauteur totale du bloc texte
    line_height = font.getbbox("Ag")[3] + 10
    total_height = len(lignes) * line_height
    y_start = (h - total_height) // 2

    # Dessin
    draw = ImageDraw.Draw(img)
    for i, ligne in enumerate(lignes):
        bbox = font.getbbox(ligne)
        text_width = bbox[2] - bbox[0]
        x = (w - text_width) // 2
        draw.text((x, y_start + i * line_height), ligne, fill="white", font=font)

    img.save(chemin)
