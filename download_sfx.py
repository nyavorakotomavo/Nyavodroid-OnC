#!/usr/bin/env python3
"""
Télécharge automatiquement les SFX recommandés.
Nécessite : pip install requests
"""
import os
import requests

SFX_DIR = "video_pipeline/sfx"

SFX_URLS = {
    "whoosh.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-fast-sweep-transition-2942.mp3",
    "impact.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-large-hit-down-2128.mp3",
    "click.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-modern-technology-select-3227.mp3",
    "glitch.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-glitch-interface-2346.mp3",
    "explosion.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-large-explosion-2311.mp3",
    "transition.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-positive-notification-953.mp3",
    "pop.mp3": "https://assets.mixkit.co/sfx/preview/mixkit-interface-option-select-2164.mp3",
}

os.makedirs(SFX_DIR, exist_ok=True)

for filename, url in SFX_URLS.items():
    path = os.path.join(SFX_DIR, filename)
    print(f"️  {filename}...")
    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)
    size = os.path.getsize(path) / 1024
    print(f"  ✅ {filename} ({size:.1f} KB)")

print("\n✅ Tous les SFX sont dans video_pipeline/sfx/")