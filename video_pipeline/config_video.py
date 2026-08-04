#!/usr/bin/env python3
"""
Video Pipeline — Configuration centralisée.
Tous les scripts du pipeline lisent leurs constantes ici.
"""
import os

# ──────────────────────────────────────────────
#  Dimensions & format de sortie
# ──────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_CRF = 23
VIDEO_FORMAT = "mp4"

# ──────────────────────────────────────────────
#  Volumes (0.0 → 1.0)
# ──────────────────────────────────────────────
VOL_VOICE = 1.0
VOL_MUSIC = 0.15   # musique de fond basse pour ne pas couvrir la voix
VOL_SFX   = 0.7    # effets sonores selon événement

# ──────────────────────────────────────────────
#  Durées cibles
# ──────────────────────────────────────────────
DURATION_TARGET_SEC = 45       # durée visée de la vidéo
MAX_PHRASES = 10               # max de phrases dans la narration
MAX_PHRASE_CHARS = 180         # longueur max d'une phrase

# ──────────────────────────────────────────────
#  Voix fish.audio
# ──────────────────────────────────────────────
FISH_TTS_URL = "https://api.fish.audio/v1/tts"
FISH_LATENCY = "normal"        # "normal" ou "balanced" ou "extreme"
FISH_VOICE_ID = None           # None = voix par défaut
FISH_API_KEY = os.environ.get("FISH_API_KEY", "")

# ──────────────────────────────────────────────
#  Chemins
# ──────────────────────────────────────────────
BASE_DIR = "video_pipeline"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SFX_DIR = os.path.join(BASE_DIR, "sfx")
SCENES_FILE = os.path.join(BASE_DIR, "scenes.json")
VOICE_FILE = os.path.join(BASE_DIR, "voice.mp3")
FINAL_VIDEO = "final_video.mp4"

# ──────────────────────────────────────────────
#  Bibliothèque SFX (clé → fichier)
# ──────────────────────────────────────────────
SFX_LIBRARY = {
    "whoosh":    "whoosh.mp3",
    "impact":    "impact.mp3",
    "click":     "click.mp3",
    "glitch":    "glitch.mp3",
    "explosion": "explosion.mp3",
    "transition":"transition.mp3",
    "pop":       "pop.mp3",
}

# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
def ensure_dirs():
    """Crée les dossiers de travail s'ils n'existent pas."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(SFX_DIR, exist_ok=True)