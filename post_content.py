#!/usr/bin/env python3
"""
Nyavodroid — publication multi-formats (texte / image+texte / Reel).
Logique métier uniquement ; texte/image/audio viennent de nyavo_media.
Secrets : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_CONTENT,
          MISTRAL_API_KEY, TOGETHER_API_KEY, HF_TOKEN, REPLICATE_API_TOKEN,
          FAL_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN,
          FREEAI_API_KEY
"""

import os
import random
import subprocess
import sys
import time
import json
from datetime import datetime, timezone

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    HOOK_FONTSIZE, EXPL_FONTSIZE, DETAIL_FONTSIZE, MARGIN,
    EXPRESSIONS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])

IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
AUDIO_PATH = "background_music.mp3"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
POST_WIDTH, POST_HEIGHT = 1080, 1350   # Ratio 4:5 pour les posts feed
DELAY_ENTRE_IMAGES = 30

STRUCTURE_REEL = [
    {"acte": "ACCROCHE", "role": "Scène d'ouverture — capte l'attention immédiatement",
     "ambiance": "calme, mystérieuse, contemplative",
     "consigne_texte": "Une phrase d'accroche qui pose le décor ou une question",
     "consigne_image": "Plan large, ambiance calme et mystérieuse, le sujet vu de loin ou partiellement caché, atmosphère contemplative, lumière douce"},
    {"acte": "TENSION", "role": "Développement — crée la surprise ou la tension",
     "ambiance": "dynamique, intense, inattendue",
     "consigne_texte": "Un fait surprenant, un chiffre choc ou une révélation",
     "consigne_image": "Plan rapproché, ambiance dynamique et intense, le sujet au centre de l'action, éléments visuels percutants, contraste élevé"},
    {"acte": "RÉVÉLATION", "role": "Chute — la révélation finale qui marque l'esprit",
     "ambiance": "épique, lumineuse, mémorable",
     "consigne_texte": "La chute, la prédiction ou le message final percutant",
     "consigne_image": "Plan final épique, ambiance lumineuse et mémorable, le sujet révélé dans toute sa puissance, effet dramatique, lumière néon intense"},
]


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


def choisir_type_contenu() -> str:
    h = datetime.now(timezone.utc).hour
    if 6 <= h < 8:
        return "texte_seul"
    if 8 <= h < 12:
        return "image_texte"
    if 16 <= h < 20:
        return "reel"
    return random.choices(["reel", "image_texte", "texte_seul"], weights=[40, 35, 25], k=1)[0]


def choisir_pilier() -> str:
    return random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]


