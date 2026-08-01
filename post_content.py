#!/usr/bin/env python3
"""
Nyavodroid — publication multi-formats (texte / image+texte / Reel).
Logique métier uniquement ; texte/image/audio viennent de nyavo_media.
Secrets : FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, GEMINI_API_KEY_CONTENT,
          MISTRAL_API_KEY, TOGETHER_API_KEY, HF_TOKEN, REPLICATE_API_TOKEN,
          FAL_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
"""

import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, STORY_PROMPTS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])

IMAGE_PATH = "post_image.png"
REEL_VIDEO_PATH = "reel_video.mp4"
AUDIO_PATH = "background_music.mp3"
SILENT_AUDIO_PATH = "silence.mp3"
NB_IMAGES_REEL = 3
DUREE_PAR_IMAGE = 3.5
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
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


# ── FORMAT 1 : TEXTE SEUL ──
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
        "BLOC 4 — HASHTAGS : 2 ou 3 hashtags pertinents\n\n"
        "RÈGLES : pas de Markdown, pas d'astérisques, pas de guillemets, pas de titre, pas de numérotation, "
        "chaque bloc séparé par EXACTEMENT un saut de ligne vide. Interdit : généralités, banalités, pavés."
    )
    texte = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "(post texte)")
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


# ── FORMAT 2 : IMAGE + TEXTE ──
def publier_image_texte(pilier: str) -> dict:
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    prompt_leg = (f"Tu es Nyavodroid.\nAxe : {label}\nSujet : {sujet}\n"
                  f"Écris une légende Facebook de 2-3 lignes en français.\nTon : {TON_EDITORIAL}\n"
                  f"Termine par 2-3 hashtags.\nPas de guillemets, pas de Markdown.")
    legende = M.texte_avec_fallback(prompt_leg, GEMINI_API_KEY, "(légende)")
    prompt_img = (f"Illustration verticale 9:16 sur le sujet : {sujet}\n"
                  f"Axe : {label}\nStyle : {STYLE_IMAGE_SUFFIX}")
    print("  🖼️  Génération image...")
    M.image_avec_fallback(prompt_img, GEMINI_API_KEY, IMAGE_PATH)
    print(f"\n📌 Axe    : {label}\n📌 Sujet  : {sujet}\n📌 Légende :\n{legende}\n")
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(IMAGE_PATH, "rb") as f:
            r = M._req("POST", ep,
                       data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
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


# ── FORMAT 3 : REEL ──
def _generer_phrases_reel(pilier: str):
    label = PILLARS[pilier]["label"]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    actes_desc = "".join(f"Acte {i} — {a['acte']} : {a['role']}\n  → {a['consigne_texte']}\n"
                         for i, a in enumerate(STRUCTURE_REEL, 1))
    prompt = (
        "Tu es Nyavodroid, la page tech immersive de storytelling technologique.\n\n"
        f"Axe : {label}\nSujet imposé : {sujet}\n\n"
        f"MISSION : MINI-HISTOIRE en exactement {NB_IMAGES_REEL} actes, narration cohérente (début→tension→chute), PAS des faits isolés.\n\n"
        f"Structure :\n{actes_desc}\n"
        f"Consignes : chaque phrase < 10 mots ; numérotées 1 à {NB_IMAGES_REEL}, une par ligne ; ton {TON_EDITORIAL} ; "
        f"PAS de Markdown, PAS d'astérisques. Interdit : faits isolés, généralités.\n\n"
        f"Format :\n1. Phrase une\n2. Phrase deux\n3. Phrase trois"
    )
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, f"(Reel : {sujet})")
    phrases = []
    for ligne in brut.split("\n"):
        ligne = M.clean_text(ligne)
        if ligne and ligne[0].isdigit() and "." in ligne:
            p = M.clean_text(ligne.split(".", 1)[1].strip())
            if p:
                phrases.append(p)
    if len(phrases) < NB_IMAGES_REEL:
        raise ValueError(f"Phrases insuffisantes ({len(phrases)}/{NB_IMAGES_REEL}) : {brut}")
    return sujet, phrases[:NB_IMAGES_REEL]


