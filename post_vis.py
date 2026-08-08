#!/usr/bin/env python3
"""
Nyavodroid — VIS : moteur de publication (définitif v2).
- Carrousel AUTO-VÉRIFIÉ : si Facebook publie sans images → suppression + photo garantie.
- Story : fond AQUARELLE IA (Cloudflare) + texte crème, jamais de fond uni Pillow.
VIS_FORCE_PILIER / VIS_EXCLUDE gérés. AUCUN fact_checker.
"""
import os, json, random, sys, time, requests, subprocess
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import nyavo_media as M
from content_config import (
    BRAND, PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, SUJETS_PAR_PILIER,
    STYLE_IMAGE_SUFFIX, TON_EDITORIAL, MARGIN, get_font, wrap_text_pillow,
    COLORS, BOX_BG, PROFILE_IMAGE_PATH,
)

if BRAND != "vis":
    print("⚠️ post_vis.py doit tourner avec BRAND=vis"); sys.exit(1)

GEMINI_API_KEY = M.clean(os.environ["GEMINI_API_KEY_CONTENT"])
DRY_RUN = os.environ.get("VIS_DRY_RUN", "") == "1"
FORCE_PILIER = os.environ.get("VIS_FORCE_PILIER", "").strip().lower()
if FORCE_PILIER in ("aleatoire", "random", "au hasard"):
    FORCE_PILIER = ""
EXCLUDE = [x.strip() for x in os.environ.get("VIS_EXCLUDE", "").split(",") if x.strip()]
SLIDE = 1080
STORY_W, STORY_H = 1080, 1920
DELAY_ENTRE_SLIDES = 20


# ══════════════════════════════════════════
# HISTORIQUE — anti-répétition (30 jours glissants)
# ══════════════════════════════════════════
HISTORY_FILE = "published_history.json"

def charger_historique() -> dict:
    """Charge l'historique des publications (sujet → date ISO)."""
    if not os.path.isfile(HISTORY_FILE):
        return {"publications": []}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"publications": []}

def sauvegarder_historique(hist: dict) -> None:
    """Sauvegarde l'historique et commit automatiquement."""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
    # Auto-commit (ignoré si rien à committer)
    try:
        subprocess.run(['git', 'add', HISTORY_FILE], check=False, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'chore(vis): mise à jour historique publications'],
                       check=False, capture_output=True)
        subprocess.run(['git', 'push'], check=False, capture_output=True)
    except Exception:
        pass  # Pas bloquant si le commit échoue

def sujets_disponibles(pilier: str) -> list:
    """Retourne les sujets non publiés dans les 30 derniers jours."""
    hist = charger_historique()
    cutoff = datetime.now() - timedelta(days=30)
    deja_publies = {
        p["sujet"] for p in hist["publications"]
        if p["pilier"] == pilier and datetime.fromisoformat(p["date"]) > cutoff
    }
    tous = SUJETS_PAR_PILIER[pilier]
    dispo = [s for s in tous if s not in deja_publies]
    if not dispo:
        print(f"  ⚠️ Tous les sujets {pilier} publiés → reset (recyclage)")
        dispo = tous
    return dispo

def enregistrer_publication(pilier: str, sujet: str) -> None:
    """Ajoute une publication à l'historique."""
    hist = charger_historique()
    hist["publications"].append({
        "pilier": pilier,
        "sujet": sujet,
        "date": datetime.now().isoformat()
    })
    # Garde seulement les 90 derniers jours
    cutoff = datetime.now() - timedelta(days=90)
    hist["publications"] = [
        p for p in hist["publications"]
        if datetime.fromisoformat(p["date"]) > cutoff
    ]
    sauvegarder_historique(hist)

SCENES_PARABOLE = [
    ("ACCROCHE",       "Wide establishing shot: a soft brown hill with a winding cream path, blotchy watercolor sun in hazy sky, childlike character (round body, dot eyes) sitting peacefully, large empty cream paper sky at the top"),
    ("MANQUE",         "Close-up: the same childlike character looking down with a small sad curved mouth, soft melancholic brown tones, tender not dramatic, large empty space at top"),
    ("EFFORT RATE",    "The childlike character trying hard to push a big round brown stone uphill, gentle failure, small dust puffs, tender mood, empty space at top"),
    ("DECLIC",         "The childlike character crouching, pointing a tiny finger at a small wilted flower growing in cracked dry earth, intimate close framing, empty space at top"),
    ("TRANSFORMATION", "The childlike character gently offering one drop of water to the small flower, the flower blooming with a soft warm halo of light, joyful gentle mood, empty space at top"),
    ("MORALE",         "The childlike character sitting peacefully beside the now bloomed flower, facing hazy brown mountains and the winding path at golden hour, serene, large empty cream paper space at top"),
]

