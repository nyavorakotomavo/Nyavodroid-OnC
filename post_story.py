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
    HOOK_FONTSIZE, EXPL_FONTSIZE, DETAIL_FONTSIZE, MARGIN,
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
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    prompt = (
        "Tu es Nyavodroid, la page tech premium.\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\n"
        f"Sujet imposé : {sujet}\n\n"
        "Génère UNIQUEMENT un objet JSON avec les clés :\n"
        '  "hook" : phrase d\'accroche choc (max 10 mots), commence par un emoji pertinent\n'
        '  "explication" : 2-3 lignes développant le hook, en langage simple\n'
        '  "detail" : une précision chiffrée, une source ou une note courte (1 ligne)\n\n'
        "Règles :\n"
        "- Pas de texte autour du JSON.\n"
        "- Ton : " + TON_EDITORIAL + "\n"
        "- Compréhensible par tous.\n"
    )
    print(f"  📝 Génération texte hiérarchique...\n     Axe   : {PILLARS[pilier]['label']}\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
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
        print("  ⚠️ JSON invalide, utilisation du texte brut comme hook.")
        hook = brut
        explication = ""
        detail = ""

    hook = M.clean_text(hook)
    explication = M.clean_text(explication)
    detail = M.clean_text(detail)

    # Ajouter un emoji si absent du hook
    if hook and not any(ord(c) > 127 for c in hook[:3]):
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
def incruster_texte_hierarchique(image_in: str, hook: str, explication: str, detail: str, image_out: str) -> None:
    """
    Incruste les 3 niveaux de texte sur une image 9:16.
    - Positions Y dynamiques pour éviter le chevauchement.
    - Emoji du hook affiché sous forme d'image PNG.
    - Watermark double (expression + profil) appliqué à la fin.
    """
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
    except Exception:
        scale_filter = (
            f"scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={STORY_WIDTH}:{STORY_HEIGHT},"
            "format=rgba"
        )

    # 2. Nettoyage des textes
    hook = clean_backslash(hook)
    explication = clean_backslash(explication)
    detail = clean_backslash(detail)

    # 3. Extraction de l'emoji du début du hook
    emoji_char = None
    if hook and ord(hook[0]) > 127:
        emoji_char = hook[0]
        hook = hook[1:].strip()
    if not emoji_char and hook and len(hook) > 1 and ord(hook[0]) > 127:
        emoji_char = hook[0]
        hook = hook[1:].strip()

    emoji_path = _get_emoji_path(emoji_char) if emoji_char else None

    # 4. Wrapping
    max_chars_hook = 18
    max_chars_expl = 28
    max_chars_detail = 40
    hook_wrapped = wrap_text(hook, max_chars_hook) if hook else ""
    expl_wrapped = wrap_text(explication, max_chars_expl) if explication else ""
    detail_wrapped = wrap_text(detail, max_chars_detail) if detail else ""

    hook_esc = escape_text(hook_wrapped)
    expl_esc = escape_text(expl_wrapped)
    detail_esc = escape_text(detail_wrapped)

    # 5. Calcul des positions Y dynamiques
    line_hook = int(HOOK_FONTSIZE * 1.3)
    line_expl = int(EXPL_FONTSIZE * 1.3)
    line_detail = int(DETAIL_FONTSIZE * 1.3)

    y_hook = MARGIN
    nb_lignes_hook = count_lines(hook_wrapped)
    hauteur_hook = nb_lignes_hook * line_hook

    y_expl = y_hook + hauteur_hook + 25
    nb_lignes_expl = count_lines(expl_wrapped)
    hauteur_expl = nb_lignes_expl * line_expl

    # Détail toujours en bas, avec marge
    y_detail = STORY_HEIGHT - MARGIN - line_detail

    # 6. Construction des filtres drawtext
    filtres = []
    if hook_esc:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{hook_esc}':fontcolor=0xFFFFFF:fontsize={HOOK_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_hook}:"
            f"shadowcolor=0xEA4FD9@0.6:shadowx=0:shadowy=4"
        )
    if expl_esc:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{expl_esc}':fontcolor=0xFFFFFF:fontsize={EXPL_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_expl}:"
            f"shadowcolor=0x000000@0.4:shadowx=1:shadowy=2"
        )
    if detail_esc:
        filtres.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{detail_esc}':fontcolor=0xCCCCCC:fontsize={DETAIL_FONTSIZE}:"
            f"x=(w-text_w)/2:y={y_detail}"
        )

    filtre_texte = scale_filter
    if filtres:
        filtre_texte += "," + ",".join(filtres)

    # 7. Image temporaire après texte
    temp_text = "story_text_incrust.png"
    try:
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre_texte, "-frames:v", "1", "-y", temp_text],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg texte story échec : {e.stderr[:500]}")

    # 8. Superposition de l'emoji (si dispo)
    if emoji_path:
        emoji_size = 80
        # Position : centré horizontalement avec le hook, juste au-dessus de la première ligne
        emo_x = (STORY_WIDTH - emoji_size) // 2
        emo_y = y_hook - emoji_size - 10  # un peu au-dessus du hook
        if emo_y < 0:
            emo_y = y_hook  # fallback si trop haut
        emo_filter = (
            f"[1:v]scale={emoji_size}:-1[emo];"
            f"[0:v][emo]overlay={emo_x}:{emo_y}"
        )
        temp_emo = "story_text_emo.png"
        try:
            subprocess.run(
                ["ffmpeg", "-i", temp_text, "-i", emoji_path,
                 "-filter_complex", emo_filter,
                 "-frames:v", "1", "-y", temp_emo],
                check=True, capture_output=True, text=True
            )
            os.replace(temp_emo, temp_text)
        except subprocess.CalledProcessError:
            # continuer sans emoji
            pass

    # 9. Watermark double (expression + profil)
    M.overlay_watermark(temp_text, image_out)
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
    print("🎬 Nyavodroid — Story [Premium]")
    print("=" * 50)
    M.verify_fb_token()

    pilier, sujet, hook, explication, detail = generer_texte_story()
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}\n")

    print("  🖼️  Génération image de fond...")
    generer_image_story(pilier, sujet, "story_raw.png")

    print("  🎨 Incrustation du texte hiérarchique + watermark double...")
    incruster_texte_hierarchique("story_raw.png", hook, explication, detail, STORY_IMAGE_PATH)

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