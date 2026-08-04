#!/usr/bin/env python3
"""
Nyavodroid — publication multi-formats (texte / image+texte / Reel).
Intégration Pexels vs IA, rendu texte Pillow (lisibilité garantie), watermark double.
"""

import os
import random
import subprocess
import sys
import time
import json
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    MARGIN, DETAIL_FONTSIZE,
    POST_WIDTH, POST_HEIGHT, STORY_WIDTH, STORY_HEIGHT,
    EXPRESSIONS_DIR, PROFILE_IMAGE_PATH, EMOJIS_DIR
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])

IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
AUDIO_PATH = "background_music.mp3"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
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
def clean_backslash(t: str) -> str:
    """Supprime les backslashes parasites qui pourraient apparaître dans le texte."""
    return t.replace("\\", "")

def choisir_type_contenu() -> str:
    """Décide du format en priorisant la stratégie NAnaly, fallback sur l'heure."""
    from charger_strategie import charger_strategie
    strategie = charger_strategie()

    # Priorité 1 : format imposé par NAnaly
    if strategie.format_prefere:
        mapping = {
            "photo": "image_texte",
            "image_texte": "image_texte",
            "texte_seul": "texte_seul",
            "video": "image_texte",  # video → image_texte car Reels désactivés
            "reel": "image_texte",    # reel → image_texte car désactivé
            "story": "image_texte",
            "carousel": "image_texte"
        }
        fmt = mapping.get(strategie.format_prefere, "image_texte")
        print(f"  🎯 Format imposé par NAnaly : {strategie.format_prefere} → {fmt}")
        return fmt

    # Priorité 2 : fallback horaire (comportement actuel)
    h = datetime.now(timezone.utc).hour
    if 6 <= h < 8:
        return "texte_seul"
    if 8 <= h < 12:
        return "image_texte"
    if 16 <= h < 20:
        return "image_texte"
    return random.choices(["image_texte", "texte_seul"], weights=[60, 40], k=1)[0]


def choisir_pilier() -> str:
    """Choisit un pilier en priorisant les sujets tendance de NAnaly."""
    from charger_strategie import charger_strategie
    strategie = charger_strategie()

    # Si NAnaly a identifié des sujets tendance, on essaie de matcher avec un pilier
    if strategie.sujets_a_explorer:
        sujet_tendance = random.choice(strategie.sujets_a_explorer)
        print(f"  🔥 Sujet tendance NAnaly détecté : {sujet_tendance}")
        # On stocke le sujet tendance pour qu'il soit utilisé plus tard
        # (via une variable globale simple ou un attribut)
        global _SUJET_TENDANCE_NANALY
        _SUJET_TENDANCE_NANALY = sujet_tendance

    # Fallback : choix pondéré classique
    return random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]


# Variable globale pour passer le sujet tendance entre choisir_pilier() et generer_*()
_SUJET_TENDANCE_NANALY: Optional[str] = None


# ══════════════════════════════════════════════
#  FORMAT 1 : TEXTE SEUL (fond Pillow)
# ══════════════════════════════════════════════
def generer_post_texte_seul(pilier: str) -> tuple[str, str]:
    global _SUJET_TENDANCE_NANALY
    if _SUJET_TENDANCE_NANALY:
        sujet = _SUJET_TENDANCE_NANALY
        _SUJET_TENDANCE_NANALY = None  # Reset après utilisation
        print(f"  🎯 Sujet imposé par NAnaly : {sujet}")
    else:
        sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    
    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français et EXTRÊMEMENT COURT :\n"
        "1 phrase de contexte + 1 fait choc avec un chiffre, maximum 15 mots.\n"
        f"Sujet : {sujet}. {TON_EDITORIAL}"
    )
    print(f"  📝 Génération texte post seul...\n     Sujet : {sujet}")
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post texte)")
    texte = M.clean_text(texte)
    texte = clean_backslash(texte)
    print(f"  ✅ Texte : « {texte} »")

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
#  FORMAT 2 : IMAGE + TEXTE (Pexels/IA, hiérarchie Pillow, watermark)
# ══════════════════════════════════════════════
def incruster_texte_hierarchique_post(image_in, contexte, fait_choc, consequence, source, image_out):
    """Incrustation hiérarchique Pillow (post 1080x1350), puis watermark profil+expression."""
    M.incruster_texte_pillow(image_in, contexte, fait_choc, consequence, source,
                             image_out, target_size=(POST_WIDTH, POST_HEIGHT))
    # Watermark profil + expression uniquement (la source est déjà rendue par Pillow)
    M.overlay_watermark(image_out, image_out, source_text="")

