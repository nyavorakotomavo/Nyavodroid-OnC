#!/usr/bin/env python3
"""Nyavodroid — STORY v3 : texte calibré, visuel aligné mots-clés, réel vs IA."""
import os, random, sys, json
import requests
import nyavo_media as M
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, SUJETS_PAR_PILIER,
    STORY_WIDTH, STORY_HEIGHT
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])
STORY_IMAGE_PATH = "story_image.png"

def generer_texte_story():
    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
    sujet = random.choice(SUJETS_PAR_PILIER[pilier])
    
    # Prompt avec auto-vérification intégrée (technique 2-passes [[8]])
    prompt = (
        "Tu es Nyavodroid, un expert fact-checker. Tu dois générer du contenu 100% vérifié.\n\n"
        "ÉTAPE 1 — Génère une anecdote factuelle sur le sujet.\n"
        "ÉTAPE 2 — Vérifie-la en te posant ces 3 questions :\n"
        "  Q1: La source citée existe-t-elle réellement et est-elle accessible ?\n"
        "  Q2: Les chiffres/années sont-ils cohérents avec la réalité documentée ?\n"
        "  Q3: L'image_prompt décrit-il visuellement le sujet SANS erreur technique ?\n"
        "       (ex: NoSQL ≠ JSON, HTTP/3 ≠ TCP, CDN ≠ serveur unique)\n"
        "ÉTAPE 3 — Si une réponse est 'non' ou 'incertain', corrige avant de répondre.\n\n"
        "RÈGLES STRICTES :\n"
        "- Jamais de chiffre inventé. Jamais d'année > 2024.\n"
        "- Source obligatoire : organisme réel + année ≤ 2024.\n"
        "- image_prompt EN ANGLAIS : scène visuelle concrète, techniquement exacte, sans texte.\n"
        "- Si tu ne peux pas vérifier un fait, réponds {\"erreur\": \"fait non vérifiable\"}.\n\n"
        "Réponds EXACTEMENT en JSON :\n"
        '{"texte": "anecdote FACTUELLE 2 phrases (25-35 mots) avec 2-3 mots clés entre **", '
        '"visuel": "concret ou conceptuel", '
        '"image_prompt": "EN ANGLAIS, scène techniquement exacte liée aux mots-clés, sans texte", '
        '"source": "organisme réel + année ≤ 2024"}\n\n'
        f"Sujet : {sujet}."
    )
    
    print(f"  📝 Génération story (avec auto-vérification)...\n     Sujet : {sujet}")
    brut = M.texte_avec_fallback(prompt, GEMINI_API_KEY, "[story]").strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]
    
    try:
        d = json.loads(brut)
        if "erreur" in d:
            raise ValueError(d["erreur"])
        fait_choc, consequence = d.get("texte", ""), ""
        source, visuel, image_prompt = d.get("source",""), d.get("visuel","conceptuel"), d.get("image_prompt","")
    except Exception as e:
        print(f"  ⚠️  Vérification échouée ou JSON invalide : {e}")
        fait_choc, consequence, source = "Fait non vérifiable pour ce sujet.", "", ""
        visuel, image_prompt = "conceptuel", ""
    
    return pilier, sujet, fait_choc, consequence, source, visuel, image_prompt

def incruster_texte_hierarchique(image_in, contexte, fait_choc, consequence, source, image_out):
    M.incruster_texte_pillow(image_in, contexte, fait_choc, consequence, source,
                             image_out, target_size=(STORY_WIDTH, STORY_HEIGHT))
    M.overlay_watermark(image_out, image_out, source_text="")

def uploader_photo_non_publiee(path):
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    try:
        with open(path, "rb") as f:
            r = M._req("POST", ep, data={"published":"false","access_token":M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(path), f, "image/png")}, timeout=M.TIMEOUT)
        pid = r.json().get("id")
        if not pid: raise ValueError(f"Réponse FB inattendue : {r.json()}")
        return pid
    except requests.exceptions.HTTPError as e: raise M.fb_error(e, "upload photo") from e

def publier_story(photo_id):
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photo_stories"
    try:
        r = M._req("POST", ep, data={"photo_id": photo_id, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res: raise ValueError(f"Réponse FB inattendue : {res}")
        return res
    except requests.exceptions.HTTPError as e: raise M.fb_error(e, "publication story") from e

def main():
    print("="*50); print("🎬 Nyavodroid — Story v3"); print("="*50)
    M.verify_fb_token()
    pilier, sujet, fait_choc, consequence, source, visuel, image_prompt = generer_texte_story()
    print(f"\n📌 Sujet : {sujet}\n   Texte : {fait_choc}\n   Source : {source}\n   Visuel : {visuel}")
    generer_image_story(pilier, sujet, "story_raw.png", visuel, image_prompt)
    incruster_texte_hierarchique("story_raw.png", "", fait_choc, consequence, source, STORY_IMAGE_PATH)
    res = publier_story(uploader_photo_non_publiee(STORY_IMAGE_PATH))
    print(f"\n✅ TERMINÉ — Story ID : {res.get('id','N/A')}")

if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print(f"\n❌ ERREUR : {e}", file=sys.stderr); sys.exit(1)
    except KeyError as e: print(f"\n❌ Secret manquant : {e}", file=sys.stderr); sys.exit(1)
    except Exception as e: print(f"\n❌ Inattendu : {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)