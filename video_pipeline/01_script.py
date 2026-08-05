#!/usr/bin/env python3
"""
Phase 1 — Générateur de narration à partir de VRAIES news (flux RSS).
Le contenu est toujours réel : on part d'un article vrai, le LLM ne fait
que reformuler en narration courte, sans rien inventer.
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

FEEDS = [
    ("BBC Tech", "http://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("ScienceDaily", "https://www.sciencedaily.com/rss/computers_math.xml"),
    ("Le Monde", "https://www.lemonde.fr/rss/une.xml"),
]


def _strip_html(t: str) -> str:
    return re.sub(r"<[^>]+>", "", t or "").strip()


def _parse_feed(xml_text: str, source: str) -> list:
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in ("item", "entry"):
            title = desc = link = ""
            for child in node:
                t = child.tag.split("}")[-1]
                if t == "title":
                    title = (child.text or "").strip()
                elif t in ("description", "summary", "content"):
                    desc = _strip_html(child.text or "")
                elif t == "link":
                    link = (child.text or "").strip() or child.get("href", "")
            if title:
                items.append({"title": title, "desc": desc, "link": link, "source": source})
    return items


def fetch_real_news() -> dict:
    all_items = []
    for name, url in FEEDS:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Nyavodroid/1.0"})
            if r.status_code == 200:
                all_items += _parse_feed(r.text, name)
        except Exception as e:
            print(f"    ⚠️ Feed {name} : {e}")
    if not all_items:
        raise RuntimeError("Aucune news récupérée (flux RSS injoignables)")
    return random.choice(all_items)


def generer_narration(article: dict) -> dict:
    prompt = (
        "Tu es Nyavodroid. Voici un VRAI article d'actualité :\n"
        f"Source : {article['source']}\n"
        f"Titre : {article['title']}\n"
        f"Résumé : {article['desc']}\n\n"
        "Écris la narration d'une vidéo verticale courte en français.\n"
        f"Entre 5 et {MAX_PHRASES} phrases courtes (max 15 mots chacune).\n"
        "INTERDICTION ABSOLUE d'inventer des chiffres, dates ou faits absents de l'article.\n"
        "Si le résumé manque de détail, reste général mais vrai.\n"
        "1ère phrase = accroche choc. Dernière phrase = chute mémorable.\n"
        "Réponds UNIQUEMENT en JSON : {\"phrases\": [\"...\", ...]}\n"
    )
    brut = M.texte_avec_fallback(prompt, os.environ.get("GEMINI_API_KEY_CONTENT", ""), "[video script]")
    brut = brut.strip()
    if brut.startswith("```json"): brut = brut[7:]
    if brut.endswith("```"): brut = brut[:-3]
    try:
        phrases = [M.clean_text(p) for p in json.loads(brut).get("phrases", []) if p.strip()]
    except Exception:
        phrases = [M.clean_text(article["title"])]
    return {"phrases": phrases[:MAX_PHRASES] or [M.clean_text(article["title"])]}


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    print("\n📰 [01_script] Récupération de vraies news (RSS)...")
    article = fetch_real_news()
    print(f"  📌 Article : {article['title']} ({article['source']})")

    meta = generer_narration(article)

    with open(os.path.join(BASE_DIR, "narration.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(meta["phrases"]))

    with open(os.path.join(BASE_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({
            "sujet": article["title"],
            "title": article["title"],
            "source": article["source"],
            "link": article["link"],
            "style": "documentaire dynamique",
            "nb_phrases": len(meta["phrases"]),
        }, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Narration : {len(meta['phrases'])} phrases")


if __name__ == "__main__":
    main()