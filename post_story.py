#!/usr/bin/env python3
"""
Nyavodroid — STORY avec hiérarchie de texte dynamique, rendu Pillow,
watermark double (expression + profil), style Infographie Narrative d'Expert.
"""

import os
import random
import sys
import json

import requests

import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS,
    STYLE_IMAGE_SUFFIX, SUJETS_PAR_PILIER, TON_EDITORIAL,
    STORY_WIDTH, STORY_HEIGHT
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])

STORY_IMAGE_PATH = "story_image.png"


# ══════════════════════════════════════════════
#  GÉNÉRATION DE TEXTE + PROMPT IMAGE RÉALISTE
# ══════════════════════════════════════════════
def generer_texte_story():
    """Génère la structure et le prompt image style Cultination."""
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # Prompt modifié pour le style Cultination + surlignage
    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français.\n"
        "Raconte une anecdote fascinante sur le sujet en 2 phrases maximum.\n"
        "Mets les chiffres et les mots-clés les plus importants entre double astérisques **comme ceci** pour qu'ils soient surlignés.\n"
        "Réponds EXACTEMENT en JSON :\n"
        '{\n  "texte": "Ton texte avec les **mots clés**",\n'
        '  "source": "Source courte (ex: National Geographic)"\n}\n\n'
        f"Sujet : {sujet}. {TON_EDITORIAL}"
    )
    
    print(f"  📝 Génération texte Cultination...\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]
    
    try:
        data = json.loads(brut)
        texte_complet = data.get("texte", "")
        source = data.get("source", "")
        
        # On parse le texte pour remplir les champs attendus par la fonction d'incrustation
        # On met tout dans 'fait_choc' car notre nouvelle fonction fusionne tout, 
        # mais on garde la structure pour la compatibilité
        contexte = ""
        fait_choc = texte_complet 
        consequence = ""
        
    except Exception:
        print("  ⚠️ JSON invalide, fallback.")
        contexte = brut
        fait_choc = ""
        consequence = ""
        source = ""

    return pilier, sujet, contexte, fait_choc, consequence, source


def generer_image_story(pilier: str, sujet: str, chemin: str) -> None:
    """Génère une image RÉALISTE et explicative (style photojournalisme)."""
    # Prompt changé : on veut une vraie photo du sujet, pas de l'abstrait
    prompt_img = (
        f"Photojournalism style, realistic high-quality photo of {sujet}, "
        f"cinematic lighting, 8k resolution, highly detailed, documentary photography. "
        f"No text, no letters, no watermark."
    )
    print(f"  🖼️  Génération image réaliste pour : {sujet}")
    M.image_avec_fallback(prompt_img, GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT))


# ══════════════════════════════════════════════
#  IMAGE DE FOND
# ══════════════════════════════════════════════
def generer_image_story(pilier: str, sujet: str, chemin: str) -> None:
    """Génère l'image 9:16 avec le style premium (via IA)."""
    prompt = M.clean_text(
        f"Illustration verticale 9:16 pour le sujet : {sujet}\n"
        f"Axe : {PILLARS[pilier]['label']}\nStyle : {STYLE_IMAGE_SUFFIX}"
    )
    M.image_avec_fallback(prompt, GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT))


# ══════════════════════════════════════════════
#  INCRUSTATION TEXTE PILLOW + WATERMARK
# ══════════════════════════════════════════════
def incruster_texte_hierarchique(image_in, contexte, fait_choc, consequence, source, image_out):
    """Incrustation hiérarchique Pillow (story 1080x1920), puis watermark profil+expression."""
    M.incruster_texte_pillow(image_in, contexte, fait_choc, consequence, source,
                             image_out, target_size=(STORY_WIDTH, STORY_HEIGHT))
    # Watermark profil + expression uniquement (la source est déjà rendue par Pillow)
    M.overlay_watermark(image_out, image_out, source_text="")


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