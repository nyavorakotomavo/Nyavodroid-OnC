#!/usr/bin/env python3
"""
Nyavodroid — STORY avec hiérarchie de texte dynamique, emoji en image,
watermark double (expression + profil), style Infographie Narrative d'Expert.
"""

import os
import random
import subprocess
import sys
import json

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    ACCROCHE_FONTSIZE, FAIT_CHOC_FONTSIZE, CONSEQUENCE_FONTSIZE, SOURCE_FONTSIZE, MARGIN,
    EXPRESSIONS_DIR, PROFILE_IMAGE_PATH, EMOJIS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])

STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920


# ══════════════════════════════════════════════
#  UTILITAIRES (identiques à ceux de post_content)
# ══════════════════════════════════════════════
def wrap_text(text: str, max_chars: int = 26) -> str:
    if not text:
        return ""
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
    if len(lines) == 1 and len(lines[0]) > max_chars:
        s = lines[0]
        lines = [s[i:i+max_chars] for i in range(0, len(s), max_chars)]
    return "\n".join(lines)


def escape_text(t: str) -> str:
    return t.replace("'", "\\'").replace(":", "\\:").replace("%", "%%").replace("\\", "\\\\")


def clean_backslash(t: str) -> str:
    return t.replace("\\", "")


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + 1


def _get_emoji_path(emoji_char: str) -> str | None:
    """Cherche une image PNG correspondant à l'emoji dans assets/emojis/."""
    emoji_filename = emoji_char + ".png"
    path = os.path.join(EMOJIS_DIR, emoji_filename)
    if os.path.isfile(path):
        return path
    # fallback : premier emoji trouvé
    if os.path.isdir(EMOJIS_DIR):
        for f in os.listdir(EMOJIS_DIR):
            if f.endswith(".png"):
                return os.path.join(EMOJIS_DIR, f)
    return None


# ══════════════════════════════════════════════
#  GÉNÉRATION DE TEXTE HIÉRARCHISÉ (JSON)
# ══════════════════════════════════════════════
def generer_texte_story():
    """Génère la structure contexte / fait_choc / consequence / source en français."""
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français et en respectant EXACTEMENT ce format JSON :\n"
        '{\n  "contexte": "1 phrase de contexte général",\n'
        '  "fait_choc": "le chiffre ou fait surprenant (max 8 mots)",\n'
        '  "consequence": "1 phrase de conséquence concrète",\n'
        '  "source": "source vérifiable (ex: Nature, 2026)"\n}\n\n'
        f"Sujet imposé : {sujet}. {TON_EDITORIAL}"
    )
    print(f"  📝 Génération texte Cultination...\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]
    try:
        data = json.loads(brut)
        contexte = data.get("contexte", "")
        fait_choc = data.get("fait_choc", "")
        consequence = data.get("consequence", "")
        source = data.get("source", "")
    except Exception:
        # fallback : on découpe le texte brut en trois lignes max
        lignes = [l.strip() for l in brut.split('\n') if l.strip()]
        contexte = lignes[0] if len(lignes) > 0 else ""
        fait_choc = lignes[1] if len(lignes) > 1 else ""
        consequence = lignes[2] if len(lignes) > 2 else ""
        source = ""

    return pilier, sujet, contexte, fait_choc, consequence, source


# ══════════════════════════════════════════════
#  IMAGE DE FOND
# ══════════════════════════════════════════════
def generer_image_story(pilier: str, sujet: str, chemin: str) -> None:
    """Génère l'image 9:16 avec le style premium (via IA)."""
    prompt = M.clean_text(
        f"Illustration verticale 9:16 pour le sujet : {sujet}\n"
        f"Axe : {PILLARS[pilier]['label']}\nStyle : {STYLE_IMAGE_SUFFIX}"
    )
    M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin, size=(1080, 1920))
