#!/usr/bin/env python3
"""
Nyavodroid — Dispatcher multi-marques (v2 YAML).
Charge le style depuis themes/<BRAND>.yaml et expose les mêmes noms
que l'ancienne version pour compatibilité totale avec tous les scripts.

BRAND absent / "nyavo" → themes/nyavo.yaml
BRAND = "vis"          → themes/vis.yaml
BRAND = "<autre>"      → themes/<autre>.yaml (futur)

Fallback : nyavo si le YAML demandé est absent.
Les fichiers content_config_nyavo.py / content_config_vis.py restent
disponibles comme legacy mais ne sont plus routés.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
from PIL import ImageFont

try:
    import yaml
except ImportError:
    yaml = None  # fallback : lit le .py legacy

BRAND = os.environ.get("BRAND", "nyavo").strip().lower()
THEMES_DIR = Path(__file__).parent / "themes"


# ──────────────────────────────────────────────
#  Chargement YAML
# ──────────────────────────────────────────────
def _load_yaml(brand: str) -> dict:
    """Charge themes/<brand>.yaml ou fallback nyavo."""
    if yaml is None:
        raise ImportError("PyYAML non installé")
    for candidate in (brand, "nyavo"):
        path = THEMES_DIR / f"{candidate}.yaml"
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return data
    raise FileNotFoundError(f"Aucun thème trouvé dans {THEMES_DIR}")


def _load_style() -> dict:
    """Charge le thème YAML ; fallback sur import .py legacy si PyYAML absent."""
    try:
        data = _load_yaml(BRAND)
        print(f"🎭 Marque active : {BRAND} (YAML)")
        return data
    except (ImportError, FileNotFoundError) as e:
        print(f"⚠️ {e} → fallback legacy .py")
        try:
            _mod = importlib.import_module(f"content_config_{BRAND}")
        except ImportError:
            _mod = importlib.import_module("content_config_nyavo")
            print(f"⚠️ Marque '{BRAND}' sans config → fallback nyavo")
        # Extrait toutes les variables publiques du module legacy
        return {k: v for k, v in _mod.__dict__.items() if not k.startswith("_")}


# ──────────────────────────────────────────────
#  Chargement du style (exécuté à l'import)
# ──────────────────────────────────────────────
_style = _load_style()


def _build_from_yaml(d: dict):
    """Construit toutes les variables module à partir d'un dict YAML."""
    import sys
    me = sys.modules[__name__]

    # ── Couleurs (convertir listes → tuples) ──
    colors = d.get("colors", {})
    me.COLORS = {k: tuple(v) if isinstance(v, list) else v for k, v in colors.items()}

    box_bg = d.get("box_bg", {})
    me.BOX_BG = {k: tuple(v) if isinstance(v, list) else v for k, v in box_bg.items()}

    me.BACKGROUND_GRADIENT = d.get("background_gradient", [])

    # ── Image style ──
    me.STYLE_IMAGE_SUFFIX = d.get("image_style", "")

    # ── Polices ──
    fonts = d.get("fonts", {})
    font_dir = fonts.get("dir", "assets/fonts")
    me.FONT_DIR = font_dir
    me.FONT_REGULAR_PATH = os.path.join(font_dir, fonts.get("regular", "Inter-Regular.ttf"))
    me.FONT_BOLD_PATH = os.path.join(font_dir, fonts.get("bold", "Inter-Bold.ttf"))

    # ── Tailles ──
    sizes = d.get("sizes", {})
    me.ACCROCHE_FONTSIZE = sizes.get("accroche", 44)
    me.FAIT_CHOC_FONTSIZE = sizes.get("fait_choc", 58)
    me.CONSEQUENCE_FONTSIZE = sizes.get("consequence", 28)
    me.SOURCE_FONTSIZE = sizes.get("source", 22)
    me.DETAIL_FONTSIZE = sizes.get("detail", 36)
    me.MARGIN = sizes.get("margin", 54)
    me.BOX_BORDER = sizes.get("box_border", 24)
    me.LINE_SPACING = sizes.get("line_spacing", 14)

    # ── Canvas texte seul ──
    canvas = d.get("canvas", {})
    me.CANVAS_SIZE_TEXTE_SEUL = tuple(canvas.get("size", [1080, 1080]))
    me.CANVAS_MARGIN_TEXTE_SEUL = canvas.get("margin", 90)

    # ── Dimensions ──
    dims = d.get("dimensions", {})
    me.POST_WIDTH, me.POST_HEIGHT = tuple(dims.get("post", [1080, 1350]))
    me.STORY_WIDTH, me.STORY_HEIGHT = tuple(dims.get("story", [1080, 1920]))
    me.MAX_TEXT_WIDTH_POST = me.POST_WIDTH - 2 * me.MARGIN
    me.MAX_TEXT_WIDTH_STORY = me.STORY_WIDTH - 2 * me.MARGIN

    # ── Assets ──
    assets = d.get("assets", {})
    me.EXPRESSIONS_DIR = assets.get("expressions", "assets/expressions")
    me.PROFILE_IMAGE_PATH = assets.get("profile", "assets/profile.png")
    me.EMOJIS_DIR = assets.get("emojis", "assets/emojis")

    # ── Éditorial ──
    editorial = d.get("editorial", {})
    me.TON_EDITORIAL = editorial.get("ton", "")
    me.STORY_PROMPTS = editorial.get("story_prompts", [])

    # ── Piliers ──
    pillars_raw = d.get("pillars", {})
    me.PILLARS = {}
    for key, val in pillars_raw.items():
        me.PILLARS[key] = {
            "label": val.get("label", key),
            "description": val.get("description", ""),
            "mots_cles": val.get("mots_cles", []),
            "categorie": val.get("categorie", "tech"),
        }
    me.PILLAR_KEYS = list(me.PILLARS.keys())

    pillar_weights = d.get("pillar_weights", {})
    me.PILLAR_WEIGHTS = {k: pillar_weights.get(k, 20) for k in me.PILLAR_KEYS}

    me.SUJETS_PAR_PILIER = d.get("sujets_par_pilier", {})


