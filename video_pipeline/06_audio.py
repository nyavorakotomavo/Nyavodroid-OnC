#!/usr/bin/env python3
"""
Phase 6 — SFX + musique de fond.
Entrée  : scenes.json + voice.mp3 + sfx/*.mp3
Sortie  : video_pipeline/mixed_audio.mp3 (voix + SFX + musique)

CORRECTION : tous les flux sont normalisés au même sample rate (44100 Hz,
stéréo) AVANT amix, sinon FFmpeg refuse de mixer.
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

RATE = 44100
LAYOUT = "stereo"
NORM = f"aformat=sample_rates={RATE}:channel_layouts={LAYOUT}"


def _run_ffmpeg(cmd: list) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0), r.stderr
    except Exception as e:
        return False, str(e)


def generate_background_music(duration: float, output_path: str) -> bool:
    cmd = [
        "ffmpeg",
        "-f", "lavfi", "-i", f"sine=frequency=110:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=165:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={duration}",
        "-filter_complex",
        f"[0:a]volume=0.3[a0];[1:a]volume=0.3[a1];[2:a]volume=0.4[a2];"
        f"[a0][a1][a2]amix=inputs=3:duration=longest:normalize=0[out]",
        "-map", "[out]", "-ac", "2", "-ar", str(RATE), "-y", output_path
    ]
    ok, err = _run_ffmpeg(cmd)
    if not ok:
        print(f"    ⚠️ Musique échec : {err[-500:]}")
    return ok and os.path.isfile(output_path)


def mix_audio_with_sfx(voice_path, scenes, music_path, output_path) -> bool:
    if not os.path.isfile(voice_path):
        print(f"❌ {voice_path} introuvable")
        return False

    inputs = ["-i", voice_path]
    parts = [f"[0:a]{NORM}[voice]"]
    mix_list = ["[voice]"]
    idx = 1

    if music_path and os.path.isfile(music_path):
        inputs += ["-i", music_path]
        parts.append(f"[{idx}:a]{NORM},volume={VOL_MUSIC}[music]")
        mix_list.append("[music]")
        idx += 1

    for scene in scenes:
        sfx_name = scene.get("sfx", "none")
        if sfx_name == "none":
            continue
        sfx_file = os.path.join(SFX_DIR, f"{sfx_name}.mp3")
        if not os.path.isfile(sfx_file):
            print(f"    ⚠️ SFX manquant : {sfx_name}")
            continue
        inputs += ["-i", sfx_file]
        ms = int(scene.get("start", 0) * 1000)
        parts.append(f"[{idx}:a]{NORM},adelay={ms}:all=1,volume={VOL_SFX}[s{idx}]")
        mix_list.append(f"[s{idx}]")
        idx += 1

    n = len(mix_list)
    parts.append("".join(mix_list) + f"amix=inputs={n}:duration=first:normalize=0[out]")
    cmd = ["ffmpeg", *inputs, "-filter_complex", ";".join(parts),
           "-map", "[out]", "-ac", "2", "-ar", str(RATE), "-b:a", "192k", "-y", output_path]

    ok, err = _run_ffmpeg(cmd)
    if ok and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        return True
    print(f"    ⚠️ Mix complet échec : {err[-800:]}")

    # Fallback 1 : voix + musique seulement
    if music_path and os.path.isfile(music_path):
        cmd2 = ["ffmpeg", "-i", voice_path, "-i", music_path,
                "-filter_complex",
                f"[0:a]{NORM}[v];[1:a]{NORM},volume={VOL_MUSIC}[m];"
                f"[v][m]amix=inputs=2:duration=first:normalize=0[out]",
                "-map", "[out]", "-ac", "2", "-ar", str(RATE), "-b:a", "192k", "-y", output_path]
        ok, err = _run_ffmpeg(cmd2)
        if ok and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
            print("    ✅ Fallback voix+musique")
            return True

    # Fallback 2 : voix seule
    cmd3 = ["ffmpeg", "-i", voice_path, "-ac", "2", "-ar", str(RATE), "-y", output_path]
    ok, err = _run_ffmpeg(cmd3)
    if ok and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024:
        print("    ✅ Fallback voix seule")
        return True

    print(f"❌ Mixage échec définitif : {err[-1500:]}")
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

    music_path = os.path.join(BASE_DIR, "music.mp3")
    print("  🎵 Génération musique de fond...")
    if generate_background_music(total_duration, music_path):
        print(f"  ✅ {music_path}")
    else:
        music_path = None
        print("  ⚠️ Musique absente (mixage sans musique)")

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