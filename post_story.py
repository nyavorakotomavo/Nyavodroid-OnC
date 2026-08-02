#!/usr/bin/env python3
"""
Nyavodroid — STORY avec hiérarchie de texte, watermark et style violet/magenta.
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
    HOOK_FONTSIZE, EXPL_FONTSIZE, DETAIL_FONTSIZE, MARGIN,
    EXPRESSIONS_DIR
)

# Clé Gemini dédiée aux stories (nouvelle clé si nécessaire, stockée dans les secrets GitHub)
GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])

STORY_IMAGE_PATH = "story_image.png"
STORY_WIDTH, STORY_HEIGHT = 1080, 1920

# ══════════════════════════════════════════════
#  UTILITAIRES
# ══════════════════════════════════════════════
def wrap_text(text: str, max_chars: int = 26) -> str:
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
    if len(lines) == 1 and len(lines[0]) > max_chars:
        s = lines[0]
        lines = [s[i:i+max_chars] for i in range(0, len(s), max_chars)]
    return "\n".join(lines)


def escape_text(t: str) -> str:
    """Échappe les caractères spéciaux pour ffmpeg drawtext."""
    return t.replace("'", "\\'").replace(":", "\\:").replace("%", "%%").replace("\\", "\\\\")


# ══════════════════════════════════════════════
#  GÉNÉRATION DE TEXTE HIÉRARCHISÉ
# ══════════════════════════════════════════════
def generer_texte_story():
    """Génère les trois niveaux (hook, explication, détail) via l'IA."""
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        "Tu es Nyavodroid, la page tech qui révèle les mécanismes cachés du monde numérique.\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\n\n"
        "Génère UNIQUEMENT un objet JSON avec les trois clés suivantes :\n"
        '  "hook" : une phrase d\'accroche choc (max 10 mots), commence par un emoji pertinent\n'
        '  "explication" : 2-3 lignes développant le hook, en langage simple\n'
        '  "detail" : une précision chiffrée, une source ou une note courte (1 ligne)\n\n'
        "Règles :\n"
        "- Pas de texte autour du JSON.\n"
        "- Ton : " + TON_EDITORIAL + "\n"
        "- Aucun jargon inutile, compréhensible par tous.\n"
        "- Le hook doit être percutant et donner envie de lire la suite.\n"
    )
    print(f"  📝 Génération texte hiérarchique...\n     Axe   : {PILLARS[pilier]['label']}\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
    # Nettoyage Markdown éventuel
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]
    try:
        data = json.loads(brut)
        hook = data.get("hook", "")
        explication = data.get("explication", "")
        detail = data.get("detail", "")
    except Exception:
        # Fallback : utiliser la réponse brute comme hook, le reste vide
        print("  ⚠️ Le format JSON n'a pas été respecté, utilisation du texte brut comme hook.")
        hook = brut
        explication = ""
        detail = ""

    # Nettoyage et vérification
    hook = M.clean_text(hook)
    explication = M.clean_text(explication)
    detail = M.clean_text(detail)

    # Ajouter un emoji si absent du hook
    if not any(ord(c) > 127 for c in hook[:3]):
        emojis = ["💡", "🔍", "⚡", "🧠", "🤖", "🛡️", "🌐", "🔐", "💻", "🚀", "📡", "🧬"]
        hook = random.choice(emojis) + " " + hook

    print(f"  ✅ Hook      : {hook}")
    if explication:
        print(f"     Explication : {explication}")
    if detail:
        print(f"     Détail      : {detail}")
    return pilier, sujet, hook, explication, detail


# ══════════════════════════════════════════════
#  IMAGE DE FOND
# ══════════════════════════════════════════════
def generer_image_story(pilier: str, texte: str, chemin: str) -> None:
    """
    Génère l'image d'arrière-plan en 9:16 (1080x1920) avec le style violet/magenta.
    """
    prompt = M.clean_text(
        f"Illustration verticale 9:16 pour le sujet : {texte}\n"
        f"Axe : {PILLARS[pilier]['label']}\nStyle : {STYLE_IMAGE_SUFFIX}"
    )
    M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin, size=(1080, 1920))


