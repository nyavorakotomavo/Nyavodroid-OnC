#!/usr/bin/env python3
"""
Nyavodroid — publication multi-formats (texte / image+texte / Reel).
Intégration Pexels vs IA, post texte seul en image, watermark double.
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
    EXPRESSIONS_DIR, PROFILE_IMAGE_PATH, EMOJIS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])

IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
AUDIO_PATH = "background_music.mp3"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
POST_WIDTH, POST_HEIGHT = 1080, 1350       # ratio 4:5
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
    """Échappe les caractères spéciaux pour ffmpeg drawtext."""
    return t.replace("'", "\\'").replace(":", "\\:").replace("%", "%%").replace("\\", "\\\\")


def clean_backslash(t: str) -> str:
    """Supprime les backslashes parasites qui pourraient apparaître dans le texte."""
    return t.replace("\\", "")


def count_lines(text: str) -> int:
    """Retourne le nombre de lignes d'un texte wrappé (séparateur \\n)."""
    if not text:
        return 0
    return text.count("\n") + 1


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
#  FORMAT 1 : TEXTE SEUL (nouveau : fond Pillow)
# ══════════════════════════════════════════════
def generer_post_texte_seul(pilier: str) -> (str, str):
    """Génère un texte engageant et l'image de fond correspondante.
    Retourne (texte, chemin_image)."""
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    style = random.choice(STORY_PROMPTS)
    prompt = (
        f"Tu es Nyavodroid. Rédige une question courte et engageante pour les abonnés "
        f"sur le thème suivant : {sujet}. "
        f"Ton : {TON_EDITORIAL}. "
        "Maximum 15 mots. Pas de hashtags, pas de lien. "
        "Juste la question, sans guillemets, sans signature."
    )
    print(f"  📝 Génération texte post seul...\n     Sujet : {sujet}")
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post texte)")
    texte = M.clean_text(texte)
    # Nettoyage backslash
    texte = clean_backslash(texte)
    print(f"  ✅ Texte : « {texte} »")

    # Génération de l'image de fond avec Pillow
    chemin_image = "post_text_image.png"
    M.generer_fond_texte_seul(texte, chemin_image)
    return texte, chemin_image


def publier_texte_seul(pilier: str) -> dict:
    texte, image_path = generer_post_texte_seul(pilier)
    # Légende minimale avec #Nyavodroid
    legende = f"{texte}\n\n#Nyavodroid"

    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : (post texte seul)\n📌 Texte : {texte}\n")

    # Publication comme photo
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(image_path, "rb") as f:
            r = M._req("POST", ep,
                       data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(image_path), f, "image/png")},
                       timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Post texte (image) publié — ID : {res['id']}")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "post texte") from e
    except OSError as e:
        raise RuntimeError(f"Fichier image illisible : {e}") from e


# ══════════════════════════════════════════════
#  FORMAT 2 : IMAGE + TEXTE (Pexels/IA, hiérarchie, watermark)
# ══════════════════════════════════════════════
def _get_emoji_path(emoji_char: str) -> str | None:
    """Cherche une image PNG correspondant à l'emoji dans assets/emojis/."""
    # On peut mapper les emojis courants vers des fichiers
    # Pour l'instant, on essaie le nom directement (ex: 🔍.png)
    emoji_filename = emoji_char + ".png"
    path = os.path.join(EMOJIS_DIR, emoji_filename)
    if os.path.isfile(path):
        return path
    # Sinon, on essaie de prendre le premier emoji dispo
    if os.path.isdir(EMOJIS_DIR):
        for f in os.listdir(EMOJIS_DIR):
            if f.endswith(".png"):
                return os.path.join(EMOJIS_DIR, f)
    return None