def publier_image_texte(pilier: str) -> dict:
    label = PILLARS[pilier]["label"]
    global _SUJET_TENDANCE_NANALY
    
    if _SUJET_TENDANCE_NANALY:
        sujet = _SUJET_TENDANCE_NANALY
        _SUJET_TENDANCE_NANALY = None  # Reset après utilisation
        print(f"  🎯 Sujet imposé par NAnaly : {sujet}")
    else:
        sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    
    # Détection des sujets à risque (génèrent du texte parasite en IA)
    TEXT_TRIGGER_WORDS = ["code", "compiler", "traduction", "translation", "language", "langage", 
                          "database", "sql", "json", "api", "interface", "ui", "screen", "écran",
                          "llm", "ia", "ai", "model", "modèle", "network", "réseau"]
    force_pexels = any(word in sujet.lower() for word in TEXT_TRIGGER_WORDS)

    prompt = (
        "Tu es Nyavodroid, expert fact-checker. Contenu 100% vérifié obligatoire.\n\n"
        "ÉTAPE 1 — Génère contexte + fait_choc + conséquence + description.\n"
        "ÉTAPE 2 — Auto-vérification (3 questions) :\n"
        "  Q1: Source réelle et accessible ?\n"
        "  Q2: Chiffres/années cohérents avec la réalité ?\n"
        "  Q3: image_prompt techniquement exact ET sans aucun texte ?\n"
        "       (NoSQL≠JSON, HTTP/3≠TCP, CDN≠serveur unique, ZÉRO caractères dans l'image)\n"
        "ÉTAPE 3 — Corrige si nécessaire avant de répondre.\n\n"
        "RÈGLES :\n"
        "- Jamais de chiffre inventé. Année ≤ 2024.\n"
        "- Source obligatoire : organisme réel + année ≤ 2024.\n"
        '- image_prompt EN ANGLAIS. CRITICAL: absolutely zero text, letters, words, numbers, or typography in the image. '
        'If the subject involves code, translation, or data, use ONLY abstract visual metaphors (glowing neural networks, light streams, geometric shapes). '
        'NEVER generate fake text, gibberish, or UI elements with characters.\n'
        '- Si non vérifiable : {"erreur": "fait non vérifiable"}.\n\n'
        "Réponds EXACTEMENT en JSON :\n"
        '{"contexte": "1 phrase (10-15 mots)", '
        '"fait_choc": "fait/chiffre surprenant (max 8 mots, mots clés entre **)", '
        '"consequence": "1 phrase courte (10-15 mots)", '
        '"description": "2 phrases développées (30-40 mots)", '
        '"visuel": "concret ou conceptuel", '
        '"image_prompt": "EN ANGLAIS, scène techniquement exacte, ZÉRO texte, métaphores abstraites si tech", '
        '"source": "organisme réel + année ≤ 2024"}\n\n'
        f"Sujet imposé : {sujet}."
    )

    print(f"  📝 Génération post image...\n     Sujet : {sujet}")
    if force_pexels:
        print(f"  ⚠️ Sujet à risque texte détecté → Pexels sera forcé")

    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post json)").strip()
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]

    try:
        d = json.loads(brut)
        if "erreur" in d:
            raise ValueError(d["erreur"])
        contexte, fait_choc = d.get("contexte", ""), d.get("fait_choc", "")
        consequence, description = d.get("consequence", ""), d.get("description", "")
        source, visuel, image_prompt = d.get("source", ""), d.get("visuel", "conceptuel"), d.get("image_prompt", "")

        # Force Pexels si sujet à risque, même si l'IA a dit "conceptuel"
        if force_pexels:
            visuel = "concret"

    except Exception as e:
        print(f"  ⚠️ Vérification échouée ou JSON invalide : {e}")
        contexte, fait_choc, consequence, description, source = "Fait non vérifiable.", "", "", "", ""
        visuel, image_prompt = "conceptuel", ""

    # ----- Image : réel si concret ou sujet à risque, IA alignée sinon -----
    img_prompt = image_prompt or f"abstract visual metaphor for {sujet}, no text"

    # Double sécurité : tentative Pexels forcée pour les sujets tech
    if any(word in sujet.lower() for word in TEXT_TRIGGER_WORDS):
        print(f"  🖼️ [Pexels] Tentative forcée (sujet à risque texte) : {sujet}")
        if M.get_image_from_pexels(sujet, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT)):
            print("  ✅ [Pexels] photo réelle utilisée (texte évité)")
        elif visuel == "concret":
            print("  ⚠️ [Pexels] échec → IA avec métaphores abstraites")
            M.image_avec_fallback(img_prompt, GEMINI_API_KEY, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT))
        else:
            print("  🎨 [IA] visuel conceptuel (métaphores abstraites, zéro texte)")
            M.image_avec_fallback(img_prompt, GEMINI_API_KEY, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT))
    elif visuel == "concret":
        print(f"  🖼️ [Pexels] photo réelle : {sujet}")
        if not M.get_image_from_pexels(sujet, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT)):
            print("  ⚠️ [Pexels] échec → IA avec métaphores abstraites")
            M.image_avec_fallback(img_prompt, GEMINI_API_KEY, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT))
    else:
        print("  🎨 [IA] visuel conceptuel (métaphores abstraites, zéro texte)")
        M.image_avec_fallback(img_prompt, GEMINI_API_KEY, IMAGE_PATH, size=(POST_WIDTH, POST_HEIGHT))

    # ----- Incrustation -----
    if fait_choc or consequence:
        incruster_texte_hierarchique_post(IMAGE_PATH, contexte, fait_choc, consequence, source, IMAGE_PATH)
    else:
        M.overlay_watermark(IMAGE_PATH, IMAGE_PATH, source_text="")

    # ----- Légende développée -----
    legende_finale = f"{contexte}\n\n{fait_choc.replace('**','')}\n\n{description}\n\nSource : {source}\n\n#Nyavodroid"
    print(f"\n📌 Sujet : {sujet}\n📌 Légende :\n{legende_finale}\n")

    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(IMAGE_PATH, "rb") as f:
            r = M._req("POST", ep, data={"caption": legende_finale, "access_token": M.FB_PAGE_ACCESS_TOKEN},
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
#  FORMAT 3 : REEL — génération des phrases
# ══════════════════════════════════════════════
def _generer_phrases_reel(pilier: str):
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    actes_desc = ""
    for i, a in enumerate(STRUCTURE_REEL, 1):
        actes_desc += f"Acte {i} — {a['acte']} : {a['role']}\n  → {a['consigne_texte']}\n"

    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français.\n"
        f"Axe : {label}\nSujet : {sujet}\n"
        f"Pour chaque acte, donne un 'hook' (phrase choc < 10 mots) et un 'detail' (< 5 mots).\n"
        "Réponds par un tableau JSON : [{\"hook\":\"...\", \"detail\":\"...\"}, ...]\n"
        f"{TON_EDITORIAL}"
    )
    print(f"  📝 Génération phrases Reel...")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, f"(Reel : {sujet})")
    brut = brut.strip()
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]
    try:
        data = json.loads(brut)
        hooks, details = [], []
        for item in data[:NB_IMAGES_REEL]:
            hooks.append(item.get("hook", ""))
            details.append(item.get("detail", ""))
        if len(hooks) < NB_IMAGES_REEL:
            raise ValueError("Pas assez")
    except:
        # fallback : phrases numérotées
        prompt2 = (
            "En français, génère trois phrases numérotées de 10 mots max.\n"
            f"Sujet : {sujet}\n1.\n2.\n3."
        )
        brut2 = M.texte_avec_fallback(prompt2, GEMINI_API_KEY, "(fallback reel)")
        hooks = []
        details = []
        for ligne in brut2.split("\n"):
            if ligne.strip() and ligne[0].isdigit():
                p = M.clean_text(ligne.split(".", 1)[1].strip())
                if p:
                    hooks.append(p)
                    details.append("")
    return sujet, hooks[:NB_IMAGES_REEL], details[:NB_IMAGES_REEL]


