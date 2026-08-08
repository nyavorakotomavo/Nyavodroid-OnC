#!/usr/bin/env python3
"""
Nyavodroid — VIS : moteur de publication (définitif).
VIS_FORCE_PILIER=story  → force story (vis_stories.yml)
VIS_EXCLUDE=story       → exclut story (vis.yml)
Texte : Cloudflare d'abord. Images : Cloudflare d'abord (jamais Gemini en 1er).
AUCUN fact_checker.
"""
import os, json, random, sys, time, requests
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
EXCLUDE = [x.strip() for x in os.environ.get("VIS_EXCLUDE", "").split(",") if x.strip()]
SLIDE = 1080
DELAY_ENTRE_SLIDES = 20

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
    """Cloudflare texte d'abord, fallback chaîne classique."""
    if M.CLOUDFLARE_CREDS and hasattr(M, "_t_cloudflare"):
        try:
            print(f"  📝 Texte via Cloudflare {tag}...")
            return M._t_cloudflare(prompt)
        except Exception as e:
            print(f"    ⚠️ Cloudflare texte : {M.sanitize_log(str(e))}")
    return M.texte_avec_fallback(prompt, GEMINI_API_KEY, tag)

def image_vis_garantie(prompt: str, chemin: str, size=(SLIDE, SLIDE)) -> None:
    """Cloudflare image d'abord, JAMAIS Gemini en premier pour vis."""
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
    try:
        print("    🖼️ Hugging Face (fallback)...")
        M._i_hf(prompt_complet, chemin, size)
        return
    except Exception as e:
        print(f"    ⚠️ HF : {e}")
    print("    🖼️ Pollinations (dernier recours)...")
    M._i_pollinations(prompt_complet, chemin)

def generer_fond_story_local(texte: str, chemin: str) -> None:
    """Fond story 1080x1920 : dégradé brun + texte crème + logo cercle."""
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    stops = [(0.0, (92, 64, 51)), (0.5, (62, 39, 35)), (1.0, (26, 18, 11))]
    for y in range(h):
        t = y / h
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]; t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0)
                draw.line([(0, y), (w, y)],
                          fill=tuple(int(c0[j] + (c1[j] - c0[j]) * f) for j in range(3)))
                break
    margin, max_w = 100, w - 200
    size = 58
    texte_propre = M.clean_text(texte)
    while size >= 36:
        font = get_font(size, bold=True)
        lines = wrap_text_pillow(texte_propre, font, max_w)
        ascent, descent = font.getmetrics()
        stride = ascent + descent + 12
        total_h = stride * len(lines)
        if total_h <= h - 2 * margin:
            break
        size -= 4
    y = (h - total_h) // 2
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        draw.text(((w - lw) // 2, y), ln, font=font, fill=(212, 196, 168))
        y += stride
    if os.path.isfile(PROFILE_IMAGE_PATH):
        try:
            s = 140
            logo = Image.open(PROFILE_IMAGE_PATH).convert("RGBA").resize((s, s), Image.LANCZOS)
            mask = Image.new("L", (s, s), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, s, s), fill=255)
            img.paste(logo, (w - s - margin, h - s - 340), mask)
        except Exception:
            pass
    img.save(chemin)

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
    if brut.startswith("```"): brut = brut.strip("`json ")
    return json.loads(brut)

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

def publier_carrousel(chemins: list, legende: str) -> dict:
    if DRY_RUN:
        print("  🧪 DRY RUN — carrousel sauté."); return {"id": "dry-run"}
    ids = []
    for c in chemins:
        with open(c, "rb") as f:
            r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                       data={"published": "false", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(c), f, "image/png")}, timeout=M.TIMEOUT)
        pid = r.json().get("id")
        if not pid: raise ValueError(f"Réponse FB : {r.json()}")
        ids.append(pid)
    attached = [f"{M.FB_PAGE_ID}_{pid}" for pid in ids]
    try:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/feed",
                   data={"message": legende, "attached_images": json.dumps(attached),
                         "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res: raise ValueError(res)
        return res
    except Exception as e:
        print(f"  ⚠️ Carrousel échoué ({e}) → fallback photo unique")
        with open(chemins[0], "rb") as f:
            r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                       data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(chemins[0]), f, "image/png")}, timeout=M.TIMEOUT)
        return r.json()

def publier_parabole() -> dict:
    sujet = random.choice(SUJETS_PAR_PILIER["parabole"])
    print(f"📌 Sujet : {sujet}")
    textes = generer_textes_parabole(sujet)
    chemins = generer_slides(sujet, textes)
    legende = (f"{textes.get('morale','')}\n\n{textes.get('question','')}\n\n"
               "#DeveloppementPersonnel #LeconDeVie #HistoireIllustrée")
    print(f"📌 Légende :\n{legende}")
    return publier_carrousel(chemins, legende)

# ══════════════════════════════════════════
# MORALE / QUESTION
# ══════════════════════════════════════════
def publier_texte_vis(pilier: str) -> dict:
    texte = random.choice(SUJETS_PAR_PILIER[pilier])
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
    try:
        with open(chemin, "rb") as f:
            r = M._req("POST", ep, data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
        res = r.json()
        if "id" not in res: raise ValueError(res)
        return res
    except requests.exceptions.HTTPError as e:
        raise M.fb_error(e, "post texte vis") from e

# ══════════════════════════════════════════
# STORY
# ══════════════════════════════════════════
def publier_story_vis() -> dict:
    texte = random.choice(SUJETS_PAR_PILIER["story"])
    print(f"📌 Story : {texte}")
    chemin = "vis_story.png"
    generer_fond_story_local(texte, chemin)
    img = ajouter_grain(Image.open(chemin)); img.save(chemin)
    if DRY_RUN:
        print("  🧪 DRY RUN — story sautée."); return {"id": "dry-run"}
    ep_photos = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos"
    with open(chemin, "rb") as f:
        r = M._req("POST", ep_photos, data={"published": "false", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
    photo_id = r.json().get("id")
    if not photo_id: raise ValueError(f"Upload story échoué : {r.json()}")
    print(f"  ✅ Photo story uploadée : {photo_id}")
    ep_story = f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photo_stories"
    r = M._req("POST", ep_story, data={"photo_id": photo_id, "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
    res = r.json()
    if "id" not in res: raise ValueError(f"Publication story échouée : {res}")
    print(f"  ✅ Story publiée : {res['id']}")
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
