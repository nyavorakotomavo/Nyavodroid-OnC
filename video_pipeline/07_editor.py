#!/usr/bin/env python3
"""
Phase 7 — Montage final.
Entrée  : scenes.json + clips animés + mixed_audio.mp3
Sortie  : final_video.mp4 (1080x1920, H.264, prêt à publier)

Assemble :
- Clips vidéo animés (concaténés selon timestamps)
- Audio mixé (voix + SFX + musique)
- Sous-titres synchronisés (drawtext FFmpeg)
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CODEC, VIDEO_CRF,
    FINAL_VIDEO
)


def create_concat_file(scenes: list, output_path: str) -> bool:
    """Crée le fichier de concaténation pour FFmpeg."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for scene in scenes:
                clip_name = scene.get("clip", "")
                if not clip_name:
                    continue
                clip_path = os.path.join(ASSETS_DIR, clip_name)
                if os.path.isfile(clip_path):
                    escaped = clip_path.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")
        return True
    except Exception as e:
        print(f"❌ Erreur concat file : {e}")
        return False


def build_subtitle_filter(scenes: list) -> str:
    """Construit le filtre FFmpeg pour afficher les sous-titres synchronisés."""
    filters = []
    
    for scene in scenes:
        text = scene.get("subtitle_text", "")
        if not text:
            continue
        
        # Échappement pour FFmpeg
        text = text.replace("'", "'\\''").replace(":", "\\:")
        
        start = scene.get("start", 0)
        end = scene.get("end", start + 3)
        
        # Position : bas de l'écran, centré
        filters.append(
            f"drawtext=text='{text}':"
            f"fontsize=36:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-text_h-80:"
            f"enable='between(t,{start},{end})'"
        )
    
    return ",".join(filters) if filters else "null"


def assemble_video(concat_file: str, audio_file: str, scenes: list, output_path: str) -> bool:
    """Assemble clips + audio + sous-titres en vidéo finale."""
    
    subtitle_filter = build_subtitle_filter(scenes)
    
    cmd = [
        "ffmpeg",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-i", audio_file,
        "-vf", subtitle_filter,
        "-c:v", VIDEO_CODEC, "-preset", "fast", "-crf", str(VIDEO_CRF),
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-y", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 10240
    except subprocess.CalledProcessError as e:
        print(f"❌ Assemblage échec : {e.stderr[:500]}")
        return False


def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable")
        sys.exit(1)
    
    mixed_audio = os.path.join(BASE_DIR, "mixed_audio.mp3")
    if not os.path.isfile(mixed_audio):
        print(f"❌ {mixed_audio} introuvable — lance 06_audio.py d'abord")
        sys.exit(1)
    
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    scenes = doc.get("scenes", [])
    if not scenes:
        print("❌ scenes.json vide")
        sys.exit(1)
    
    print(f"\n🎬 [07_editor] Montage final ({len(scenes)} scènes)\n")
    
    # Fichier de concaténation
    concat_file = os.path.join(BASE_DIR, "concat.txt")
    print("  📋 Création fichier concat...")
    if not create_concat_file(scenes, concat_file):
        print("❌ Échec concat file")
        sys.exit(1)
    
    # Assemblage final
    print("  🎞️  Assemblage vidéo...")
    if assemble_video(concat_file, mixed_audio, scenes, FINAL_VIDEO):
        size_mb = os.path.getsize(FINAL_VIDEO) / (1024 * 1024)
        print(f"  ✅ {FINAL_VIDEO} ({size_mb:.1f} MB)")
        
        # Nettoyage
        if os.path.isfile(concat_file):
            os.remove(concat_file)
        
        print(f"\n🎉 Vidéo finale prête à publier !")
    else:
        print("❌ Montage échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()