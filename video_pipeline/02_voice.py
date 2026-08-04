#!/usr/bin/env python3
"""
Phase 2 — Génération voix off via Edge TTS (gratuit, illimité).
Entrée  : narration.txt
Sortie  : voice.mp3 + phrase_times.json (timestamps exacts sans Whisper)
"""
import asyncio
import json
import os
import re as _re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import BASE_DIR, VOICE_FILE

EDGE_VOICE = "fr-FR-HenriNeural"

_INVISIBLE = _re.compile(
    "[\u200e\u200f\u200b\u200c\u200d\ufeff\u00ad\u2060\u180e\u202a-\u202e\u2066-\u2069]"
)


def get_audio_duration(path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", path]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception as e:
        print(f"    ⚠️ ffprobe échec pour {path} : {e}")
        return 0.0


async def _tts_edge_async(text: str, out_path: str) -> bool:
    try:
        import edge_tts
        text_clean = _INVISIBLE.sub("", text or "")
        text_clean = "".join(c for c in text_clean if c.isprintable() or c in " \n\t").strip()
        if not text_clean:
            return False
        communicate = edge_tts.Communicate(text_clean, EDGE_VOICE)
        await communicate.save(out_path)
        return os.path.isfile(out_path) and os.path.getsize(out_path) > 1024
    except Exception as e:
        print(f"    ❌ Edge TTS échec : {e}")
        return False


def tts_edge(text: str, out_path: str) -> bool:
    return asyncio.run(_tts_edge_async(text, out_path))


def _run_ffmpeg(cmd: list) -> tuple:
    """Exécute ffmpeg et retourne (ok, stderr_complet)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0), r.stderr
    except Exception as e:
        return False, str(e)


def concat_audio(paths: list, output: str) -> bool:
    """
    Jonction de MP3. Méthode 1 : concat protocol (binaire, sans ré-encodage).
    Méthode 2 (fallback) : concat filter normalisé + libmp3lame.
    """
    if not paths:
        return False

    # ── Méthode 1 : concat protocol (la plus fiable pour MP3) ──
    concat_str = "concat:" + "|".join(paths)
    ok, err = _run_ffmpeg(["ffmpeg", "-i", concat_str, "-c", "copy", "-y", output])
    if ok and os.path.isfile(output) and os.path.getsize(output) > 1024:
        print("    ✅ Concat via protocol (copy)")
        return True
    print(f"    ⚠️ concat protocol échec, tentative fallback...\n{err[-800:]}")

    # ── Méthode 2 : concat filter normalisé + encodeur MP3 ──
    inputs, parts = [], []
    for i, p in enumerate(paths):
        inputs += ["-i", p]
        parts.append(f"[{i}:a]aformat=sample_rates=24000:channel_layouts=mono[a{i}]")
    parts.append("".join(f"[a{i}]" for i in range(len(paths))) +
                 f"concat=n={len(paths)}:v=0:a=1[out]")
    cmd = ["ffmpeg", *inputs, "-filter_complex", ";".join(parts),
           "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "4", "-y", output]
    ok, err = _run_ffmpeg(cmd)
    if ok and os.path.isfile(output) and os.path.getsize(output) > 1024:
        print("    ✅ Concat via filter (libmp3lame)")
        return True

    # Affiche le VRAI message d'erreur pour diagnostic
    print(f"    ❌ concat échec définitif :\n{err[-1500:]}")
    return False


def main():
    narration_path = os.path.join(BASE_DIR, "narration.txt")
    if not os.path.isfile(narration_path):
        print(f"❌ {narration_path} introuvable — lance 01_script.py d'abord")
        sys.exit(1)

    with open(narration_path, "r", encoding="utf-8") as f:
        phrases = [p.strip() for p in f.readlines() if p.strip()]

    print(f"\n🎙️  [02_voice] Génération de {len(phrases)} phrases (Edge TTS)...")
    phrases_dir = os.path.join(BASE_DIR, "phrases")
    os.makedirs(phrases_dir, exist_ok=True)

    timings, audio_files, t_cursor = [], [], 0.0

    for i, phrase in enumerate(phrases, 1):
        audio_path = os.path.join(phrases_dir, f"phrase_{i:03d}.mp3")
        print(f"  🎙️  Phrase {i}/{len(phrases)}...")
        if not tts_edge(phrase, audio_path):
            print(f"    ⚠️  Phrase {i} sautée")
            continue
        duration = get_audio_duration(audio_path)
        timings.append({
            "index": i, "text": phrase, "file": audio_path,
            "start": round(t_cursor, 2), "end": round(t_cursor + duration, 2),
            "duration": round(duration, 2),
        })
        audio_files.append(audio_path)
        t_cursor += duration

    if not audio_files:
        print("❌ Aucune phrase générée.")
        sys.exit(1)

    print(f"  🔗 Assemblage → {VOICE_FILE}")
    if not concat_audio(audio_files, VOICE_FILE):
        print("❌ Concat final échoué")
        sys.exit(1)

    times_path = os.path.join(BASE_DIR, "phrase_times.json")
    with open(times_path, "w", encoding="utf-8") as f:
        json.dump({"total_duration": round(t_cursor, 2), "phrases": timings},
                  f, indent=2, ensure_ascii=False)

    print(f"  ✅ Voice : {os.path.getsize(VOICE_FILE):,} octets, durée {t_cursor:.1f}s")
    print(f"  ✅ Timings → {times_path}")


if __name__ == "__main__":
    main()