def incruster_texte_hierarchique_post(image_in: str, hook: str, explication: str, detail: str, image_out: str) -> None:
    """
    Incruste les 3 niveaux de texte sur une image 4:5 avec positions dynamiques (anti-chevauchement).
    """
    # 1. Scale/crop pour garantir le ratio 4:5
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
                f"pad={POST_WIDTH}:{POST_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
                "format=rgba"
            )
        else:
            scale_filter = (
                f"scale={POST_WIDTH}:{POST_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={POST_WIDTH}:{POST_HEIGHT},"
                "format=rgba"
            )
    except Exception:
        scale_filter = (
            f"scale={POST_WIDTH}:{POST_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={POST_WIDTH}:{POST_HEIGHT},"
            "format=rgba"
        )

    # 2. Nettoyage des textes
    hook = clean_backslash(hook)
    explication = clean_backslash(explication)
    detail = clean_backslash(detail)

    # 3. Extraction de l'emoji du début du hook (s'il y en a un)
    emoji_char = None
    if hook and ord(hook[0]) > 127:
        # On considère que le premier caractère est un emoji (unicode non ASCII)
        emoji_char = hook[0]
        hook = hook[1:].strip()
    # Si le hook commence par un emoji après un espace, on le capture aussi
    if not emoji_char and hook and ord(hook[0]) > 127:
        emoji_char = hook[0]
        hook = hook[1:].strip()

    emoji_path = _get_emoji_path(emoji_char) if emoji_char else None

    # 4. Wrapping des textes
    # On limite la largeur pour tenir dans les marges
    max_chars_hook = 18
    max_chars_expl = 30
    max_chars_detail = 40
    hook_wrapped = wrap_text(hook, max_chars_hook)
    expl_wrapped = wrap_text(explication, max_chars_expl)
    detail_wrapped = wrap_text(detail, max_chars_detail)

    hook_esc = escape_text(hook_wrapped) if hook_wrapped else ""
    expl_esc = escape_text(expl_wrapped) if expl_wrapped else ""
    detail_esc = escape_text(detail_wrapped) if detail_wrapped else ""

    # 5. Calcul des positions Y dynamiques
    # Hauteur d'une ligne approximative pour chaque taille (en px)
    line_hook = int(HOOK_FONTSIZE * 1.3)
    line_expl = int(EXPL_FONTSIZE * 1.3)
    line_detail = int(DETAIL_FONTSIZE * 1.3)

    y_hook = MARGIN
    nb_lignes_hook = count_lines(hook_wrapped) if hook_wrapped else 0
    hauteur_hook = nb_lignes_hook * line_hook

    y_expl = y_hook + hauteur_hook + 20  # marge entre hook et explication
    nb_lignes_expl = count_lines(expl_wrapped) if expl_wrapped else 0
    hauteur_expl = nb_lignes_expl * line_expl

    # Détail en bas
    y_detail = POST_HEIGHT - MARGIN - line_detail

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

    filtre_texte = ",".join([scale_filter] + filtres)

    # 7. Image temporaire après incrustation texte
    temp_text = "post_text_incrust.png"
    try:
        subprocess.run(
            ["ffmpeg", "-i", image_in, "-vf", filtre_texte, "-frames:v", "1", "-y", temp_text],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg texte post échec (code {e.returncode}) :\n{e.stderr[:500]}")

    # 8. Si emoji disponible, on le superpose au-dessus du hook (en haut à gauche du hook)
    if emoji_path:
        # Position : à gauche du hook, centré verticalement avec la première ligne du hook
        emoji_size = 80  # un peu plus petit que le hook
        emoji_x = (POST_WIDTH - 500) // 2  # approximation, on pourrait centrer avec le texte mais on simplifie
        # On va plutôt centrer l'emoji à gauche de la zone de texte, aligné sur y_hook
        # On calcule la largeur approximative du hook
        # On utilise ffprobe pour obtenir la largeur du texte? Pas possible. On peut centrer l'emoji avec le hook en utilisant overlay.
        # On va faire un filtre supplémentaire: on crée une entrée pour l'emoji, on le redimensionne et on l'overlay à une position approximative.
        emo_filter = (
            f"[1:v]scale={emoji_size}:-1[emo];"
            f"[0:v][emo]overlay=400:{y_hook + (line_hook - emoji_size)//2}"
        )
        temp_emo = "post_text_emo.png"
        try:
            subprocess.run(
                ["ffmpeg", "-i", temp_text, "-i", emoji_path,
                 "-filter_complex", emo_filter,
                 "-frames:v", "1", "-y", temp_emo],
                check=True, capture_output=True, text=True
            )
            os.replace(temp_emo, temp_text)
        except subprocess.CalledProcessError:
            # Si l'overlay emoji échoue, on garde sans
            pass

    # 9. Watermark double (expression + profil)
    M.overlay_watermark(temp_text, image_out)
    if os.path.exists(temp_text):
        os.remove(temp_text)


def publier_image_texte(pilier: str) -> dict:
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    categorie = PILLARS[pilier].get("categorie", "tech")

    # --- Génération du contenu structuré (JSON) ---
    prompt = (
        "Tu es Nyavodroid, la page tech premium.\n"
        f"Axe : {label}\nSujet : {sujet}\n\n"
        "Génère UNIQUEMENT un JSON avec les clés :\n"
        "  \"hook\" : accroche choc (max 10 mots), commence par un emoji pertinent\n"
        "  \"explication\" : 2-3 lignes simples, valeur concrète\n"
        "  \"detail\" : précision chiffrée ou source (1 ligne)\n"
        "  \"legende_hook\" : phrase d'accroche pour la légende (max 15 mots)\n"
        "  \"legende_contexte\" : 2-3 lignes de contexte\n"
        "  \"legende_developpement\" : 2-4 points de valeur\n"
        "  \"legende_cta\" : question ou appel à l'engagement\n"
        "  \"hashtags\" : 3 hashtags (sans #Nyavodroid, ajouté automatiquement)\n\n"
        "Règles : pas de texte hors JSON, ton " + TON_EDITORIAL
    )
    print(f"  📝 Génération contenu post image...\n     Axe : {label}\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post json)")
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
        legende_hook = data.get("legende_hook", "")
        legende_contexte = data.get("legende_contexte", "")
        legende_developpement = data.get("legende_developpement", "")
        legende_cta = data.get("legende_cta", "")
        hashtags = data.get("hashtags", "")
    except Exception:
        # Fallback : on utilise tout le texte brut comme légende simple
        print("  ⚠️ JSON invalide, fallback légende simple.")
        hook = explication = detail = ""
        legende_hook = brut
        legende_contexte = legende_developpement = legende_cta = ""
        hashtags = ""

    # Nettoyage
    hook = M.clean_text(hook)
    explication = M.clean_text(explication)
    detail = M.clean_text(detail)

    # --- Choix de la source d'image ---
    use_pexels = (categorie != "tech")  # non-tech = Pexels
    if use_pexels:
        # On utilisera la fonction image_avec_fallback avec use_pexels=True
        pexels_query = sujet
        prompt_img = ""  # pas utilisé
    else:
        prompt_img = (
            f"Illustration verticale 4:5 pour le sujet : {sujet}\n"
            f"Axe : {label}\nStyle : {STYLE_IMAGE_SUFFIX}"
        )
        pexels_query = ""

    print(f"  🖼️  Source image : {'Pexels' if use_pexels else 'IA'}...")
    M.image_avec_fallback(
        prompt_img, GEMINI_API_KEY, IMAGE_PATH,
        size=(POST_WIDTH, POST_HEIGHT),
        use_pexels=use_pexels, pexels_query=pexels_query
    )

    # --- Incrustation du texte hiérarchique + watermark ---
    if hook or explication or detail:
        print("  🎨 Incrustation texte + watermark double...")
        incruster_texte_hierarchique_post(IMAGE_PATH, hook, explication, detail, IMAGE_PATH)
    else:
        # Même sans texte, on applique le watermark double
        M.overlay_watermark(IMAGE_PATH, IMAGE_PATH)

    # --- Assemblage légende ---
    parts = []
    if legende_hook:
        parts.append(legende_hook)
    if legende_contexte:
        parts.append(legende_contexte)
    if legende_developpement:
        parts.append(legende_developpement)
    if legende_cta:
        parts.append(legende_cta)
    hashtags_finaux = hashtags.strip()
    if "#Nyavodroid" not in hashtags_finaux:
        hashtags_finaux += " #Nyavodroid"
    parts.append(hashtags_finaux.strip())
    legende_finale = "\n\n".join(parts)

    print(f"\n📌 Axe : {label}\n📌 Sujet : {sujet}\n📌 Légende :\n{legende_finale}\n")

    # --- Publication ---
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(IMAGE_PATH, "rb") as f:
            r = M._req("POST", ep,
                       data={"caption": legende_finale, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(IMAGE_PATH), f, "image/png")},
                       timeout=M.TIMEOUT)
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