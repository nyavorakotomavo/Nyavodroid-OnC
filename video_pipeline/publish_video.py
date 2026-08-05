#!/usr/bin/env python3
"""
Publication de la vidéo finale sur Facebook.
Légende : titre + source + lien + hashtag.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nyavo_media as M
from content_config import PILLARS
from video_pipeline.config_video import BASE_DIR, SCENES_FILE, FINAL_VIDEO


def main():
    if not os.path.isfile(FINAL_VIDEO):
        print(f"❌ {FINAL_VIDEO} introuvable — lance 07_editor.py d'abord")
        sys.exit(1)

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    meta = doc.get("metadata", {})
    title = meta.get("title", "Vidéo Nyavodroid")
    source = meta.get("source", "")
    link = meta.get("link", "")

    legende = f"{title}\n\n"
    if source and link:
        legende += f"Source : {source}\n{link}\n\n"
    legende += "#Nyavodroid #Tech #Science"

    print(f"\n📤 Publication vidéo Facebook...")
    print(f"📌 Titre : {title}")
    print(f"📌 Source : {source}")

    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/videos"
    try:
        with open(FINAL_VIDEO, "rb") as f:
            r = M._req("POST", ep,
                       data={"description": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(FINAL_VIDEO), f, "video/mp4")},
                       timeout=300)
        res = r.json()
        if "id" not in res:
            raise ValueError(f"Réponse FB inattendue : {res}")
        print(f"  ✅ Vidéo publiée — ID : {res['id']}")
    except Exception as e:
        print(f"❌ Publication échouée : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()