def incruster_texte_reel_pillow(image_in, hook, detail, image_out):
    """Incruste le hook (grand, centré) et le détail (bas) sur une image de Reel 1080x1920."""
    w, h = STORY_WIDTH, STORY_HEIGHT
    img = Image.open(image_in).convert("RGBA")
    img = M._crop_resize_pillow(img, (w, h))
    draw = ImageDraw.Draw(img)
    x_center = w / 2
    max_width = w - 2 * M.MARGIN

    hook = M.clean_text(hook) if hook else ""
    detail = M.clean_text(detail) if detail else ""

    font_hook = M.get_font(68, bold=True)
    font_detail = M.get_font(DETAIL_FONTSIZE, bold=False)
    usable_width = max_width - 2 * M.BOX_BORDER

    # HOOK — grand, centré dans la moitié haute
    if hook:
        hook_lines = M.wrap_text_pillow(hook, font_hook, usable_width)
        h_hook = M._measure_block_height(hook_lines, font_hook, M.BOX_BORDER)
        y_hook = int(h * 0.38) - h_hook // 2
        M.draw_text_block(img, draw, hook_lines, font_hook, x_center, y_hook,
                          M.COLORS["blanc"], box_color=M.BOX_BG["noir_translucide"])

    # DETAIL — petit, en bas au-dessus de la marge
    if detail:
        detail_lines = M.wrap_text_pillow(detail, font_detail, usable_width)
        h_detail = M._measure_block_height(detail_lines, font_detail, M.BOX_BORDER)
        y_detail = h - M.MARGIN - h_detail
        M.draw_text_block(img, draw, detail_lines, font_detail, x_center, y_detail,
                          M.COLORS["blanc"], box_color=M.BOX_BG["noir_translucide"])

    img.convert("RGB").save(image_out)
