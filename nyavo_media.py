#!/usr/bin/env python3
"""
Nyavo Channel — module média partagé (texte + image + audio).
Chaînes de fallback robustes, zéro duplication entre post_content / post_story.

  TEXTE : Mistral → Together (Mixtral) → Gemini (multi-modèles) → Hugging Face
  IMAGE : Gemini → Hugging Face → Together (FLUX) → Pollinations
  AUDIO : Replicate (musicgen) → Hugging Face (musicgen) → muet (best-effort)

Règle "fiable" : un 429 (quota) fait basculer IMMÉDIATEMENT au fournisseur suivant
(pas de retry de 5 min). Seuls les 5xx / timeouts / coupures réseau sont retentés,
brièvement. Les clés absentes = fournisseur sauté silencieusement.
"""

import base64
import os
import re
import time
import urllib.parse

import requests

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
# Secrets (communs aux 2 workflows ; Gemini est passé en paramètre car dédié)
# ──────────────────────────────────────────────
FB_PAGE_ID = clean(os.environ["FB_PAGE_ID"])
FB_PAGE_ACCESS_TOKEN = clean(os.environ["FB_PAGE_ACCESS_TOKEN"])
MISTRAL_API_KEY = clean(os.environ.get("MISTRAL_API_KEY", ""))
TOGETHER_API_KEY = clean(os.environ.get("TOGETHER_API_KEY", ""))
HF_TOKEN = clean(os.environ.get("HF_TOKEN", ""))
REPLICATE_API_TOKEN = clean(os.environ.get("REPLICATE_API_TOKEN", ""))

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
GRAPH_API_VERSION = "v25.0"

MISTRAL_TEXT_URL = "https://api.mistral.ai/v1/chat/completions"
TOGETHER_TEXT_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_IMAGE_URL = "https://api.together.xyz/v1/images/generations"
HF_INFER_URL = "https://api-inference.huggingface.co/models/"
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"
GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_TEXT_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"

# Modèles
TOGETHER_TEXT_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
HF_TEXT_MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"
TOGETHER_IMAGE_MODEL = "black-forest-labs/FLUX.1-dev"
HF_IMAGE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image"
REPLICATE_AUDIO_MODEL = "meta/musicgen"
HF_AUDIO_MODEL = "facebook/musicgen-small"

# Dimensions
IMG_W, IMG_H = 1024, 1792          # 9:16 pour Together / HF (multiples de 16)
POLL_W, POLL_H = 1080, 1920        # Pollinations
AUDIO_SECONDS = 11

# Modèles texte Gemini essayés dans l'ordre (ceux qui EXISTENT ; les 429 basculent vite)
GEMINI_TEXT_MODELS = ["gemini-flash-latest", "gemini-pro-latest", "gemini-2.5-pro", "gemini-2.5-flash"]

TIMEOUT = 60


# ══════════════════════════════════════════════
#  REQUÊTE HTTP — retry court, 429 = bascule immédiate
# ══════════════════════════════════════════════
def _req(
    method: str, url: str, *,
    headers: dict | None = None, json_data: dict | None = None,
    data: dict | None = None, files: dict | None = None,
    timeout: int = TIMEOUT, stream: bool = False,
    max_retries: int = 2, retry_delay: int = 6,
) -> requests.Response:
    """
    429 / 4xx  → lève immédiatement (le fallback suivant prend le relais).
    5xx / timeout / connexion → retente max_retries fois avec retry_delay.
    """
    derniere: Exception | None = None
    for tentative in range(1, max_retries + 1):
        try:
            r = requests.request(
                method=method, url=url, headers=headers,
                json=json_data, data=data, files=files,
                timeout=timeout, stream=stream,
            )
            if r.status_code == 429:
                r.raise_for_status()            # quota plein → bascule, pas d'attente
            if r.status_code >= 500:
                derniere = requests.exceptions.HTTPError(f"HTTP {r.status_code}", response=r)
                print(f"    ↻ {r.status_code} — retry {tentative}/{max_retries} dans {retry_delay}s")
                time.sleep(retry_delay)
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError:
            raise                                # 429 / 4xx propagés tout de suite
        except requests.exceptions.Timeout as e:
            derniere = e
            print(f"    ↻ timeout — retry {tentative}/{max_retries}")
            time.sleep(retry_delay)
        except requests.exceptions.ConnectionError as e:
            derniere = e
            print(f"    ↻ connexion — retry {tentative}/{max_retries}")
            time.sleep(retry_delay)
    raise derniere  # type: ignore[misc]


# ══════════════════════════════════════════════
#  FACEBOOK — vérif token + erreurs
# ══════════════════════════════════════════════
def fb_error(e: requests.exceptions.HTTPError, ctx: str) -> RuntimeError:
    corps, code = "", "N/A"
    if e.response is not None:
        code = e.response.status_code
        try:
            err = e.response.json().get("error", {})
            corps = f"[{err.get('type','?')}] {err.get('message','?')} (code {err.get('code','?')})"
        except Exception:
            corps = e.response.text[:400]
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


