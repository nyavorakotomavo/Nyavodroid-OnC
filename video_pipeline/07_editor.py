#!/usr/bin/env python3
"""
Phase 7 — Montage final (blindé).
Étapes séparées avec fallbacks :
  A. Concat des clips vidéo          → tmp_video.mp4
  B. Mux vidéo + audio               → tmp_av.mp4
  C. Sous-titres (optionnel, police explicite) → final_video.mp4
Si C échoue, on garde tmp_av.mp4 comme final (vidéo toujours livrée).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR, FINAL_VIDEO,
    VIDEO_CODEC, VIDEO_CRF
)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _run(cmd: list) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0), r.stderr
    except Exception as e:
        return False, str(e)


def concat_clips(clips: list, out: str) -> bool:
    list_file = out + ".txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    ok, err = _run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c", "copy", "-y", out])
    if os.path.isfile(list_file):
        os.remove(list_file)
    if not ok:
        print(f"    ❌ concat clips : {err[-800:]}")
    return ok and os.path.isfile(out)


def mux_audio(video: str, audio: str, out: str) -> bool:
    ok, err = _run(["ffmpeg", "-i", video, "-i", audio,
                    "-c", "copy", "-shortest", "-y", out])
    if not ok:
        print(f"    ❌ mux audio : {err[-800:]}")
    return ok and os.path.isfile(out)


def build_subtitle_filter(scenes: list) -> str:
    filters = []
    for i, scene in enumerate(scenes):
        text = scene.get("subtitle_text", "")
        if not text:
            continue
        txt_file = os.path.join(BASE_DIR, f"sub_scene_{i}.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(text)
        start = scene.get("start", 0)
        end = scene.get("end", start + 3)
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:textfile='{txt_file}':"
            f"fontsize=36:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=h-text_h-80:enable='between(t,{start},{end})'"
        )
    return ",".join(filters) if filters else ""


def add_subtitles(video: str, scenes: list, out: str) -> bool:
    vf = build_subtitle_filter(scenes)
    if not vf:
        return False
    ok, err = _run(["ffmpeg", "-i", video, "-vf", vf,
                    "-c:v", VIDEO_CODEC, "-preset", "fast", "-crf", str(VIDEO_CRF),
                    "-c:a", "copy", "-y", out])
    if not ok:
        print(f"    ⚠️ sous-titres échec : {err[-800:]}")
    return ok and os.path.isfile(out)


def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable")
        sys.exit(1)

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scenes = doc.get("scenes", [])

    # Ne garder que les clips qui existent réellement
    clips = []
    for s in scenes:
        p = os.path.join(ASSETS_DIR, s.get("clip", ""))
        if s.get("clip") and os.path.isfile(p):
            clips.append(p)
    if not clips:
        print("❌ Aucun clip vidéo trouvé — relance 05_animate.py")
        sys.exit(1)

    print(f"\n🎬 [07_editor] Montage final ({len(clips)} clips)\n")

    # Étape A : concat vidéo
    tmp_video = os.path.join(BASE_DIR, "tmp_video.mp4")
    print("  🎞️  Étape A : concat clips...")
    if not concat_clips(clips, tmp_video):
        print("❌ Concat vidéo échoué")
        sys.exit(1)

    # Étape B : mux audio
    mixed = os.path.join(BASE_DIR, "mixed_audio.mp3")
    tmp_av = os.path.join(BASE_DIR, "tmp_av.mp4")
    current = tmp_video
    if os.path.isfile(mixed):
        print("  🔊 Étape B : ajout audio...")
        if mux_audio(tmp_video, mixed, tmp_av):
            current = tmp_av
        else:
            print("    ⚠️ Audio non ajouté (vidéo muette)")
    else:
        print("    ⚠️ mixed_audio.mp3 absent (vidéo muette)")

    # Étape C : sous-titres (optionnel)
    print("  📝 Étape C : sous-titres...")
    if add_subtitles(current, scenes, FINAL_VIDEO):
        print(f"  ✅ {FINAL_VIDEO} (avec sous-titres)")
    else:
        # Fallback : livrer sans sous-titres
        subprocess.run(["cp", current, FINAL_VIDEO], check=True)
        print(f"  ✅ {FINAL_VIDEO} (sans sous-titres, fallback)")

    # Nettoyage
    for t in (tmp_video, tmp_av):
        if os.path.isfile(t):
            os.remove(t)

    size_mb = os.path.getsize(FINAL_VIDEO) / (1024 * 1024)
    print(f"\n🎉 Vidéo finale : {FINAL_VIDEO} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()