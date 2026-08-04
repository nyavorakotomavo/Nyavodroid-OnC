#!/usr/bin/env python3
"""
Phase 7 — Montage final (blindé).
CORRECTION : chemins ABSOLUS dans la liste concat (sinon FFmpeg double le chemin).
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
    list_file = os.path.abspath(out + ".txt")
    # Chemins ABSOLUS : évite la résolution relative qui doublait le chemin
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    ok, err = _run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
                    "-c", "copy", "-y", out])
    if os.path.isfile(list_file):
        os.remove(list_file)
    if ok and os.path.isfile(out):
        return True
    print(f"    ⚠️ concat copy échec, fallback ré-encodage : {err[-500:]}")

    # Fallback : concat filter avec ré-encodage
    inputs, parts = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", os.path.abspath(c)]
        parts.append(f"[{i}:v]")
    parts.append("".join(f"[{i}:v]" for i in range(len(clips))) +
                 f"concat=n={len(clips)}:v=1:a=0[out]")
    ok, err = _run(["ffmpeg", *inputs, "-filter_complex", ";".join(parts),
                    "-map", "[out]", "-c:v", VIDEO_CODEC, "-preset", "fast",
                    "-crf", str(VIDEO_CRF), "-pix_fmt", "yuv420p", "-y", out])
    if not ok:
        print(f"    ❌ concat filter : {err[-800:]}")
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
        txt_file = os.path.abspath(os.path.join(BASE_DIR, f"sub_scene_{i}.txt"))
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

    clips = []
    for s in scenes:
        p = os.path.join(ASSETS_DIR, s.get("clip", ""))
        if s.get("clip") and os.path.isfile(p):
            clips.append(p)
    if not clips:
        print("❌ Aucun clip vidéo trouvé — relance 05_animate.py")
        sys.exit(1)

    print(f"\n🎬 [07_editor] Montage final ({len(clips)} clips)\n")

    tmp_video = os.path.join(BASE_DIR, "tmp_video.mp4")
    print("  🎞️  Étape A : concat clips...")
    if not concat_clips(clips, tmp_video):
        print("❌ Concat vidéo échoué")
        sys.exit(1)

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

    print("  📝 Étape C : sous-titres...")
    if add_subtitles(current, scenes, FINAL_VIDEO):
        print(f"  ✅ {FINAL_VIDEO} (avec sous-titres)")
    else:
        subprocess.run(["cp", current, FINAL_VIDEO], check=True)
        print(f"  ✅ {FINAL_VIDEO} (sans sous-titres, fallback)")

    for t in (tmp_video, tmp_av):
        if os.path.isfile(t):
            os.remove(t)

    size_mb = os.path.getsize(FINAL_VIDEO) / (1024 * 1024)
    print(f"\n🎉 Vidéo finale : {FINAL_VIDEO} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()