# ══════════════════════════════════════════════
#  FORMAT 1 : TEXTE SEUL (amélioré #Nyavodroid)
# ══════════════════════════════════════════════
def publier_texte_seul(pilier: str) -> dict:
    style = random.choice(STORY_PROMPTS)
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    prompt = (
        "Tu es Nyavodroid, la page tech qui révèle les mécanismes cachés du monde numérique.\n\n"
        f"Axe éditorial : {PILLARS[pilier]['label']}\nSujet imposé : {sujet}\nAngle : {style}\n\n"
        "Écris un post Facebook en respectant EXACTEMENT cette structure (blocs séparés par un saut de ligne vide) :\n\n"
        "BLOC 1 — HOOK : < 80 car., 1 emoji pertinent, phrase choc, pas de point final\n"
        "BLOC 2 — CONTEXTE : 1 à 5 phrases, exactement 1 terme technique précis (DNS, API, LLM, GPU...), ton " + TON_EDITORIAL + "\n"
        "BLOC 3 — QUESTION/CTA : UNE question binaire ou incitation au partage\n"
        "BLOC 4 — HASHTAGS : 2 ou 3 hashtags pertinents (sans compter #Nyavodroid)\n\n"
        "RÈGLES : pas de Markdown, pas d'astérisques, pas de guillemets, pas de titre, pas de numérotation, "
        "chaque bloc séparé par EXACTEMENT un saut de ligne vide. Interdit : généralités, banalités, pavés."
    )
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post texte)")

    # Ajout systématique de #Nyavodroid si absent
    if "#Nyavodroid" not in texte:
        texte += "\n\n#Nyavodroid"

    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}\n📌 Texte :\n{texte}\n")
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/feed"
    try:
        r = M._req("POST", ep, data={"message": texte, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Post texte publié — ID : {res['id']}")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "post texte") from e


# ══════════════════════════════════════════════
#  FORMAT 2 : IMAGE + TEXTE (refonte complète)
# ══════════════════════════════════════════════
def incruster_texte_hierarchique_post(image_in: str, hook: str, explication: str, detail: str, image_out: str) -> None:
    """
    Incruste les 3 niveaux de texte sur une image de ratio 4:5 (1080x1350).
    """
    # 1. Scale/crop pour garantir un 4:5 sans déformation
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", image_in
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w_orig, h_orig = map(int, out.stdout.strip().split(','))
        ratio_orig = w_orig / h_orig
        ratio_cible = POST_WIDTH / POST_HEIGHT
        if abs(ratio_orig - ratio_cible) > 0.05:
            scale_filter = (
                f"scale={POST_WIDTH}:{POST_HEIGHT}:force_original_aspect_ratio=decrease,"
                f"pad={POST_WIDTH}:{POST_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
            )
        else:
            scale_filter = (
                f"scale={POST_WIDTH}:{POST_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={POST_WIDTH}:{POST_HEIGHT}"
            )
    except Exception:
        scale_filter = (
            f"scale={POST_WIDTH}:{POST_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={POST_WIDTH}:{POST_HEIGHT}"
        )

    # 2. Préparation des textes
    hook_wrapped = wrap_text(hook, max_chars=20)
    expl_wrapped = wrap_text(explication, max_chars=35)
    detail_wrapped = wrap_text(detail, max_chars=45)

    hook_esc = escape_text(hook_wrapped)
    expl_esc = escape_text(expl_wrapped)
    detail_esc = escape_text(detail_wrapped)

    # 3. Filtres de texte (positions adaptées au canvas 1080x1350)
    # Hook : haut, centré, blanc, ombre magenta
    hook_y = f"{MARGIN}"
    hook_filtre = (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{hook_esc}':fontcolor=0xFFFFFF:fontsize={HOOK_FONTSIZE}:"
        f"x=(w-text_w)/2:y={hook_y}:"
        f"shadowcolor=0xEA4FD9@0.6:shadowx=0:shadowy=4"
    )

    # Explication : sous le hook
    expl_y = f"{MARGIN}+{HOOK_FONTSIZE}+25"
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

    filtre = f"{scale_filter},{hook_filtre}"
    if explication:
        filtre += f",{expl_filtre}"
    if detail:
        filtre += f",{detail_filtre}"

    # Image temporaire avec texte
    temp_text = "post_text.png"
    try:
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre, "-frames:v", "1", "-y", temp_text],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg texte post échec (code {e.returncode}) :\n{e.stderr[:500]}")

    # 4. Watermark d'expression
    M.overlay_expression(temp_text, image_out)
    if os.path.exists(temp_text):
        os.remove(temp_text)


def publier_image_texte(pilier: str) -> dict:
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # ----- Génération du texte structuré (JSON) -----
    prompt = (
        "Tu es Nyavodroid, la page tech qui révèle les mécanismes cachés du monde numérique.\n"
        f"Axe éditorial : {label}\n"
        f"Sujet imposé : {sujet}\n\n"
        "Génère UNIQUEMENT un objet JSON avec les clés suivantes :\n"
        '  "hook" : phrase d\'accroche choc (max 10 mots), commence par un emoji pertinent\n'
        '  "explication" : 2-3 lignes développant le hook, en langage simple\n'
        '  "detail" : une précision chiffrée, une source ou une note courte (1 ligne)\n'
        '  "legende_hook" : la phrase d\'accroche pour la légende (max 15 mots)\n'
        '  "legende_contexte" : 2-3 lignes expliquant le contexte\n'
        '  "legende_developpement" : 2-4 points ou lignes apportant de la valeur concrète\n'
        '  "legende_cta" : une question ou une incitation à l\'engagement\n'
        '  "hashtags" : 3 hashtags pertinents (sans #Nyavodroid, il sera ajouté automatiquement)\n\n'
        "Règles :\n"
        "- Pas de texte autour du JSON.\n"
        "- Ton : " + TON_EDITORIAL + "\n"
        "- Compréhensible par un débutant, pas de jargon inutile.\n"
        "- Le hook doit être percutant et donner envie de lire la suite.\n"
    )

    print(f"  📝 Génération texte + légende (JSON)...\n     Axe : {label}\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post json)")

    # Nettoyage Markdown éventuel
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]
    try:
        data = json.loads(brut.strip())
        hook = data.get("hook", "")
        explication = data.get("explication", "")
        detail = data.get("detail", "")
        legende_hook = data.get("legende_hook", "")
        legende_contexte = data.get("legende_contexte", "")
        legende_developpement = data.get("legende_developpement", "")
        legende_cta = data.get("legende_cta", "")
        hashtags = data.get("hashtags", "")
    except Exception:
        print("  ⚠️ Échec du parsing JSON, utilisation du texte brut comme légende.")
        # Fallback : on utilise tout le texte comme légende simple
        hook = explication = detail = ""
        legende_hook = brut
        legende_contexte = legende_developpement = legende_cta = ""
        hashtags = ""

    # Nettoyage
    hook = M.clean_text(hook)
    explication = M.clean_text(explication)
    detail = M.clean_text(detail)

    # Ajout d'un emoji au hook si absent
    if hook and not any(ord(c) > 127 for c in hook[:3]):
        emojis = ["💡", "🔍", "⚡", "🧠", "🤖", "🛡️", "🌐", "🔐", "💻", "🚀", "📡", "🧬"]
        hook = random.choice(emojis) + " " + hook

    # ----- Génération de l'image (4:5) -----
    prompt_img = (
        f"Illustration verticale 4:5 pour le sujet : {sujet}\n"
        f"Axe : {label}\nStyle : {STYLE_IMAGE_SUFFIX}"
    )
    print("  🖼️  Génération image 4:5...")
    M.image_avec_fallback(prompt_img, GEMINI_API_KEY, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT))

    # ----- Incrustation du texte hiérarchisé + watermark -----
    if hook or explication or detail:
        print("  🎨 Incrustation du texte + watermark sur l'image...")
        incruster_texte_hierarchique_post(IMAGE_PATH, hook, explication, detail, IMAGE_PATH)
    else:
        # Si pas de texte hiérarchique, on applique juste le watermark
        print("  🎭 Application du watermark seul...")
        M.overlay_expression(IMAGE_PATH, IMAGE_PATH)

    # ----- Assemblage de la légende finale -----
    legende_parts = []
    if legende_hook:
        legende_parts.append(legende_hook)
    if legende_contexte:
        legende_parts.append(legende_contexte)
    if legende_developpement:
        legende_parts.append(legende_developpement)
    if legende_cta:
        legende_parts.append(legende_cta)

    hashtags_finaux = hashtags.strip()
    if "#Nyavodroid" not in hashtags_finaux:
        hashtags_finaux += " #Nyavodroid"
    legende_parts.append(hashtags_finaux.strip())

    legende_finale = "\n\n".join(legende_parts)

    print(f"\n📌 Axe      : {label}\n📌 Sujet    : {sujet}\n📌 Légende  :\n{legende_finale}\n")

    # ----- Publication -----
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(IMAGE_PATH, "rb") as f:
            r = M._req("POST", ep,
                       data={"caption": legende_finale, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(IMAGE_PATH), f, "image/png")}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Image+Texte publié — ID : {res['id']}")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "photo + légende") from e
    except OSError as e:
        raise RuntimeError(f"Fichier image illisible : {e}") from e


# ══════════════════════════════════════════════
#  FIN DE LA PARTIE 1 — LA PARTIE 2 CONTIENT LE FORMAT REEL ET LE MAIN
# ══════════════════════════════════════════════