# ══════════════════════════════════════════════
#  FORMAT 3 : REEL — images, audio, assemblage, publication
# ══════════════════════════════════════════════
def _generer_images_reel(pilier: str, hooks: list, details: list, sujet: str) -> list:
    """Génère les images de chaque scène en 9:16, avec incrustation Pillow et watermark."""
    label = PILLARS[pilier]["label"]
    categorie = PILLARS[pilier].get("categorie", "tech")
    use_pexels = (categorie != "tech")

    chemins = []
    for i, (hook, detail) in enumerate(zip(hooks, details), 1):
        chemin = f"reel_img_{i}.png"
        ctx = ""
        if i > 1:
            ctx += f"Scène précédente : « {hooks[i-2]} »\n"
        if i < len(hooks):
            ctx += f"Scène suivante : « {hooks[i]} »\n"

        acte = STRUCTURE_REEL[i-1]
        prompt = (
            f"Scène {i}/{NB_IMAGES_REEL} d'une mini-histoire visuelle en 3 actes.\n"
            f"Sujet global : {sujet}\nAxe : {label}\n\n"
            f"ACTE {i} — {acte['acte']} : {acte['role']}\n"
            f"Texte affiché : « {hook} »\n"
            f"Détail : « {detail} »\n"
            f"Ambiance : {acte['ambiance']}\n"
            f"Cadrage : {acte['consigne_image']}\n\n"
        )
        if ctx:
            prompt += f"Continuité narrative :\n{ctx}\n"
        prompt += f"Style : {STYLE_IMAGE_SUFFIX}\nIMPORTANT : cohérence visuelle."

        if i > 1:
            pause = DELAY_ENTRE_IMAGES + random.uniform(0, 10)
            print(f"  ⏳ Pause anti-rate-limit : {pause:.0f}s...")
            time.sleep(pause)

        print(f"  🖼️  Scène {i}/{NB_IMAGES_REEL} [{acte['acte']}]...")

        pexels_query = sujet if use_pexels else ""
        M.image_avec_fallback(
            prompt if not use_pexels else "",
            GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT),
            use_pexels=use_pexels, pexels_query=pexels_query
        )

        # Incrustation du texte (hook + détail) via Pillow
        incruster_texte_reel_pillow(chemin, hook, detail, chemin)

        # Appliquer le watermark profil + expression (sans source)
        watermarked = f"reel_img_wm_{i}.png"
        M.overlay_watermark(chemin, watermarked, source_text="")
        os.replace(watermarked, chemin)

        chemins.append(chemin)
    return chemins


def _generer_audio_reel(pilier: str) -> None:
    prompt = ("Dark synthwave cyber ambient instrumental, deep analog bass, neon atmosphere, "
              "cinematic tension, retro-futuristic, no vocals, no speech")
    print("  🎵 Génération musique de fond (best-effort)...")
    M.audio_avec_fallback(prompt, AUDIO_PATH)


