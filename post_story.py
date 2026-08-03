#!/usr/bin/env python3
"""
Nyavodroid — STORY avec hiérarchie de texte dynamique, rendu Pillow,
watermark (expression + logo), style Infographie Narrative d'Expert.

Améliorations v2 :
- Sources vérifiables (année ≤ 2025, jamais de futur)
- Tronquage automatique des textes trop longs
- Requête Pexels nettoyée (mots concrets)
- Cohérence avec nyavo_media.py v2 (safe zones, logo unique)
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
#  GÉNÉRATION DE TEXTE — PROMPT CRÉDIBLE
# ══════════════════════════════════════════════
def generer_texte_story():
    """Génère une anecdote FACTUELLE avec source réelle (pas de 2026 ni de chiffres inventés)."""
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # Prompt renforcé : crédibilité + concision + surlignage
    prompt = (
        "Tu es Nyavodroid. Rédige UNIQUEMENT en français.\n"
        "Raconte une anecdote FACTUELLE sur le sujet en 2 phrases courtes (max 30 mots au total).\n"
        "Mets les 2-3 MOTS LES PLUS IMPORTANTS entre **astérisques** pour surlignage.\n"
        "SOURCE OBLIGATOIRE : organisme réel connu + année 2024 ou antérieure (jamais 2025/2026).\n"
        "Exemples valides : 'Nature 2023', 'INSEE 2022', 'NASA 2024', 'RFC 1035 1987'.\n"
        "INTERDIT : chiffres inventés, prédictions sur l'avenir, sources floues ('études').\n"
        "Réponds EXACTEMENT en JSON :\n"
        '{\n  "texte": "Texte court avec **mots clés**",\n'
        '  "source": "Organisme Année"\n}\n\n'
        f"Sujet : {sujet}."
    )

    print(f"  📝 Génération texte story...\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]")
    brut = brut.strip()
    if brut.startswith("```json"):
        brut = brut[7:]
    if brut.endswith("```"):
        brut = brut[:-3]

    try:
        data = json.loads(brut)
        texte_complet = data.get("texte", "")
        source = data.get("source", "")
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


# ══════════════════════════════════════════════
#  GÉNÉRATION IMAGE — PEXELS PRIORITAIRE + FALLBACK IA
# ══════════════════════════════════════════════
def generer_image_story(pilier: str, sujet: str, chemin: str) -> None:
    """Décision dynamique : Pexels (nettoyé) pour le réel, IA pour l'abstrait."""
    categorie = PILLARS[pilier].get("categorie", "tech")
    use_pexels = (categorie in ["tech", "science"])

    if use_pexels:
        print(f"  🖼️  [Pexels] Recherche : '{sujet}'")
        success = M.get_image_from_pexels(sujet, chemin, size=(STORY_WIDTH, STORY_HEIGHT))
        
        if not success:
            # La fonction get_image_from_pexels v2 fait déjà le nettoyage
            # On tente un dernier fallback avec un seul mot-clé principal
            mot_principal = sujet.split()[0] if sujet else ""
            if mot_principal and len(mot_principal) > 3:
                print(f"  🖼️  [Pexels] Ultime tentative : '{mot_principal}'")
                success = M.get_image_from_pexels(mot_principal, chemin, size=(STORY_WIDTH, STORY_HEIGHT))
        
        if not success:
            print(f"  ⚠️  [Pexels] Échec total → Fallback IA documentaire")
            prompt_img = (
                f"Professional documentary photography of {sujet}, photorealistic, 8k, sharp focus. "
                f"NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, NO WATERMARKS."
            )
            M.image_avec_fallback(prompt_img, GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT))
        else:
            print(f"  ✅ [Pexels] Photo réelle utilisée")
    else:
        print(f"  🎨 [IA] Génération conceptuelle pour : {sujet}")
        prompt_img = (
            f"Abstract conceptual art representing {sujet}, premium editorial style, "
            f"deep violet and midnight blue tones. NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS."
        )
        M.image_avec_fallback(prompt_img, GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT))


# ══════════════════════════════════════════════
#  INCRUSTATION TEXTE PILLOW + WATERMARK
# ══════════════════════════════════════════════
def incruster_texte_hierarchique(image_in, contexte, fait_choc, consequence, source, image_out):
    """Incrustation hiérarchique Pillow (story 1080x1920), puis watermark expression."""
    # Tronquage de sécurité : jamais de pavé de texte
    fait_choc = M._truncate(fait_choc, 90) if fait_choc else ""
    consequence = M._truncate(consequence, 140) if consequence else ""
    source = M.clean_text(source) if source else ""
    
    M.incruster_texte_pillow(image_in, contexte, fait_choc, consequence, source,
                             image_out, target_size=(STORY_WIDTH, STORY_HEIGHT))
    # Watermark expression uniquement (logo déjà ajouté par _apply_logo dans incruster_texte_pillow)
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
    print("🎬 Nyavodroid — Story [Premium Cultination v2]")
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

    print("  🎨 Incrustation Cultination (logo + texte + watermark)...")
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