#!/usr/bin/env python3
"""
Nyavodroid — VIS : moteur de publication (définitif v4).
Répartition images :
  - Parabole (6 slides) + Story  → IA aquarelle (Cloudflare)
  - Morale + Question            → Pillow (dégradé brun + texte crème)
Publication TOUJOURS via /photos (image garantie visible sur la page).
Carrousel parabole tenté en bonus ; sinon post photo slide 1 garanti.
Historique anti-répétition auto-commité (30 jours). AUCUN fact_checker.
"""
import os, re, json, random, sys, time, requests, subprocess
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import nyavo_media as M
from content_config import (
    BRAND, PILLAR_KEYS, PILLAR_WEIGHTS, PILLARS, SUJETS_PAR_PILIER,
    TON_EDITORIAL, MARGIN, get_font, wrap_text_pillow,
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
HISTORY_FILE = "published_history.json"

SCENES_PARABOLE = [
    ("ACCROCHE",       "Wide establishing shot: a soft brown hill with a winding cream path, blotchy watercolor sun in hazy sky, childlike character (round body, dot eyes) sitting peacefully, large empty cream paper sky at the top"),
    ("MANQUE",         "Close-up: the same childlike character looking down with a small sad curved mouth, soft melancholic brown tones, tender not dramatic, large empty space at top"),
    ("EFFORT RATE",    "The childlike character trying hard to push a big round brown stone uphill, gentle failure, small dust puffs, tender mood, empty space at top"),
    ("DECLIC",         "The childlike character crouching, pointing a tiny finger at a small wilted flower growing in cracked dry earth, intimate close framing, empty space at top"),
    ("TRANSFORMATION", "The childlike character gently offering one drop of water to the small flower, the flower blooming with a soft warm halo of light, joyful gentle mood, empty space at top"),
    ("MORALE",         "The childlike character sitting peacefully beside the now bloomed flower, facing hazy brown mountains and the winding path at golden hour, serene, large empty cream paper space at top"),
]

# ══════════════════════════════════════════
# HISTORIQUE anti-répétition (30 jours)
# ══════════════════════════════════════════
def charger_historique() -> dict:
    if not os.path.isfile(HISTORY_FILE):
        return {"publications": []}
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"publications": []}

def sauvegarder_historique(hist: dict) -> None:
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
    try:
        subprocess.run(['git', 'add', HISTORY_FILE], check=False, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'chore(vis): historique publications'],
                       check=False, capture_output=True)
        subprocess.run(['git', 'push'], check=False, capture_output=True)
    except Exception:
        pass

def sujets_disponibles(pilier: str) -> list:
    hist = charger_historique()
    cutoff = datetime.now() - timedelta(days=60)
    deja = {p["sujet"] for p in hist["publications"]
            if p["pilier"] == pilier and datetime.fromisoformat(p["date"]) > cutoff}
    dispo = [s for s in SUJETS_PAR_PILIER[pilier] if s not in deja]
    if not dispo:
        print("  ⚠️ Tous les sujets publiés → recyclage")
        dispo = SUJETS_PAR_PILIER[pilier]
    return dispo

def enregistrer_publication(pilier: str, sujet: str) -> None:
    hist = charger_historique()
    hist["publications"].append({"pilier": pilier, "sujet": sujet,
                                 "date": datetime.now().isoformat()})
    cutoff = datetime.now() - timedelta(days=90)
    hist["publications"] = [p for p in hist["publications"]
                            if datetime.fromisoformat(p["date"]) > cutoff]
    sauvegarder_historique(hist)

# ══════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════
def ajouter_grain(img: Image.Image, force: float = 0.06) -> Image.Image:
    w, h = img.size
    bruit = Image.effect_noise((w, h), 20).convert("L")
    gris = Image.merge("RGB", (bruit, bruit, bruit))
    return Image.blend(img.convert("RGB"), gris, force)

def _crop_pillow(img: Image.Image, size) -> Image.Image:
    tw, th = size
    w, h = img.size
    r = max(tw / w, th / h)
    img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
    w, h = img.size
    left, top = (w - tw) // 2, (h - th) // 2
    return img.crop((left, top, left + tw, top + th))