# ══════════════════════════════════════════════
#  TEXTE — fournisseurs
# ══════════════════════════════════════════════
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
                raise ValueError(f"pas de candidates ({data.get('promptFeedback',{}).get('blockReason','?')})")
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
    if "[/INST]" in txt:                       # filet : retirer l'écho du template
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
#  IMAGE — fournisseurs
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


def _i_gemini(prompt: str, chemin: str, gemini_key: str) -> None:
    r = _req(
        "POST", GEMINI_IMAGE_URL,
        headers={"x-goog-api-key": gemini_key, "Content-Type": "application/json"},
        json_data={"model": GEMINI_IMAGE_MODEL,
                   "input": [{"type": "text", "text": prompt}],
                   "response_format": {"type": "image", "aspect_ratio": "9:16", "image_size": "1K"}},
        timeout=120,
    )
    b64 = _extract_b64(r.json())
    with open(chemin, "wb") as f:
        f.write(base64.b64decode(b64))


def _i_hf(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", f"{HF_INFER_URL}{HF_IMAGE_MODEL}",
        headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
        json_data={"inputs": prompt, "parameters": {"width": IMG_W, "height": IMG_H}},
        timeout=120, max_retries=2, retry_delay=8,
    )
    ct = r.headers.get("Content-Type", "")
    if "image" not in ct:                       # JSON d'erreur au lieu d'une image
        raise ValueError(f"réponse non-image ({ct}) : {r.text[:200]}")
    with open(chemin, "wb") as f:
        f.write(r.content)


def _i_together(prompt: str, chemin: str) -> None:
    r = _req(
        "POST", TOGETHER_IMAGE_URL,
        headers={"Authorization": f"Bearer {TOGETHER_API_KEY}", "Content-Type": "application/json"},
        json_data={"model": TOGETHER_IMAGE_MODEL, "prompt": prompt,
                   "width": IMG_W, "height": IMG_H, "n": 1, "response_format": "b64_json"},
        timeout=120,
    )
    b64 = r.json()["data"][0]["b64_json"]
    with open(chemin, "wb") as f:
        f.write(base64.b64decode(b64))


def _i_pollinations(prompt: str, chemin: str) -> None:
    encoded = urllib.parse.quote(prompt, safe='')   # ← encode le "/" de "Scène 1/3" → plus de 404
    url = f"{POLLINATIONS_URL}{encoded}?width={POLL_W}&height={POLL_H}&nologo=true"
    r = _req("GET", url, headers={"User-Agent": "NyavoChannel/1.0"}, timeout=120, stream=True)
    with open(chemin, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def _check_img(chemin: str) -> None:
    taille = os.path.getsize(chemin)
    if taille < 1024:
        raise ValueError(f"image suspecte ({taille} octets)")


def image_avec_fallback(prompt: str, gemini_key: str, chemin: str) -> None:
    prompt = clean_text(prompt)
    erreurs = []

    try:
        print("    🖼️ Gemini image...")
        _i_gemini(prompt, chemin, gemini_key); _check_img(chemin)
        print(f"    ✅ Image Gemini ({os.path.getsize(chemin):,} o)")
        return
    except Exception as e:
        erreurs.append(f"Gemini={e}"); print(f"    ⚠️ Gemini image : {e}")

    if HF_TOKEN:
        try:
            print("    🖼️ Hugging Face image...")
            _i_hf(prompt, chemin); _check_img(chemin)
            print(f"    ✅ Image HF ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"HF={e}"); print(f"    ⚠️ HF image : {e}")

    if TOGETHER_API_KEY:
        try:
            print("    🖼️ Together image...")
            _i_together(prompt, chemin); _check_img(chemin)
            print(f"    ✅ Image Together ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            erreurs.append(f"Together={e}"); print(f"    ⚠️ Together image : {e}")

    try:
        print("    🖼️ Pollinations image...")
        _i_pollinations(prompt, chemin); _check_img(chemin)
        print(f"    ✅ Image Pollinations ({os.path.getsize(chemin):,} o)")
        return
    except Exception as e:
        erreurs.append(f"Pollinations={e}"); print(f"    ⚠️ Pollinations image : {e}")

    raise RuntimeError("Image impossible (tous fournisseurs KO) :\n  " + "\n  ".join(erreurs))


# ══════════════════════════════════════════════
#  AUDIO — fournisseurs (best-effort, jamais bloquant)
# ══════════════════════════════════════════════
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
    for _ in range(40):                          # ~2 min max
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
    """Renvoie True si un son a été généré, False sinon (Reel muet, non bloquant)."""
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