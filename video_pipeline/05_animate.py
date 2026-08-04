#!/usr/bin/env python3
"""
Phase 5 — Animation des visuels.
Entrée  : scenes.json (avec images déjà téléchargées)
Sortie  : video_pipeline/assets/scene_XXX.mp4 (clips animés)

Animations FFmpeg :
- zoom_in    : zoom avant progressif
- zoom_out   : zoom arrière progressif
- pan_left   : déplacement horizontal gauche→droite
- pan_right  : déplacement horizontal droite→gauche
- pan_up     : déplacement vertical bas→haut
- pan_down   : déplacement vertical haut→bas
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_pipeline.config_video import (
    BASE_DIR, SCENES_FILE, ASSETS_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS
)


def animate_scene(image_path: str, output_path: str, animation: str, duration: float) -> bool:
    fps = VIDEO_FPS
    frames = int(duration * fps)
    
    # On agrandit l'image de 20% pour éviter les bords noirs lors du zoom
    scale_w = int(VIDEO_WIDTH * 1.25)
    scale_h = int(VIDEO_HEIGHT * 1.25)

    if animation == "zoom_in":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='min(zoom+0.001,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    elif animation == "zoom_out":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='if(lte(zoom,1.0),1.2,max(zoom-0.001,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    elif animation == "pan_left":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='1.2':x='iw/2-(iw/zoom/2)+on*2':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    elif animation == "pan_right":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='1.2':x='iw/2-(iw/zoom/2)-on*2':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    elif animation == "pan_up":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='1.2':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+on*2'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    elif animation == "pan_down":
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='1.2':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)-on*2'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    else:
        filter_complex = (
            f"scale={scale_w}:{scale_h},"
            f"zoompan=z='min(zoom+0.0005,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        )
    
    cmd = [
        "ffmpeg", "-loop", "1", "-i", image_path,
        "-vf", filter_complex,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-y", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 1024
    except subprocess.CalledProcessError as e:
        print(f"    ❌ FFmpeg échec : {e.stderr[:300]}")
        return False

def main():
    if not os.path.isfile(SCENES_FILE):
        print(f"❌ {SCENES_FILE} introuvable — lance 04_visuals.py d'abord")
        sys.exit(1)
    
    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    scenes = doc.get("scenes", [])
    if not scenes:
        print("❌ scenes.json vide")
        sys.exit(1)
    
    print(f"\n🎬 [05_animate] Animation de {len(scenes)} scènes\n")
    
    success_count = 0
    fail_count = 0
    
    for scene in scenes:
        idx = scene.get("scene", "?")
        image_path = os.path.join(ASSETS_DIR, scene.get("image", ""))
        clip_path = os.path.join(ASSETS_DIR, scene.get("image", "").replace(".jpg", ".mp4"))
        animation = scene.get("animation", "zoom_in")
        duration = scene.get("duration", 3.0)
        
        print(f"  [{idx}/{len(scenes)}] {animation} ({duration:.1f}s)")
        
        if not os.path.isfile(image_path):
            print(f"    ❌ Image manquante : {image_path}")
            fail_count += 1
            continue
        
        ok = animate_scene(image_path, clip_path, animation, duration)
        if ok:
            scene["clip"] = os.path.basename(clip_path)
            success_count += 1
            print(f"    ✅ {clip_path}")
        else:
            fail_count += 1
    
    # Mise à jour de scenes.json
    with open(SCENES_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'─'*50}")
    print(f"📊 Bilan : {success_count} clips animés, {fail_count} échecs")
    print(f"✅ {SCENES_FILE} mis à jour")


if __name__ == "__main__":
    main()