def incruste_haut(chemin: str, texte: str, size: int = 56) -> None:
    """Bandeau crème + texte espresso (pour slides IA)."""
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
    """Bandeau espresso en bas + texte crème + logo (story IA)."""
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
    ImageDraw.Draw(overlay).rectangle([0, top_band, w, top_band + block_h + 2 * pad], fill=(46, 31, 22, 200))
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
    """Logo cercle en haut à gauche (posts Pillow)."""
    if not os.path.isfile(PROFILE_IMAGE_PATH):
        return
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
    """Image IA : Cloudflare d'abord, Pollinations en fallback."""
    prompt_complet = M.clean_text(prompt)
    if M.CLOUDFLARE_CREDS:
        try:
            print("    ☁️ Cloudflare image (IA)...")
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
    _crop_pillow(Image.open(chemin), size).save(chemin)
    print(f"    ✅ Pollinations ({os.path.getsize(chemin):,} o)")

# ══════════════════════════════════════════
# PUBLICATION (toujours /photos → image garantie)
# ══════════════════════════════════════════
def _publier_photo(chemin: str, legende: str) -> dict:
    """Post photo GARANTI : l'image est toujours visible sur la page."""
    if DRY_RUN:
        print("  🧪 DRY RUN — photo sautée."); return {"id": "dry-run"}
    with open(chemin, "rb") as f:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                   data={"caption": legende, "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
    out = r.json()
    if "id" not in out: raise ValueError(out)
    print(f"  ✅ Post photo publié (image garantie) : {out['id']}")
    return out

def _upload_photo_non_publiee(chemin: str) -> str:
    with open(chemin, "rb") as f:
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/photos",
                   data={"published": "false", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                   files={"source": (os.path.basename(chemin), f, "image/png")}, timeout=M.TIMEOUT)
    pid = r.json().get("id")
    if not pid: raise ValueError(f"Upload échoué : {r.json()}")
    return pid

def _post_a_des_images(post_id: str) -> bool:
    try:
        r = requests.get(f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{post_id}",
                         params={"fields": "attachments", "access_token": M.FB_PAGE_ACCESS_TOKEN},
                         timeout=M.TIMEOUT)
        att = r.json().get("attachments", {}).get("data", [])
        ok = any(a.get("type") in ("photo", "album", "video", "share") for a in att)
        print(f"  🔎 Vérification : {'images présentes ✅' if ok else 'AUCUNE image ❌'}")
        return ok
    except Exception as e:
        print(f"  ⚠️ Vérification impossible ({e}) → on garde")
        return True

def _supprimer_post(post_id: str) -> None:
    try:
        requests.delete(f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{post_id}",
                        params={"access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        print("  🗑️ Post supprimé")
    except Exception as e:
        print(f"  ⚠️ Suppression : {e}")

# ══════════════════════════════════════════
# PARABOLE — IA (6 slides) + carrousel bonus
# ══════════════════════════════════════════
def incruste_slide(chemin: str, texte: str, size: int = 64) -> None:
    """Texte court centré en BAS de la slide, bandeau sombre translucide (style mind_vision)."""
    img = Image.open(chemin).convert("RGBA")
    w, h = img.size
    font = get_font(size, bold=True)
    lines = wrap_text_pillow(M.clean_text(texte), font, w - 2 * MARGIN)
    ascent, descent = font.getmetrics()
    stride = ascent + descent + 8
    block_h = stride * len(lines)
    pad = 50
    top_band = h - block_h - 2 * pad - 40
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # dégradé sombre vers le bas pour lisibilité
    for yy in range(top_band, h):
        alpha = int(200 * (yy - top_band) / (h - top_band))
        od.line([(0, yy), (w, yy)], fill=(20, 12, 8, min(alpha, 210)))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    y = h - block_h - pad - 40
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        # ombre portée
        draw.text(((w - lw) / 2 + 2, y + 2), ln, font=font, fill=(0, 0, 0, 180))
        draw.text(((w - lw) / 2, y), ln, font=font, fill=(255, 244, 224))
        y += stride
    img.convert("RGB").save(chemin)

def generer_textes_parabole(sujet: str) -> dict:
    prompt = (
        "Carrousel Instagram motivationnel, narration visuelle en 6 slides.\n"
        f"SUJET (à illustrer LITTÉRALEMENT) : {sujet}\n\n"
        "RÈGLE D'OR : chaque image doit montrer EXACTEMENT et CONCRÈTEMENT les objets/animaux/personnes du sujet. "
        "Si le sujet parle d'un aigle et d'un corbeau, l'image DOIT montrer un aigle et un corbeau. Pas de métaphore abstraite.\n\n"
        "Réponds UNIQUEMENT en JSON valide, sans markdown, avec exactement ces clés :\n"
        '{"s1": {"txt": "accroche choc FR entre guillemets 2-5 mots", "img": "EN ANGLAIS, 8-12 mots max, scène 1 littérale du sujet"}, '
        '"s2": {"txt": "FR 3-6 mots", "img": "EN 8-12 mots, scène 2 littérale"}, '
        '"s3": {"txt": "FR 3-6 mots", "img": "EN 8-12 mots, scène 3 littérale"}, '
        '"s4": {"txt": "FR déclic 3-6 mots", "img": "EN 8-12 mots, scène 4 littérale"}, '
        '"s5": {"txt": "FR 3-6 mots", "img": "EN 8-12 mots, scène 5 littérale"}, '
        '"s6": {"txt": "FR morale 5-10 mots", "img": "EN 8-12 mots, scène finale littérale"}, '
        '"caption": "FR légende 2 phrases + question"}\n'
        "img = description photo-réaliste courte et littérale en anglais. txt = texte français percutant inédit."
    )
    print("  📝 Génération titres/morale/question...")
    brut = texte_vis_garantie(prompt, "[parabole]").strip()
    brut = re.sub(r'^```(?:json)?\s*', '', brut)
    brut = re.sub(r'\s*```$', '', brut).strip()
    try:
        obj, _ = json.JSONDecoder().raw_decode(brut)
        if isinstance(obj, dict) and "titre" in obj:
            return obj
    except Exception:
        pass
    s, e = brut.find("{"), brut.rfind("}")
    if s != -1 and e > s:
        try:
            obj = json.loads(brut[s:e+1])
            if isinstance(obj, dict) and "titre" in obj:
                return obj
        except Exception:
            pass
    m = re.search(r'\{[^{}]*"titre"[^{}]*\}', brut, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    print("  ⚠️ JSON invalide → valeurs dérivées du sujet")
    base = sujet.split("(")[0].strip()
    base_en = base.lower()
    return {
        "s1": {"txt": f"\"{base}.\"", "img": f"a dramatic literal scene of {base_en}, cinematic golden light"},
        "s2": {"txt": "Tout commence petit.", "img": f"tiny beginning of {base_en}, close-up, warm light"},
        "s3": {"txt": "Personne n'y croit.", "img": f"doubt and struggle around {base_en}, moody atmosphere"},
        "s4": {"txt": "Et pourtant...", "img": f"the turning point about {base_en}, ray of hope"},
        "s5": {"txt": "Le temps fait son œuvre.", "img": f"transformation of {base_en}, golden hour"},
        "s6": {"txt": f"{base} : la patience gagne.", "img": f"serene resolution of {base_en}, peaceful wide shot"},
        "caption": f"{base}. Et toi, que laisses-tu grandir doucement ? #Motivation",
    }

def generer_slides(sujet: str, textes: dict) -> list:
    chemins = []
    for i in range(1, 7):
        chemin = f"vis_slide_{i}.png"
        if i > 1:
            print(f"  ⏳ Pause : {DELAY_ENTRE_SLIDES}s...")
            time.sleep(DELAY_ENTRE_SLIDES)
        bloc = textes.get(f"s{i}", {})
        if isinstance(bloc, str):
            bloc = {"txt": bloc, "img": ""}
        txt_slide = bloc.get("txt", "")
        desc_img = bloc.get("img", f"literal scene of {sujet}")
        print(f"  🖼️ Slide {i}/6 (IA) : {desc_img[:70]}...")
        # prompt COURT et littéral pour que flux dessine exactement la scène
        prompt = f"{desc_img}, cinematic warm golden amber lighting, dramatic atmosphere, highly detailed digital illustration, square composition, no text"
        image_vis_garantie(prompt, chemin, size=(SLIDE, SLIDE))
        img = ajouter_grain(Image.open(chemin)); img.save(chemin)
        if txt_slide:
            incruste_slide(chemin, txt_slide, size=70 if i in (1, 6) else 60)
        chemins.append(chemin)
    return chemins

def publier_parabole() -> dict:
    sujet = random.choice(sujets_disponibles("parabole"))
    print(f"📌 Sujet : {sujet}")
    textes = generer_textes_parabole(sujet)
    chemins = generer_slides(sujet, textes)
    cap = textes.get("caption", "")
    if not cap:
        s6 = textes.get("s6", {})
        cap = s6.get("txt", "") if isinstance(s6, dict) else str(s6)
    legende = f"{cap}\n\n#DeveloppementPersonnel #LeconDeVie #HistoireIllustrée #Motivation"
    print(f"📌 Légende :\n{legende}")

    # ── Méthode 1 : carrousel attached_images (format ID brut, numéroté 1/6) ──
    res_photo = _publier_photo(chemins[0], legende)
    try:
        ids = [_upload_photo_non_publiee(ch) for ch in chemins]
        # ordre des formats : brut d'abord (marche sur Pages récentes), puis préfixé
        for nom, attached in [("brut", ids), ("préfixé", [f"{M.FB_PAGE_ID}_{p}" for p in ids])]:
            try:
                print(f"  📤 Tentative CARROUSEL (format {nom})...")
                r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/feed",
                           data={"message": legende, "attached_images": json.dumps(attached),
                                 "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
                res = r.json()
                if "id" not in res: raise ValueError(res)
                if _post_a_des_images(res["id"]):
                    print(f"  ✅ CARROUSEL 6 slides OK (format {nom}) → suppression post simple")
                    _supprimer_post(res_photo["id"])
                    enregistrer_publication("parabole", sujet)
                    return res
                _supprimer_post(res["id"])
            except Exception as e:
                print(f"  ⚠️ Carrousel {nom} échoué : {e}")
    except Exception as e:
        print(f"  ⚠️ Carrousel abandonné : {e}")

    # ── Méthode 2 : album 6 photos (grille) ──
    try:
        print("  📚 Tentative ALBUM 6 slides...")
        r = M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{M.FB_PAGE_ID}/albums",
                   data={"name": cap[:100] or "Parabole vis", "message": legende,
                         "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        album = r.json()
        album_id = album.get("id")
        if not album_id: raise ValueError(album)
        for ch in chemins:
            with open(ch, "rb") as f:
                M._req("POST", f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{album_id}/photos",
                       data={"access_token": M.FB_PAGE_ACCESS_TOKEN},
                       files={"source": (os.path.basename(ch), f, "image/png")}, timeout=M.TIMEOUT)
        # L'album crée un post ; on récupère son ID via le lien de l'album
        r2 = requests.get(f"https://graph.facebook.com/{M.GRAPH_API_VERSION}/{album_id}",
                          params={"fields": "link,id", "access_token": M.FB_PAGE_ACCESS_TOKEN}, timeout=M.TIMEOUT)
        print(f"  ✅ Album publié : {album_id} (6 slides en grille)")
        enregistrer_publication("parabole", sujet)
        return {"id": album_id, "type": "album"}
    except Exception as e:
        print(f"  ⚠️ Album échoué ({e}) → fallback photos individuelles")

    # ── Méthode 3 fallback : slides 2-6 en photos individuelles (slide 1 déjà publiée) ──
    print("  📷 Fallback : slides 2-6 en photos individuelles...")
    dernier = res_photo
    for idx in range(2, 7):
        s = textes.get(f"s{idx}", {})
        txt = s.get("txt", "") if isinstance(s, dict) else str(s)
        leg_i = f"({idx}/6) {txt}\n\n#Motivation"
        dernier = _publier_photo(chemins[idx - 1], leg_i)
        time.sleep(3)
    enregistrer_publication("parabole", sujet)
    return dernier

# ══════════════════════════════════════════
# MORALE / QUESTION — Pillow (dégradé brun + texte)
# ══════════════════════════════════════════
def publier_texte_vis(pilier: str) -> dict:
    texte = random.choice(sujets_disponibles(pilier))
    print(f"📌 Texte ({pilier}, Pillow) : {texte}")
    chemin = "vis_texte.png"
    M.generer_fond_texte_seul(texte, chemin)   # dégradé brun + texte crème
    img = ajouter_grain(Image.open(chemin)); img.save(chemin)
    coller_logo(chemin)
    tags = ("#DeveloppementPersonnel #ParlonsEn" if pilier == "question"
            else "#DeveloppementPersonnel #LeconDeVie")
    legende = f"{texte}\n\n{tags}"
    res = _publier_photo(chemin, legende)
    enregistrer_publication(pilier, texte)
    return res

# ══════════════════════════════════════════
# STORY — IA aquarelle 9:16
# ══════════════════════════════════════════
def publier_story_vis() -> dict:
    texte = random.choice(sujets_disponibles("story"))
    print(f"📌 Story (IA) : {texte}")
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