# ══════════════════════════════════════════════
#  INCRUSTATION DU TEXTE + WATERMARK
# ══════════════════════════════════════════════
def incruster_texte_hierarchique(image_in: str, hook: str, explication: str, detail: str, image_out: str) -> None:
    """
    Incruste les 3 niveaux de texte sur l'image, applique le watermark d'expression.
    """
    # ─── 1. Scale/crop pour garantir un 9:16 sans déformation ───
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", image_in
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w_orig, h_orig = map(int, out.stdout.strip().split(','))
        ratio_orig = w_orig / h_orig
        ratio_cible = STORY_WIDTH / STORY_HEIGHT
        if abs(ratio_orig - ratio_cible) > 0.05:
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
            )
        else:
            scale_filter = (
                f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={STORY_WIDTH}:{STORY_HEIGHT}"
            )
    except Exception:
        scale_filter = (
            f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={STORY_WIDTH}:{STORY_HEIGHT}"
        )

    # ─── 2. Préparation des textes (wrapping + échappement) ───
    hook_wrapped = wrap_text(hook, max_chars=20)
    expl_wrapped = wrap_text(explication, max_chars=35)
    detail_wrapped = wrap_text(detail, max_chars=45)

    hook_esc = escape_text(hook_wrapped)
    expl_esc = escape_text(expl_wrapped)
    detail_esc = escape_text(detail_wrapped)

    # ─── 3. Filtres de texte ───
    # Hook : haut, centré, blanc, ombre magenta
    hook_y = f"{MARGIN}"
    hook_filtre = (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{hook_esc}':fontcolor=0xFFFFFF:fontsize={HOOK_FONTSIZE}:"
        f"x=(w-text_w)/2:y={hook_y}:"
        f"shadowcolor=0xEA4FD9@0.6:shadowx=0:shadowy=4"
    )

    # Explication : sous le hook
    expl_y = f"{MARGIN}+{HOOK_FONTSIZE}+30"
    expl_filtre = (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{expl_esc}':fontcolor=0xFFFFFF:fontsize={EXPL_FONTSIZE}:"
        f"x=(w-text_w)/2:y={expl_y}:"
        f"shadowcolor=0x000000@0.4:shadowx=1:shadowy=2"
    )

    # Détail : bas, gris clair
    detail_y = f"h-{MARGIN}-{DETAIL_FONTSIZE}"
    detail_filtre = (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{detail_esc}':fontcolor=0xCCCCCC:fontsize={DETAIL_FONTSIZE}:"
        f"x=(w-text_w)/2:y={detail_y}"
    )

    # Combinaison des filtres
    filtre = f"{scale_filter},{hook_filtre}"
    if explication:
        filtre += f",{expl_filtre}"
    if detail:
        filtre += f",{detail_filtre}"

    # Image temporaire avec texte
    temp_text = "story_text.png"
    try:
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", temp_text],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg texte échec (code {e.returncode}) :\n{e.stderr[:500]}")

    # ─── 4. Watermark d'expression ───
    M.overlay_expression(temp_text, image_out)
    # Nettoyage du fichier temporaire
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
    print("🎬 Nyavodroid — Story [Hiérarchie + Watermark]")
    print("=" * 50)
    M.verify_fb_token()

    pilier, sujet, hook, explication, detail = generer_texte_story()
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}\n")

    # Génération de l'image de fond (avec le sujet, pas le texte final)
    print("  🖼️  Génération image de fond...")
    generer_image_story(pilier, sujet, "story_raw.png")

    # Incrustation du texte + watermark
    print("  🎨 Incrustation du texte hiérarchique + watermark...")
    incruster_texte_hierarchique("story_raw.png", hook, explication, detail, STORY_IMAGE_PATH)

    # Publication
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