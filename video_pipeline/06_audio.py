#!/usr/bin/env python3
"""
Phase 6 — SFX + musique de fond.
Entrée  : scenes.json + voice.mp3 + sfx/*.mp3
Sortie  : video_pipeline/mixed_audio.mp3 (voix + SFX + musique)

Logique :
- Voix : volume 100%
- Musique de fond : volume 15% (ne couvre pas la voix)
- SFX : placés aux timestamps exacts des scènes (volume 70%)
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, SFX_DIR, VOICE_FILE,
    VOL_VOICE, VOL_MUSIC, VOL_SFX
)


def generate_background_music(duration: float, output_path: str) -> bool:
    """Génère une musique de fond simple (tonalité ambiante) avec FFmpeg."""
    # Musique générée : plusieurs sinusoïdes pour un effet ambient
    cmd = [
        "ffmpeg",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=165:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
        "-filter_complex",
        f"[0:a]volume={VOL_MUSIC * 0.3}[a0];"
        f"[1:a]volume={VOL_MUSIC * 0.3}[a1];"
        f"[2:a]volume={VOL_MUSIC * 0.4}[a2];"
        f"[a0][a1][a2]amix=inputs=3:duration=longest[out]",
        "-map", "[out]",
        "-ac", "2", "-ar", "44100",
        "-y", output_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return os.path.isfile(output_path)
    except subprocess.CalledProcessError as e:
        print(f"    ⚠️  Musique de fond échec : {e.stderr[:200]}")
        return False


def mix_audio_with_sfx(voice_path: str, scenes: list, music_path: str, output_path: str) -> bool:
    """Mixe voix + SFX + musique en un seul fichier audio."""
    
    if not os.path.isfile(voice_path):
        print(f"❌ {voice_path} introuvable")
        return False
    
    # Préparation des inputs et filtres
    inputs = ["-i", voice_path]
    filter_parts = []
    stream_idx = 0
    voice_stream = f"[{stream_idx}:a]"
    stream_idx += 1
    
    # Ajout musique de fond
    if os.path.isfile(music_path):
        inputs += ["-i", music_path]
        music_stream = f"[{stream_idx}:a]"
        filter_parts.append(f"{music_stream}volume={VOL_MUSIC}[music]")
        stream_idx += 1
    else:
        music_stream = None
    
    # Ajout des SFX
    sfx_streams = []
    for scene in scenes:
        sfx_name = scene.get("sfx", "none")
        if sfx_name == "none":
            continue
        
        sfx_file = os.path.join(SFX_DIR, f"{sfx_name}.mp3")
        if not os.path.isfile(sfx_file):
            print(f"    ⚠️  SFX manquant : {sfx_name}")
            continue
        
        inputs += ["-i", sfx_file]
        sfx_stream = f"[{stream_idx}:a]"
        start_time = scene.get("start", 0)
        
        # Retard + volume
        filter_parts.append(
            f"{sfx_stream}adelay={int(start_time * 1000)}|{int(start_time * 1000)},"
            f"volume={VOL_SFX}[sfx{stream_idx}]"
        )
        sfx_streams.append(f"[sfx{stream_idx}]")
        stream_idx += 1
    
    # Mixage final
    if music_stream:
        mix_inputs = [voice_stream, "[music]"] + sfx_streams
    else:
        mix_inputs = [voice_stream] + sfx_streams
    
    if len(mix_inputs) > 1:
        filter_parts.append(
            f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[out]"
        )
        final_stream = "[out]"
    else:
        final_stream = voice_stream
    
    filter_complex = ";".join(filter_parts)
    
    cmd = [
        "ffmpeg", *inputs,
        "-filter_complex", filter_complex,
        "-map", final_stream,
        "-ac", "2", "-ar", "44100", "-b:a", "192k",
        "-y", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 1024
    except subprocess.CalledProcessError as e:
        print(f"❌ Mixage échec : {e.stderr[:400]}")
        return False


def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable")
        sys.exit(1)
    
    if not os.path.isfile(VOICE_FILE):
        print(f"❌ {VOICE_FILE} introuvable — lance 02_voice.py d'abord")
        sys.exit(1)
    
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    scenes = doc.get("scenes", [])
    total_duration = doc.get("video", {}).get("total_duration", 45.0)
    
    print(f"\n🔊 [06_audio] Mixage audio ({len(scenes)} scènes, {total_duration:.1f}s)\n")
    
    # Génération musique de fond
    music_path = os.path.join(BASE_DIR, "music.mp3")
    print("  🎵 Génération musique de fond...")
    if generate_background_music(total_duration, music_path):
        print(f"  ✅ {music_path}")
    else:
        print("  ⚠️  Musique de fond absente (mixage sans musique)")
    
    # Mixage voix + SFX + musique
    mixed_path = os.path.join(BASE_DIR, "mixed_audio.mp3")
    print("  🔀 Mixage voix + SFX + musique...")
    if mix_audio_with_sfx(VOICE_FILE, scenes, music_path, mixed_path):
        print(f"  ✅ {mixed_path}")
        print(f"\n✅ Audio mixé prêt")
    else:
        print("❌ Mixage échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()