#!/usr/bin/env python3
"""Nyavodroid — STORY v4 : auto-vérification factuelle, visuel aligné mots-clés."""
import os, random, sys, json
import requests
import nyavo_media as M
from typing import Optional
from content_config import (
    PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, SUJETS_PAR_PILIER,
    STORY_WIDTH, STORY_HEIGHT
)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_STORY"])
STORY_IMAGE_PATH = "story_image.png"
# Variable globale pour passer le sujet tendance entre choisir_pilier() et generer_*()
_SUJET_TENDANCE_NANALY: Optional[str] = None

def choisir_pilier() -> str:
    """Choisit un pilier en priorisant les sujets tendance de NAnaly."""
    from charger_strategie import charger_strategie
    strategie = charger_strategie()

    global _SUJET_TENDANCE_NANALY
    
    # Si NAnaly a identifié des sujets tendance, on essaie de matcher avec un pilier
    if strategie.sujets_a_explorer:
        sujet_tendance = random.choice(strategie.sujets_a_explorer)
        print(f"  🔥 Sujet tendance NAnaly détecté : {sujet_tendance}")
        _SUJET_TENDANCE_NANALY = sujet_tendance

    # Fallback : choix pondéré classique
    return random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]
def generer_texte_story():
    from charger_strategie import charger_strategie
    strategie = charger_strategie()

    pilier = random.choices(PILLAR_KEYS, weights=[PILLAR_WEIGHTS[k] for k in PILLAR_KEYS], k=1)[0]

    # Priorité NAnaly : sujet tendance
    global _SUJET_TENDANCE_NANALY
    if _SUJET_TENDANCE_NANALY:
        sujet = _SUJET_TENDANCE_NANALY
        _SUJET_TENDANCE_NANALY = None
        print(f"  🎯 Sujet story imposé par NAnaly : {sujet}")
    else:
        sujet = random.choice(SUJETS_PAR_PILIER[pilier])

    # Injection des mots-clés tendance dans le prompt si disponibles
    keywords_hint = ""
    if strategie.mots_cles_tendance:
        keywords_hint = f"\nMots-clés tendance à intégrer si pertinent : {', '.join(strategie.mots_cles_tendance[:5])}"

    prompt = (
        "Tu es Nyavodroid, expert fact-checker. Contenu 100% vérifié obligatoire.\n\n"
        "ÉTAPE 1 — Génère une anecdote factuelle sur le sujet.\n"
        "ÉTAPE 2 — Auto-vérification (3 questions) :\n"
        "  Q1: Source réelle et accessible ?\n"
        "  Q2: Chiffres/années cohérents avec la réalité ?\n"
        "  Q3: image_prompt techniquement exact ? (NoSQL≠JSON, HTTP/3≠TCP, CDN≠serveur unique)\n"
        "ÉTAPE 3 — Corrige si nécessaire avant de répondre.\n\n"
        "RÈGLES STRICTES :\n"
        "- Jamais de chiffre inventé. Année ≤ 2024.\n"
        "- FORMAT DES NOMBRES : les puissances s'écrivent SANS espaces (ex: 10^30, pas 10 ^ 30). Les unités sont collées au nombre (ex: 30kg, pas 30 kg). Jamais de ^ isolé.\n"
        "- Source obligatoire : organisme réel + année ≤ 2024.\n"
        "- image_prompt EN ANGLAIS : scène visuelle concrète, techniquement exacte, sans texte.\n"
        "- Si non vérifiable : {\"erreur\": \"fait non vérifiable\"}.\n"
        f"{keywords_hint}\n\n"
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
        print(f"  ⚠️ Vérification échouée ou JSON invalide : {e}")
        fait_choc, consequence, source = "Fait non vérifiable pour ce sujet.", "", ""
        visuel, image_prompt = "conceptuel", ""

    return pilier, sujet, fait_choc, consequence, source, visuel, image_prompt


def generer_image_story(pilier, sujet, chemin, visuel, image_prompt, pexels_query=""):
    img_prompt = image_prompt or f"abstract visual metaphor for {sujet}, no text"
    print("  [Pexels] photo reelle prioritaire : " + sujet)
    for q in [x for x in (pexels_query, sujet) if x]:
        if M.get_image_from_pexels(q, chemin, size=(STORY_WIDTH, STORY_HEIGHT)):
            print("  [Pexels] photo reelle utilisee")
            return
    print("  Pexels echec -> fallback IA (dernier recours)")
    M.image_avec_fallback(img_prompt, GEMINI_API_KEY, chemin, size=(STORY_WIDTH, STORY_HEIGHT))

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
    print("="*50); print("🎬 Nyavodroid — Story v4"); print("="*50)
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