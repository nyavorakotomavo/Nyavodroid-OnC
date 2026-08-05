#!/usr/bin/env python3
"""
Phase 1 — Vraies news Tech/Science + pipeline anti-fake-news.
RECHERCHE (RSS fiables) → NICHE → CORROBORATION → CONFIANCE → RÉDACTION.
Si aucun sujet vérifiable → ABANDON (pas de publication).
"""
import json
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import nyavo_media as M
from video_pipeline.config_video import BASE_DIR, MAX_PHRASES

# ── Sources classées par fiabilité ──
FEEDS_T1 = [  # officiels / scientifiques
    ("Nature", "https://www.nature.com/nature.rss"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/feed.rss"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/computers_math.xml"),
    ("ScienceDaily Espace", "https://www.sciencedaily.com/rss/space_time.xml"),
]
FEEDS_T2 = [  # médias tech reconnus
    ("BBC Tech", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Le Monde Pixels", "https://www.lemonde.fr/pixels/rss/une.xml"),
]

NICHE_KEYWORDS = [
    "ia", "intelligence artificielle", "robot", "quantique", "espace", "mars", "lune",
    "satellite", "fusée", "télescope", "james webb", "puce", "semi-conductor", "ordinateur",
    "logiciel", "code", "programmation", "cyber", "données", "cloud", "smartphone", "gadget",
    "batterie", "solaire", "fusion", "adn", "biotech", "découverte", "chercheur", "étude",
    "scientifique", "startup", "internet", "réseau", "processeur", "gpu", "llm", "neuronal",
    "machine learning", "drone", "écran", "énergie", "virus", "vaccin", "climat", "océan",
]


def _strip_html(t): return re.sub(r"<[^>]+>", "", t or "").strip()

def _tokens(t):
    stop = {"les","des","une","un","le","la","de","du","en","et","au","aux","sur","pour",
            "dans","avec","son","ses","cette","qui","que","the","of","and","in","to","for",
            "on","at","is","are","new","a","an","its","from","by","how","why"}
    return set(w for w in re.findall(r"[\wà-ÿÀ-Ÿ]+", (t or "").lower())
               if len(w) > 4 and w not in stop)

def _parse_feed(xml_text, source, tier):
    items = []
    try: root = ET.fromstring(xml_text)
    except ET.ParseError: return items
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in ("item", "entry"):
            title = desc = link = ""
            for c in node:
                t = c.tag.split("}")[-1]
                if t == "title": title = (c.text or "").strip()
                elif t in ("description", "summary", "content"): desc = _strip_html(c.text or "")
                elif t == "link": link = (c.text or "").strip() or c.get("href", "")
            if title:
                items.append({"title": title, "desc": desc, "link": link,
                              "source": source, "tier": tier})
    return items

def fetch_all():
    all_items = []
    for tier, feeds in ((1, FEEDS_T1), (2, FEEDS_T2)):
        for name, url in feeds:
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "Nyavodroid/1.0"})
                if r.status_code == 200:
                    all_items += _parse_feed(r.text, name, tier)
            except Exception as e:
                print(f"    ⚠️ Feed {name} : {e}")
    return all_items

def niche_prefilter(title):
    low = title.lower()
    return any(k in low for k in NICHE_KEYWORDS)

def corroborate(item, all_items):
    toks = _tokens(item["title"])
    sources = set()
    for other in all_items:
        if other["source"] != item["source"] and len(toks & _tokens(other["title"])) >= 2:
            sources.add(other["source"])
    return sorted(sources)

def generer_narration(article, prudent):
    careful = ("CONFIANCE MOYENNE : formule avec prudence ('selon', 'd'après', 'la source affirme')."
               if prudent else "CONFIANCE FORTE : tu peux affirmer les faits de l'article.")
    prompt = (
        "Tu es Nyavodroid, journaliste Tech/Science. Voici un VRAI article :\n"
        f"Source (fiabilité tier {article['tier']}) : {article['source']}\n"
        f"Titre : {article['title']}\nRésumé : {article['desc']}\n\n"
        "Réponds en JSON avec :\n"
        '1. "niche": true SEULEMENT si le sujet est strictement Tech/Science/IA/Innovation/Espace.\n'
        f'2. "phrases": narration française de 5 à {MAX_PHRASES} phrases (max 15 mots chacune), structure :\n'
        "   - phrase 1 = HOOK (info forte) ; suivantes = CONTEXTE + INFORMATION ;\n"
        "   - 1 phrase = EXPLICATION (pourquoi c'est important) ; dernière = CONCLUSION.\n"
        '3. "claims": les 1-3 affirmations factuelles clés de l\'article.\n'
        "RÈGLE ABSOLUE : n'ajoute AUCUN fait, chiffre, date, nom absent du texte ci-dessus.\n"
        f"{careful}\nRéponds UNIQUEMENT en JSON."
    )
    brut = M.texte_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""), "[script]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]
    try: return json.loads(brut)
    except Exception: return {"niche": False, "phrases": [], "claims": []}

def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    print("\n📰 [01_script] Recherche de vraies news Tech/Science...")
    all_items = fetch_all()
    candidates = [i for i in all_items if niche_prefilter(i["title"])]
    random.shuffle(candidates)

    choisi = None
    for art in candidates[:4]:
        corrob = corroborate(art, all_items)
        conf = "forte" if (art["tier"] == 1 or corrob) else "moyenne"
        print(f"  🔎 {art['source']} | confiance {conf} | corroboré par : {corrob or '—'}")
        data = generer_narration(art, prudent=(conf == "moyenne"))
        if data.get("niche") and data.get("phrases"):
            choisi = (art, corrob, conf, data)
            break

    if not choisi:
        print("❌ QC contenu : aucun sujet Tech/Science vérifiable → PAS DE PUBLICATION.")
        sys.exit(3)

    art, corrob, conf, data = choisi
    phrases = [M.clean_text(p) for p in data["phrases"] if p.strip()][:MAX_PHRASES]

    with open(os.path.join(BASE_DIR, "narration.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(phrases))
    with open(os.path.join(BASE_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({
            "sujet": art["title"], "title": art["title"], "source": art["source"],
            "link": art["link"], "tier": art["tier"], "corrobore_par": corrob,
            "confiance": conf, "niche_ok": True, "claims": data.get("claims", []),
            "nb_phrases": len(phrases),
        }, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Sujet : {art['title']}")
    print(f"  ✅ Source : {art['source']} | confiance : {conf} | corroboration : {corrob or '—'}")

if __name__ == "__main__":
    main()