def _generer_images_reel(pilier: str, phrases: list, sujet: str) -> list:
    label = PILLARS[pilier]["label"]
    chemins = []
    for i, (phrase, acte) in enumerate(zip(phrases, STRUCTURE_REEL), 1):
        chemin = f"reel_img_{i}.png"
        ctx = ""
        if i > 1:
            ctx += f"Scène précédente : « {phrases[i-2]} »\n"
        if i < len(phrases):
            ctx += f"Scène suivante : « {phrases[i]} »\n"
        prompt = (f"Scène {i}/{NB_IMAGES_REEL} d'une mini-histoire visuelle en 3 actes.\n"
                  f"Sujet global : {sujet}\nAxe : {label}\n\n"
                  f"ACTE {i} — {acte['acte']} : {acte['role']}\n"
                  f"Texte de cette scène : « {phrase} »\nAmbiance : {acte['ambiance']}\n"
                  f"Cadrage : {acte['consigne_image']}\n\n")
        if ctx:
            prompt += f"Continuité narrative :\n{ctx}\n"
        prompt += (f"Style : {STYLE_IMAGE_SUFFIX}\n"
                   f"IMPORTANT : cohérence visuelle avec les autres scènes (même univers, palette, ambiance).")
        if i > 1:
            pause = DELAY_ENTRE_IMAGES + random.uniform(0, 10)
            print(f"  ⏳ Pause anti-rate-limit : {pause:.0f}s...")
            time.sleep(pause)
        print(f"  🖼️  Scène {i}/{NB_IMAGES_REEL} [{acte['acte']}]...")
        M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin, size=(1080, 1920))
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

    # Si pas de musique, on génère un silence en AAC natif
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
            f"zoompan=z='min(zoom+0.0008,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={int(DUREE_PAR_IMAGE*25)}:s={STORY_WIDTH}x{STORY_HEIGHT}:fps=25,"
            f"fade=t=in:st=0:d=0.5,fade=t=out:st={DUREE_PAR_IMAGE-0.5}:d=0.5[scene{i}]")
    filtres.append("".join(f"[scene{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[slideshow]")
    txt = "[slideshow]"
    for i, (texte, acte) in enumerate(zip(textes, STRUCTURE_REEL)):
        t_esc = texte.replace("'", "\\'").replace(":", "\\:").replace("%", "%%")
        t0, t1 = i * DUREE_PAR_IMAGE, (i + 1) * DUREE_PAR_IMAGE
        alpha = (f"if(lt(t-{t0},0.6),min((t-{t0})/0.6,1),"
                 f"if(gt(t,{t1}-0.6),max(1-({t1}-t)/0.6,0),1))")
        txt += (f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{t_esc}':fontcolor=0x00E5FF:fontsize=56:x=(w-text_w)/2:y=h*0.78:"
                f"box=1:boxcolor=0x0D0D0D@0.75:boxborderw=28:alpha='{alpha}':"
                f"enable='between(t,{t0+0.3},{t1-0.3})'")
        txt += (f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                f"text='{i+1}/{NB_IMAGES_REEL}':fontcolor=0x00E5FF@0.5:fontsize=28:"
                f"x=(w-text_w)/2:y=60:alpha='{alpha}':enable='between(t,{t0+0.3},{t1-0.3})'")
    filtres.append(txt + "[final]")

    cmd = ["ffmpeg", *inputs, "-filter_complex", ";".join(filtres),
           "-map", "[final]", "-map", f"{n}:a",
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
           "-t", str(duree_totale), "-y", sortie]
    try:
        print("  🎬 Assemblage vidéo ffmpeg (3 actes)...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"  ✅ Vidéo : {sortie} ({os.path.getsize(sortie):,} o)")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg absent. Installez : sudo apt-get install -y ffmpeg fonts-dejavu-core")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg échec (code {e.returncode}) :\n{e.stderr[:800]}") from e


def publier_reel(pilier: str) -> dict:
    sujet, phrases = _generer_phrases_reel(pilier)
    print(f"\n📌 Axe   : {PILLARS[pilier]['label']}\n📌 Sujet : {sujet}")
    print(f"📌 Storytelling Reel ({NB_IMAGES_REEL} actes) :")
    for i, (p, a) in enumerate(zip(phrases, STRUCTURE_REEL), 1):
        print(f"   {i}. [{a['acte']}] {p}")
    images = _generer_images_reel(pilier, phrases, sujet)
    _generer_audio_reel(pilier)
    _assembler_video(images, phrases, REEL_VIDEO_PATH)
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/video_reels"
    try:
        print("  📤 Reel — phase 1/3 (start)...")
        r1 = M._req("POST", ep, data={"upload_phase": "start", "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        init = r1.json()
        video_id, upload_url = init.get("video_id"), init.get("upload_url")
        if not video_id or not upload_url:
            raise ValueError(f"Phase start échouée : {init}")
        print("  📤 Reel — phase 2/3 (transfer)...")
        with open(REEL_VIDEO_PATH, "rb") as f:
            M._req("POST", upload_url,
                   data={"upload_phase": "transfer", "video_id": video_id, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"video_file": (os.path.basename(REEL_VIDEO_PATH), f, "video/mp4")}, timeout=300)
        print("  📤 Reel — phase 3/3 (finish)...")
        r3 = M._req("POST", ep, data={"upload_phase": "finish", "video_id": video_id, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        print(f"  ✅ Reel publié — Video ID : {video_id}")
        return r3.json()
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "Reel vidéo") from e
    except OSError as e:
        raise RuntimeError(f"Fichier vidéo illisible : {e}") from e


def main() -> None:
    print("=" * 60)
    print("🎬 Nyavodroid — Multi-formats [Projet Gemini B]")
    print("=" * 60)
    M.verify_fb_token()
    tc = choisir_type_contenu()
    pilier = choisir_pilier()
    labels = {"texte_seul": "📝 Texte seul", "image_texte": "🖼️  Image + Texte", "reel": "🎬 Reel vidéo"}
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