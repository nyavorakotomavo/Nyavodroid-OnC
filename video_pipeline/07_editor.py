#!/usr/bin/env python3
"""
Phase 7 — Montage final premium (charte Nyavodroid).
- Sous-titres SANS boîtes : contour noir + ombre, police Poppins/DejaVu Bold
- Animations fade-in/fade-out (0.3s)
- Safe zone 9:16 (marges pour interface FB/TikTok)
- Logo rond en haut à gauche
- Fallbacks garantis
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR, FINAL_VIDEO, VIDEO_CODEC, VIDEO_CRF
)
from content_config import PROFILE_IMAGE_PATH

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Safe zones (marges pour éviter l'interface FB/TikTok)
SAFE_TOP = 180
SAFE_BOTTOM = 250


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return (r.returncode == 0), r.stderr
    except Exception as e:
        return False, str(e)


def probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def concat_clips(clips, out):
    list_file = os.path.abspath(out + ".txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    ok, err = _run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", "-y", out])
    if os.path.isfile(list_file): os.remove(list_file)
    if ok and os.path.isfile(out): return True
    print(f"    ⚠️ concat copy échec : {err[-400:]}")
    inputs, parts = [], []
    for i, c in enumerate(clips):
        inputs += ["-i", os.path.abspath(c)]
        parts.append(f"[{i}:v]")
    parts.append("".join(f"[{i}:v]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=0:a=0[out]")
    ok, err = _run(["ffmpeg", *inputs, "-filter_complex", ";".join(parts), "-map", "[out]",
                    "-c:v", VIDEO_CODEC, "-preset", "fast", "-crf", str(VIDEO_CRF),
                    "-pix_fmt", "yuv420p", "-y", out])
    return ok and os.path.isfile(out)

def build_video_filter(subs, has_logo):
    parts, cur = [], "[0:v]"
    if has_logo:
        parts.append("[1:v]scale=120:120,format=rgba[lg]")
        parts.append(f"{cur}[lg]overlay=40:40[base]")
        cur = "[base]"
    for i, (txt, s, e) in enumerate(subs):
        tf = os.path.abspath(os.path.join(BASE_DIR, f"sub_{i}.txt"))
        with open(tf, "w", encoding="utf-8") as f:
            f.write(txt)
        nxt = f"[dt{i}]"
        # Sous-titres centrés (milieu vertical + horizontal) + très visibles
        alpha_expr = f"if(lt(t-{s:.2f},0.3),(t-{s:.2f})/0.3,if(gt(t,{e:.2f}-0.3),({e:.2f}-t)/0.3,1))"
        parts.append(
            f"{cur}drawtext=fontfile={FONT_BOLD}:textfile='{tf}':fontsize=64:"
            f"fontcolor=white:borderw=6:bordercolor=black:shadowx=4:shadowy=4:shadowcolor=black@0.8:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"alpha='{alpha_expr}':enable='between(t,{s:.2f},{e:.2f})'{nxt}")
        cur = nxt
    return ";".join(parts), cur


def main():
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    scenes = doc.get("scenes", [])

    pairs = []
    for s in scenes:
        p = os.path.join(ASSETS_DIR, s.get("clip", ""))
        if s.get("clip") and os.path.isfile(p):
            pairs.append((s, p))
    if not pairs:
        print("❌ Aucun clip — relance 05_animate.py"); sys.exit(1)
    clips = [p for _, p in pairs]

    subs, t = [], 0.0
    for (s, p) in pairs:
        d = probe_duration(p)
        txt = s.get("subtitle_text", "")
        if txt: subs.append((txt, t, t + d))
        t += d

    print(f"\n🎬 [07_editor] Montage ({len(clips)} clips, {len(subs)} sous-titres)\n")

    tmp_video = os.path.join(BASE_DIR, "tmp_video.mp4")
    if not concat_clips(clips, tmp_video):
        print("❌ Concat échoué"); sys.exit(1)

    mixed = os.path.join(BASE_DIR, "mixed_audio.mp3")
    current = tmp_video
    if os.path.isfile(mixed):
        tmp_av = os.path.join(BASE_DIR, "tmp_av.mp4")
        ok, _ = _run(["ffmpeg", "-i", tmp_video, "-i", mixed, "-c", "copy", "-shortest", "-y", tmp_av])
        if ok: current = tmp_av

    has_logo = os.path.isfile(PROFILE_IMAGE_PATH)
    vf, out_stream = build_video_filter(subs, has_logo)
    inputs = ["-i", current] + (["-i", PROFILE_IMAGE_PATH] if has_logo else [])
    ok, err = _run(["ffmpeg", *inputs, "-filter_complex", vf,
                    "-map", out_stream, "-map", "0:a", "-c:a", "copy",
                    "-c:v", VIDEO_CODEC, "-preset", "fast", "-crf", str(VIDEO_CRF), "-y", FINAL_VIDEO])
    if not ok:
        print(f"    ⚠️ filtre échec, fallback brut : {err[-400:]}")
        subprocess.run(["cp", current, FINAL_VIDEO], check=True)

    for t_ in (tmp_video, os.path.join(BASE_DIR, "tmp_av.mp4")):
        if os.path.isfile(t_): os.remove(t_)
    print(f"\n🎉 {FINAL_VIDEO} ({os.path.getsize(FINAL_VIDEO)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()