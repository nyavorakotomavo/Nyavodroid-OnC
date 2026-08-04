#!/usr/bin/env python3
"""
Phase 2 — Génération voix off fish.audio.
Entrée  : narration.txt
Sortie  : voice.mp3 + phrase_times.json (timestamps exacts sans Whisper)

Stratégie : on génère CHAQUE phrase séparément → on connaît sa durée exacte
           (ffprobe) → les timestamps sont 100 % fiables et synchronisés.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from video_pipeline.config_video import (
    BASE_DIR, FISH_TTS_URL, FISH_LATENCY, FISH_VOICE_ID, FISH_API_KEY, VOICE_FILE
)


def get_audio_duration(path: str) -> float:
    """Retourne la durée en secondes d'un fichier audio (ffprobe)."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", path]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception as e:
        print(f"    ⚠️ ffprobe échec pour {path} : {e}")
        return 0.0


def tts_fish_audio(text: str, out_path: str) -> bool:
    """Appelle fish.audio /v1/tts et sauvegarde l'audio."""
    if not FISH_API_KEY:
        print("    ❌ FISH_API_KEY absente")
        return False

    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {"text": text, "latency": FISH_LATENCY}
    if FISH_VOICE_ID:
        body["reference_id"] = FISH_VOICE_ID

    try:
        r = requests.post(FISH_TTS_URL, headers=headers, json=body,
                          stream=True, timeout=60)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return os.path.getsize(out_path) > 1024
    except Exception as e:
        print(f"    ❌ fish.audio échec : {e}")
        return False


def concat_audio(paths: list, output: str) -> bool:
    """Assemble plusieurs .mp3 en un seul (ffmpeg concat demuxer)."""
    if not paths:
        return False
    list_file = output + ".txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            # Échapper les single quotes pour ffmpeg
            escaped = p.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    try:
        subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
             "-c", "copy", "-y", output],
            check=True, capture_output=True, text=True
        )
        os.remove(list_file)
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ❌ concat ffmpeg échec : {e.stderr[:400]}")
        return False


def main():
    narration_path = os.path.join(BASE_DIR, "narration.txt")
    if not os.path.isfile(narration_path):
        print(f"❌ {narration_path} introuvable — lance 01_script.py d'abord")
        sys.exit(1)

    with open(narration_path, "r", encoding="utf-8") as f:
        phrases = [p.strip() for p in f.readlines() if p.strip()]

    print(f"\n🎙️  [02_voice] Génération de {len(phrases)} phrases...")
    phrases_dir = os.path.join(BASE_DIR, "phrases")
    os.makedirs(phrases_dir, exist_ok=True)

    timings = []   # liste de {index, text, file, start, end}
    audio_files = []
    t_cursor = 0.0

    for i, phrase in enumerate(phrases, 1):
        audio_path = os.path.join(phrases_dir, f"phrase_{i:03d}.mp3")
        print(f"  🎙️  Phrase {i}/{len(phrases)}...")
        ok = tts_fish_audio(phrase, audio_path)
        if not ok:
            print(f"    ⚠️  Phrase {i} sautée (TTS échoué)")
            continue

        duration = get_audio_duration(audio_path)
        timings.append({
            "index": i,
            "text": phrase,
            "file": audio_path,
            "start": round(t_cursor, 2),
            "end": round(t_cursor + duration, 2),
            "duration": round(duration, 2),
        })
        audio_files.append(audio_path)
        t_cursor += duration

    if not audio_files:
        print("❌ Aucune phrase générée.")
        sys.exit(1)

    # Assemblage final
    print(f"  🔗 Assemblage → {VOICE_FILE}")
    if not concat_audio(audio_files, VOICE_FILE):
        print("❌ Concat final échoué")
        sys.exit(1)

    # Sauvegarde des timings
    times_path = os.path.join(BASE_DIR, "phrase_times.json")
    with open(times_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_duration": round(t_cursor, 2),
            "phrases": timings,
        }, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Voice : {os.path.getsize(VOICE_FILE):,} octets, durée {t_cursor:.1f}s")
    print(f"  ✅ Timings → {times_path}")


if __name__ == "__main__":
    main()