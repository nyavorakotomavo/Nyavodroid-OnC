#!/usr/bin/env python3
"""
Nyavodroid — STORY (image courte + texte minimal).
Logique métier uniquement ; texte/image viennent de nyavo_media.
Secrets : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_STORY,
          MISTRAL_API_KEY, TOGETHER_API_KEY, HF_TOKEN
"""

import os
import random
import subprocess
import sys

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])
STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920

# ────────────── Nouvelle fonction utilitaire ──────────────
def get_image_dimensions(filepath: str) -> tuple[int, int]:
    """Retourne (largeur, hauteur) d'une image via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0", filepath
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    w, h = out.stdout.strip().split(",")
    return int(w), int(h)

def wrap_text(text: str, max_chars: int = 30) -> str:
    """Découpe le texte en plusieurs lignes si trop long (au mot près)."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line = f"{current_line} {word}".strip()
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    # Si une seule ligne mais très longue, on peut couper sans casser les mots
    if len(lines) == 1 and len(lines[0]) > max_chars:
        # On force un découpage approximatif
        s = lines[0]
        lines = [s[i:i+max_chars] for i in range(0, len(s), max_chars)]
    return "\n".join(lines)


def generer_texte_story():
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    style = random.choice(STORY_PROMPTS)
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    prompt = (
        "Tu es Nyavodroid, la page tech qui révèle les mécanismes cachés du monde numérique.\n\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\nSujet imposé : {sujet}\nFormat : {style}\n\n"
        f"Consignes : UNE seule phrase en français (< 15 mots) ; ton {TON_EDITORIAL} ; "
        "au moins un terme technique précis ; pas de guillemets, pas de titre, pas de Markdown ; "
        "interdit : généralités, banalités, hors-sujet."
    )
    print(f"  📝 Texte (story)...\n     Axe   : {PILLARS[pilier]['label']}\n     Sujet : {sujet}")
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    texte = texte.strip().strip('"').split("\n")[0]
    texte = M.clean_text(texte)
    if not texte:
        raise ValueError("Réponse texte vide.")
    print(f"  ✅ Texte : « {texte} »")
    return pilier, sujet, texte


def generer_image_story(pilier: str, texte: str, chemin: str) -> None:
    prompt = M.clean_text(
        f"Illustration verticale 9:16 pour ce texte : {texte}\n"
        f"Axe : {PILLARS[pilier]['label']}\nStyle : {STYLE_IMAGE_SUFFIX}\n"
        f"L'image doit refléter visuellement le contenu du texte.")
    M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin)


def incruster_texte(image_in: str, texte: str, image_out: str) -> None:
    # ─── 1. Adapter le texte : wrapping + police adaptative ───
    lignes = wrap_text(texte, max_chars=32)
    nb_lignes = lignes.count("\n") + 1
    # Taille de police selon la longueur
    if nb_lignes == 1:
        fontsize = 58
    elif nb_lignes == 2:
        fontsize = 52
    else:
        fontsize = 44  # pour 3+ lignes, on réduit

    texte_esc = lignes.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")

    # ─── 2. Gestion du redimensionnement anti‑spaghetti ───
    try:
        w_orig, h_orig = get_image_dimensions(image_in)
        ratio_orig = w_orig / h_orig
        ratio_cible = STORY_WIDTH / STORY_HEIGHT  # 9:16 = 0.5625
        # Si l'écart est > 5%, on utilise decrease + pad (pas de déformation)
        if abs(ratio_orig - ratio_cible) > 0.05:
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
            )
        else:
            # Ratio proche → on remplit par zoom/crop (pas de barres noires)
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={STORY_WIDTH}:{STORY_HEIGHT}"
            )
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        # ffprobe absent, image illisible, ou sortie inattendue (parsing w,h) :
        # on retombe sur le comportement précédent (increase + crop) sans planter.
        print(f"  ⚠️  ffprobe indisponible ou échec ({type(e).__name__}: {e}) — fallback increase+crop.")
        scale_filter = (
            f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={STORY_WIDTH}:{STORY_HEIGHT}"
        )

    # ─── 3. Filtre drawtext avec le texte multiligne ───
    drawtext_filter = (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{texte_esc}':fontcolor=0x00E5FF:fontsize={fontsize}:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"box=1:boxcolor=0x0D0D0D@0.7:boxborderw=30:line_spacing=14"
    )

    filtre = f"{scale_filter},{drawtext_filter}"

    try:
        print("  🎨 Incrustation texte via ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", image_out],
            check=True, capture_output=True, text=True
        )
        print(f"  ✅ Image finale : {image_out}")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:500]}") from e


def uploader_photo_non_publiee(path: str) -> str:
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        print("  📤 Upload photo Facebook...")
        with open(path, "rb") as f:
            r = M._req("POST", ep,
                       data={"published": "false", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(path), f, "image/png")}, timeout=M.TIMEOUT)
        res = r.json()
        pid = res.get("id")
        if not pid:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Photo ID : {pid}")
        return pid
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "upload photo") from e
    except OSError as e:
        raise RuntimeError(f"Fichier illisible '{path}' : {e}") from e


def publier_story(photo_id: str) -> dict:
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photo_stories"
    try:
        print("  🚀 Publication story...")
        r = M._req("POST", ep, data={"photo_id": photo_id, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print("  ✅ Story publiée !")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "publication story") from e


def main() -> None:
    print("=" * 50)
    print("🎬 Nyavodroid — Story [Projet Gemini A]")
    print("=" * 50)
    M.verify_fb_token()
    pilier, sujet, texte = generer_texte_story()
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}\n📌 Texte : {texte}\n")
    generer_image_story(pilier, texte, "story_raw.png")
    incruster_texte("story_raw.png", texte, STORY_IMAGE_PATH)
    pid = uploader_photo_non_publiee(STORY_IMAGE_PATH)
    res = publier_story(pid)
    print(f"\n{'='*50}\n✅ TERMINÉ — Story ID : {res.get('id','N/A')}\n{'='*50}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr); sys.exit(1)
    except KeyError as e:
        print(f"\n❌ Secret manquant : {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"\n❌ Inattendu : {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)