# ══════════════════════════════════════════════
#  INCRUSTATION DE TEXTE DYNAMIQUE + EMOJI IMAGE + WATERMARK DOUBLE
# ══════════════════════════════════════════════
def incruster_texte_hierarchique(image_in: str, contexte: str, fait_choc: str, consequence: str, source: str, image_out: str) -> None:
    # 1. Scale/crop 9:16
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "csv=p=0", image_in]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w_orig, h_orig = map(int, out.stdout.strip().split(','))
        ratio_orig = w_orig / h_orig
        ratio_cible = STORY_WIDTH / STORY_HEIGHT
        if abs(ratio_orig - ratio_cible) > 0.05:
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                "format=rgba"
            )
        else:
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={STORY_WIDTH}:{STORY_HEIGHT},"
                "format=rgba"
            )
    except:
        scale_filter = f"scale={STORY_WIDTH}:{STORY_HEIGHT},format=rgba"

    # 2. Nettoyage
    contexte = clean_backslash(M.clean_text(contexte))
    fait_choc = clean_backslash(M.clean_text(fait_choc))
    consequence = clean_backslash(M.clean_text(consequence))
    source = clean_backslash(M.clean_text(source))

    def wrap(t, max_chars): return wrap_text(t, max_chars) if t else ""
    ctx_w = wrap(contexte, 30)
    fait_w = wrap(fait_choc, 22)
    cons_w = wrap(consequence, 35)
    src_w = wrap(source, 45)

    # Positions verticales fixes
    y_ctx = MARGIN
    y_fait = y_ctx + 80 + 20
    y_cons = y_fait + 90 + 20
    y_src = STORY_HEIGHT - MARGIN - 30

    filtres = []
    if ctx_w:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{escape_text(ctx_w)}':fontcolor=0xFFFFFF:fontsize={ACCROCHE_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_ctx}:"
            f"box=1:boxcolor=0x0D0D0D@0.7:boxborderw=20"
        )
    if fait_w:
        # Encadré blanc, texte violet sans ombre
        box_w, box_h = 600, 80
        box_x = (STORY_WIDTH - box_w)//2
        box_y = y_fait - 10
        filtres.append(f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:color=0xFFFFFF@0.85:t=fill")
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{escape_text(fait_w)}':fontcolor=0x2D1B4E:fontsize={FAIT_CHOC_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_fait}"
        )
    if cons_w:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{escape_text(cons_w)}':fontcolor=0xFFFFFF:fontsize={CONSEQUENCE_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_cons}:"
            f"box=1:boxcolor=0x0D0D0D@0.7:boxborderw=20"
        )
    if src_w:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{escape_text(src_w)}':fontcolor=0xCCCCCC:fontsize={SOURCE_FONTSIZE}:"
            f"x={MARGIN}:y={y_src}"
        )

    filtre_texte = scale_filter
    if filtres:
        filtre_texte += "," + ",".join(filtres)

    temp_text = "story_text_cult.png"
    try:
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre_texte, "-frames:v", "1", "-y", temp_text],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg texte story échec : {e.stderr[:500]}")

    M.overlay_watermark(temp_text, image_out, source_text=source)
    if os.path.exists(temp_text):
        os.remove(temp_text)


# ══════════════════════════════════════════════
#  PUBLICATION
# ══════════════════════════════════════════════
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


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main() -> None:
    print("=" * 50)
    print("🎬 Nyavodroid — Story [Premium Cultination]")
    print("=" * 50)
    M.verify_fb_token()

    pilier, sujet, contexte, fait_choc, consequence, source = generer_texte_story()
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}\n")
    print(f"   Contexte    : {contexte}")
    print(f"   Fait choc   : {fait_choc}")
    print(f"   Conséquence : {consequence}")
    print(f"   Source      : {source}")

    print("  🖼️  Génération image de fond...")
    generer_image_story(pilier, sujet, "story_raw.png")

    print("  🎨 Incrustation Cultination (encadré + watermark)...")
    incruster_texte_hierarchique("story_raw.png", contexte, fait_choc, consequence, source, STORY_IMAGE_PATH)

    pid = uploader_photo_non_publiee(STORY_IMAGE_PATH)
    res = publier_story(pid)
    print(f"\n{'='*50}\n✅ TERMINÉ — Story ID : {res.get('id','N/A')}\n{'='*50}")

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