# ══════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════
def ajouter_grain(img: Image.Image, force: float = 0.06) -> Image.Image:
    w, h = img.size
    bruit = Image.effect_noise((w, h), 20).convert("L")
    gris = Image.merge("RGB", (bruit, bruit, bruit))
    return Image.blend(img.convert("RGB"), gris, force)

def incruste_haut(chemin: str, texte: str, size: int = 56) -> None:
    img = Image.open(chemin).convert("RGBA")
    font = get_font(size, bold=True)
    lines = wrap_text_pillow(M.clean_text(texte), font, SLIDE - 2 * MARGIN)
    ascent, descent = font.getmetrics()
    stride = ascent + descent + 10
    pad = 30
    block_h = stride * len(lines)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, 0, SLIDE, MARGIN + block_h + pad], fill=BOX_BG["blanc_opaque"])
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    y = MARGIN + pad // 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        draw.text(((SLIDE - w) / 2, y), ln, font=font, fill=COLORS["noir"])
        y += stride
    img.convert("RGB").save(chemin)

def incruste_bas_story(chemin: str, texte: str, size: int = 50) -> None:
    """Bandeau espresso translucide en bas (hors zone UI) + texte crème + logo."""
    img = Image.open(chemin).convert("RGBA")
    w, h = img.size
    font = get_font(size, bold=True)
    lines = wrap_text_pillow(M.clean_text(texte), font, w - 2 * MARGIN)
    ascent, descent = font.getmetrics()
    stride = ascent + descent + 10
    pad = 45
    block_h = stride * len(lines)
    top_band = h - 260 - block_h - 2 * pad
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, top_band, w, top_band + block_h + 2 * pad],
                                      fill=(46, 31, 22, 200))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    y = top_band + pad
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        draw.text(((w - lw) / 2, y), ln, font=font, fill=(212, 196, 168))
        y += stride
    if os.path.isfile(PROFILE_IMAGE_PATH):
        try:
            s = 120
            logo = Image.open(PROFILE_IMAGE_PATH).convert("RGBA").resize((s, s), Image.LANCZOS)
            mask = Image.new("L", (s, s), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, s, s), fill=255)
            img.paste(logo, (MARGIN, 170), mask)
        except Exception:
            pass
    img.convert("RGB").save(chemin)

def coller_logo(chemin: str, size: int = 110) -> None:
    if not os.path.isfile(PROFILE_IMAGE_PATH):
        print(f"  ⚠️ Logo introuvable : {PROFILE_IMAGE_PATH}"); return
    img = Image.open(chemin).convert("RGBA")
    logo = Image.open(PROFILE_IMAGE_PATH).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.paste(logo, (MARGIN, MARGIN), mask)
    img.convert("RGB").save(chemin)

def texte_vis_garantie(prompt: str, tag: str = "") -> str:
    if M.CLOUDFLARE_CREDS and hasattr(M, "_t_cloudflare"):
        try:
            print(f"  📝 Texte via Cloudflare {tag}...")
            return M._t_cloudflare(prompt)
        except Exception as e:
            print(f"    ⚠️ Cloudflare texte : {M.sanitize_log(str(e))}")
    return M.texte_avec_fallback(prompt, GEMINI_API_KEY, tag)

def image_vis_garantie(prompt: str, chemin: str, size=(SLIDE, SLIDE)) -> None:
    """Image IA garantie : Cloudflare d'abord (crop ffmpeg), sinon Pollinations."""
    prompt_complet = M.clean_text(prompt) + ", " + STYLE_IMAGE_SUFFIX
    if M.CLOUDFLARE_CREDS:
        try:
            print("    ☁️ Cloudflare image (priorité absolue VIS)...")
            raw = chemin + ".raw.png"
            M._i_cloudflare(prompt_complet, raw)
            M.crop_to_ratio(raw, chemin, target_size=size)
            os.remove(raw)
            print(f"    ✅ Cloudflare ({os.path.getsize(chemin):,} o)")
            return
        except Exception as e:
            print(f"    ⚠️ Cloudflare : {M.sanitize_log(str(e))}")
    print("    🖼️ Pollinations (fallback IA)...")
    M._i_pollinations(prompt_complet, chemin)
    M._crop_resize_pillow(Image.open(chemin), size).save(chemin)
    print(f"    ✅ Pollinations ({os.path.getsize(chemin):,} o)")