def _assembler_video(images: list, textes: list, sortie: str) -> None:
    audio_existe = os.path.exists(AUDIO_PATH)
    duree_totale = len(images) * DUREE_PAR_IMAGE

    if not audio_existe:
        print("  🔇 'background_music.mp3' absent → génération silence AAC...")
        silence_aac = "silence.m4a"
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", str(duree_totale), "-c:a", "aac", "-b:a", "128k", "-y", silence_aac],
            check=True, capture_output=True, text=True
        )
        audio_source = silence_aac
    else:
        audio_source = AUDIO_PATH

    inputs = []
    for img in images:
        inputs += ["-loop", "1", "-t", str(DUREE_PAR_IMAGE), "-i", img]
    inputs += ["-i", audio_source]
    n = len(images)

    filtres = []
    for i in range(n):
        filtres.append(
            f"[{i}:v]scale={STORY_WIDTH}:{STORY_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={STORY_WIDTH}:{STORY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
            f"format=yuv420p,"
            f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(DUREE_PAR_IMAGE*25)}:s={STORY_WIDTH}x{STORY_HEIGHT}:fps=25,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={DUREE_PAR_IMAGE-0.5}:d=0.5[scene{i}]")
    filtres.append("".join(f"[scene{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[slideshow]")
    filtres.append("[slideshow]null[final]")

    cmd = ["ffmpeg", *inputs, "-filter_complex", ";".join(filtres),
           "-map", "[final]", "-map", f"{n}:a",
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
           "-t", str(duree_totale), "-y", sortie]
    try:
        print("  🎬 Assemblage vidéo ffmpeg...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"  ✅ Vidéo : {sortie} ({os.path.getsize(sortie):,} o)")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec : {e.stderr[:800]}")

def publier_reel(pilier: str) -> dict:
    sujet, hooks, details = _generer_phrases_reel(pilier)
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}")
    print(f"📌 Storytelling Reel ({NB_IMAGES_REEL} actes) :")
    for i, (h, d) in enumerate(zip(hooks, details), 1):
        print(f"   {i}. [{STRUCTURE_REEL[i-1]['acte']}] {h} | {d}")

    images = _generer_images_reel(pilier, hooks, details, sujet)
    _generer_audio_reel(pilier)
    _assembler_video(images, hooks, REEL_VIDEO_PATH)

    legende = " ".join(hooks)[:500] + "\n\n#Nyavodroid"

    # ✅ Endpoint /videos (fonctionne avec tes permissions actuelles)
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/videos"
    
    try:
        print("  📤 Vidéo — upload direct via /videos...")
        with open(REEL_VIDEO_PATH, "rb") as f:
            r = M._req("POST", ep,
                       data={"description": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(REEL_VIDEO_PATH), f, "video/mp4")},
                       timeout=300)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Vidéo publiée — ID : {res['id']}")
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "vidéo") from e
    except OSError as e:
        raise RuntimeError(f"Fichier vidéo illisible : {e}") from e


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main() -> None:
    print("=" * 60)
    print("🎬 Nyavodroid — Multi-formats [Premium]")
    print("=" * 60)
    M.verify_fb_token()
    tc = choisir_type_contenu()
    pilier = choisir_pilier()
    labels = {"texte_seul": "📝 Texte seul (image)", "image_texte": "🖼️  Image + Texte", "reel": "🎬 Reel vidéo"}
    print(f"\n📌 Format : {labels[tc]}\n📌 Pilier : {PILLARS[pilier]['label']}"
          f"\n📌 Heure  : {datetime.now(timezone.utc).strftime('%H:%M UTC')}\n")
    if tc == "texte_seul":
        res = publier_texte_seul(pilier)
    elif tc == "image_texte":
        res = publier_image_texte(pilier)
    else:
        res = publier_reel(pilier)
    print(f"\n{'='*60}\n✅ TERMINÉ — {labels[tc]}\n   ID : {res.get('id', res.get('video_id','N/A'))}\n{'='*60}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        print(f"\n❌ ERREUR : {e}", file=sys.stderr); sys.exit(1)
    except KeyError as e:
        print(f"\n❌ Secret manquant : {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"\n❌ Inattendu : {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)