def _build_from_legacy(mod):
    """Construit les variables depuis un module legacy .py (fallback)."""
    import sys
    me = sys.modules[__name__]
    for name in [
        "COLORS", "BOX_BG", "BACKGROUND_GRADIENT",
        "STYLE_IMAGE_SUFFIX", "FONT_DIR", "FONT_REGULAR_PATH", "FONT_BOLD_PATH",
        "ACCROCHE_FONTSIZE", "FAIT_CHOC_FONTSIZE", "CONSEQUENCE_FONTSIZE",
        "SOURCE_FONTSIZE", "DETAIL_FONTSIZE", "MARGIN", "BOX_BORDER", "LINE_SPACING",
        "CANVAS_SIZE_TEXTE_SEUL", "CANVAS_MARGIN_TEXTE_SEUL",
        "POST_WIDTH", "POST_HEIGHT", "STORY_WIDTH", "STORY_HEIGHT",
        "MAX_TEXT_WIDTH_POST", "MAX_TEXT_WIDTH_STORY",
        "EXPRESSIONS_DIR", "PROFILE_IMAGE_PATH", "EMOJIS_DIR",
        "TON_EDITORIAL", "STORY_PROMPTS",
        "PILLARS", "PILLAR_KEYS", "PILLAR_WEIGHTS", "SUJETS_PAR_PILIER",
    ]:
        if hasattr(mod, name):
            setattr(me, name, getattr(mod, name))


# ──────────────────────────────────────────────
#  Construction des variables module
# ──────────────────────────────────────────────
if isinstance(_style, dict) and "PILLARS" not in _style:
    _build_from_yaml(_style)
elif isinstance(_style, dict) and "PILLARS" in _style:
    _build_from_yaml(_style)
else:
    _build_from_legacy(_style)


# ──────────────────────────────────────────────
#  Logique partagée (POLICES + WRAP)
#  → déplacée depuis content_config_nyavo/vis
#  → ré-exportée pour compatibilité totale
# ──────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Retourne la police premium demandée, fallback DejaVu si manquante."""
    path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            fallback = (
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            )
            return ImageFont.truetype(fallback, size)
        except OSError:
            return ImageFont.load_default()


def wrap_text_pillow(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Découpe un texte en lignes en mesurant la largeur réelle de chaque mot."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    current_width = 0

    for word in words:
        word_width = font.getbbox(word)[2]
        space_width = font.getbbox(" ")[2] if current else 0
        new_width = current_width + space_width + word_width
        if new_width <= max_width:
            current.append(word)
            current_width = new_width
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
            current_width = word_width

    if current:
        lines.append(" ".join(current))
    return lines