# ══════════════════════════════════════════
# PARABOLE
# ══════════════════════════════════════════
def generer_textes_parabole(sujet: str) -> dict:
    prompt = (
        "Tu es un auteur d'albums jeunesse pour adultes. "
        f"{TON_EDITORIAL}\nSujet : {sujet}\n"
        'Réponds UNIQUEMENT en JSON : {"titre": "max 6 mots", '
        '"morale": "max 12 mots", "question": "question bienveillante max 12 mots"}'
    )
    print("  📝 Génération titres/morale/question...")
    brut = texte_vis_garantie(prompt, "[parabole]").strip()
    
    # Nettoyage robuste du JSON (Cloudflare peut retourner du texte parasite)
    brut = re.sub(r'^```(?:json)?\s*', '', brut)
    brut = re.sub(r'\s*```$', '', brut)
    brut = brut.strip()
    
    # Extrait le premier objet JSON valide
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(brut)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    
    # Fallback : cherche { ... } dans le texte
    match = re.search(r'\{[^{}]*"titre"[^{}]*\}', brut, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Dernier recours : valeurs par défaut
    print("  ⚠️ JSON invalide → valeurs par défaut")
    return {
        "titre": sujet.split("(")[0].strip()[:40],
        "morale": "Les petits pas font les grands chemins.",
        "question": "Quel petit pas fais-tu aujourd'hui ?"
    }

def generer_slides(sujet: str, textes: dict) -> list:
    chemins = []
    for i, (acte, visuel) in enumerate(SCENES_PARABOLE, 1):
        chemin = f"vis_slide_{i}.png"
        if i > 1:
            print(f"  ⏳ Pause : {DELAY_ENTRE_SLIDES}s...")
            time.sleep(DELAY_ENTRE_SLIDES)
        print(f"  🖼️ Slide {i}/6 [{acte}]...")
        prompt = (f"Scene {i}/6 — {acte}. {visuel}. Story theme: {sujet}. "
                  "Square format, same character design across all scenes.")
        image_vis_garantie(prompt, chemin, size=(SLIDE, SLIDE))
        img = ajouter_grain(Image.open(chemin)); img.save(chemin)
        if i == 1: incruste_haut(chemin, textes.get("titre", ""))
        if i == 6: incruste_haut(chemin, f"{textes.get('morale','')}  •  {textes.get('question','')}", size=44)
        chemins.append(chemin)
    return chemins

def _upload_photo_non_publiee(chemin: str) -> str:
    with open(chemin, "rb") as f:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                   data={"published": "false", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
    pid = r.json().get("id")
    if not pid: raise ValueError(f"Upload échoué : {r.json()}")
    return pid

def _post_a_des_images(post_id: str) -> bool:
    """Vérifie que le post publié contient bien des photos."""
    try:
        r = M._req("GET", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{post_id}",
                   params={"fields": "attachments", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   timeout=M.TIMEOUT)
        att = r.json().get("attachments", {}).get("data", [])
        ok = any(a.get("type") in ("photo", "album", "video", "share") for a in att)
        print(f"  🔎 Vérification post : {'images présentes ✅' if ok else 'AUCUNE image ❌'}")
        return ok
    except Exception as e:
        print(f"  ⚠️ Vérification impossible ({e}) → on garde le post")
        return True

def publier_carrousel(chemins: list, legende: str) -> dict:
    if DRY_RUN:
        print("  🧪 DRY RUN — carrousel sauté."); return {"id": "dry-run"}
    ids = [_upload_photo_non_publiee(c) for c in chemins]
    attached = [f"{M.FB_PAGE_ID}_{pid}" for pid in ids]
    res = None
    try:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/feed",
                   data={"message": legende, "attached_images": json.dumps(attached),
                         "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res: raise ValueError(res)
    except Exception as e:
        print(f"  ⚠️ Carrousel échoué ({e})")
    # AUTO-VÉRIFICATION : si le post est sorti SANS images → suppression + photo garantie
    if res and _post_a_des_images(res["id"]):
        return res
    if res:
        print("  🗑️ Post texte seul détecté → suppression...")
        try:
            M._req("DELETE", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{res['id']}",
                   params={"access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        except Exception as e:
            print(f"  ⚠️ Suppression : {e}")
    print("  📷 Republication garantie avec photo (slide 1)...")
    with open(chemins[0], "rb") as f:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                   data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemins[0]), f, "image/png")}, timeout=M.TIMEOUT)
    out = r.json()
    if "id" not in out: raise ValueError(out)
    return out

def publier_parabole() -> dict:
    sujet = random.choice(sujets_disponibles("parabole"))
    print(f"📌 Sujet : {sujet}")
    textes = generer_textes_parabole(sujet)
    chemins = generer_slides(sujet, textes)
    legende = (f"{textes.get('morale','')}\n\n{textes.get('question','')}\n\n"
               "#DeveloppementPersonnel #LeconDeVie #HistoireIllustrée")
    print(f"📌 Légende :\n{legende}")
    res = publier_carrousel(chemins, legende)
    if res.get("id") and res["id"] != "dry-run":
        enregistrer_publication("parabole", sujet)
    return res

# ══════════════════════════════════════════
# MORALE / QUESTION
# ══════════════════════════════════════════
def publier_texte_vis(pilier: str) -> dict:
    texte = random.choice(sujets_disponibles(pilier))
    print(f"📌 Texte : {texte}")
    chemin = "vis_texte.png"
    M.generer_fond_texte_seul(texte, chemin)
    img = ajouter_grain(Image.open(chemin)); img.save(chemin)
    coller_logo(chemin)
    tags = ("#DeveloppementPersonnel #ParlonsEn" if pilier == "question"
            else "#DeveloppementPersonnel #LeconDeVie")
    legende = f"{texte}\n\n{tags}"
    if DRY_RUN:
        print("  🧪 DRY RUN — texte sauté."); return {"id": "dry-run"}
    ep = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    with open(chemin, "rb") as f:
        r = M._req("POST", ep, data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
    res = r.json()
    if "id" not in res: raise ValueError(res)
    return res

# ══════════════════════════════════════════
# STORY — fond AQUARELLE IA + texte crème
# ══════════════════════════════════════════
def publier_story_vis() -> dict:
    texte = random.choice(sujets_disponibles("story"))
    print(f"📌 Story : {texte}")
    chemin = "vis_story.png"
    prompt = ("Serene watercolor landscape at golden hour, rolling brown hills, winding cream "
              "path, blotchy warm sun in hazy sky, a single small tree, heavy cold press paper "
              "grain, 1950s European children's book illustration, monochrome brown palette, "
              "no characters, vertical composition, large calm sky")
    print("  🖼️ Fond story IA (aquarelle brune)...")
    image_vis_garantie(prompt, chemin, size=(STORY_W, STORY_H))
    img = ajouter_grain(Image.open(chemin)); img.save(chemin)
    incruste_bas_story(chemin, texte)
    if DRY_RUN:
        print("  🧪 DRY RUN — story sautée."); return {"id": "dry-run"}
    pid = _upload_photo_non_publiee(chemin)
    print(f"  ✅ Photo story uploadée : {pid}")
    r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photo_stories",
               data={"photo_id": pid, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
    res = r.json()
    if "id" not in res: raise ValueError(f"Publication story échouée : {res}")
    print(f"  ✅ Story publiée : {res['id']}")
    enregistrer_publication("story", texte)
    return res

# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
def main() -> None:
    print("=" * 60)
    print("🎨 VIS — Paraboles & leçons (sans fact-check)")
    print("=" * 60)
    if not DRY_RUN:
        M.verify_fb_token()
    else:
        print("🧪 DRY RUN activé.")
    if FORCE_PILIER:
        if FORCE_PILIER not in PILLAR_KEYS:
            print(f"❌ VIS_FORCE_PILIER={FORCE_PILIER} invalide (valides : {PILLAR_KEYS})")
            sys.exit(1)
        pilier = FORCE_PILIER
        print(f"🎯 Pilier forcé : {PILLARS[pilier]['label']}")
    else:
        dispo = [k for k in PILLAR_KEYS if k not in EXCLUDE] or PILLAR_KEYS
        pilier = random.choices(dispo, weights=[PILLAR_WEIGHTS[k] for k in dispo], k=1)[0]
        print(f"🎲 Pilier tiré : {PILLARS[pilier]['label']}")
    if pilier == "parabole":   res = publier_parabole()
    elif pilier == "story":    res = publier_story_vis()
    else:                      res = publier_texte_vis(pilier)
    print(f"\n{'='*60}\n✅ TERMINÉ — ID : {res.get('id','N/A')}\n{'='*60}")

if __name__ == "__main__":
    try: main()
    except RuntimeError as e: print(f"\n❌ {e}", file=sys.stderr); sys.exit(1)
    except KeyError as e:     print(f"\n❌ Secret : {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:    print(f"\n❌ {type(e).__name__}: {e}", file=sys.stderr); sys.exit(1)
