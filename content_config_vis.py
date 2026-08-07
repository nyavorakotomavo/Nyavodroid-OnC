#!/usr/bin/env python3
"""
Nyavodroid — Configuration éditoriale de la marque VIS (ÉTAPE 2 — définitif).
Univers : album jeunesse aquarelle brune (esprit Ella, Oscar & Hoo).
Mascotte : NVISS — cercle PLAT avec visage (2 yeux-points + sourire), PAS un nuage.
Fiction morale : AUCUN fact-checking sur cette marque.
"""
import os
from PIL import ImageFont

# ── Piliers éditoriaux (fiction) ──
PILLARS = {
    "parabole": {
        "label": "Parabole illustrée",
        "description": "Histoire morale courte en 6 slides, protagoniste abstrait ou environnement.",
        "mots_cles": ["patience", "confiance", "gratitude", "résilience", "acceptation"],
        "categorie": "fiction",
    },
    "morale": {
        "label": "Morale de la semaine",
        "description": "Une phrase-leçon sur fond papier brun, texte serif crème.",
        "mots_cles": [], "categorie": "fiction",
    },
    "question": {
        "label": "Question du jour",
        "description": "Question bienveillante sur fond brun pour provoquer les commentaires.",
        "mots_cles": [], "categorie": "fiction",
    },
}
PILLAR_KEYS = list(PILLARS.keys())
PILLAR_WEIGHTS = {"parabole": 50, "morale": 25, "question": 25}

# ── Banque de sujets (anti-répétition) ──
SUJETS_PAR_PILIER = {
    "parabole": [
        "Le chemin qui serpente (patience)",
        "La fleur dans la terre craquelée (résilience)",
        "L'arbre qui poussait lentement (croissance douce)",
        "Le reflet dans l'eau (estime de soi)",
        "Le caillou trop lourd à porter (savoir lâcher)",
        "La petite pluie qui a nourri la graine (les petits pas)",
    ],
    "morale": [
        "Les petites pluies font les grandes rivières.",
        "Ce qui est lent n'est pas arrêté.",
        "Un pas minuscule reste un pas.",
        "On ne fleurit pas en regardant le voisin.",
    ],
    "question": [
        "Qu'est-ce qui grandit doucement en toi en ce moment ?",
        "Quand as-tu pris ton dernier moment lent ?",
        "Quelle petite chose t'a rendu fier cette semaine ?",
        "Que laisses-tu derrière toi pour avancer plus léger ?",
    ],
}

STORY_PROMPTS = [
    "une petite difficulté surmontée", "un déclic tout simple",
    "un geste minuscule mais juste", "un moment de doute doux",
    "une petite victoire tranquille",
]

# ── Ton éditorial (chaud, jamais injonctif) ──
TON_EDITORIAL = (
    "Rédige UNIQUEMENT en français. Ton chaleureux, doux, poétique, jamais injonctif. "
    "Maximum 3 phrases. Termine TOUJOURS par une question bienveillante au lecteur. "
    "Pas de chiffre choc, pas de coaching agressif."
)

# ── BLOC STYLE MAÎTRE (collé à chaque prompt image) ──
STYLE_IMAGE_SUFFIX = (
    "Children's picture book illustration in the spirit of 1950s-70s European youth illustration "
    "and the poetic universe of Michaël Dudok de Wit (Ella, Oscar & Hoo): digital watercolor on "
    "heavily textured cold press paper, visible paper grain everywhere including sky, dry brush "
    "texture, wet-on-wet soft transitions, organic brown contour lines slightly thickened at "
    "intersections and broken in places (walnut, espresso — NEVER pure black), childlike minimal "
    "shapes, flat naive perspective, vegetation as suggested painted shapes. "
    "STRICTLY monochrome brown palette only: cream #D4C4A8, sand #C4B08E, caramel #A67C52, "
    "honey #8B6340, chestnut #6B4E35, cinnamon #7A4A30, mocha #5C4033, chocolate #3E2723, "
    "coffee #2E1F16, espresso #1A120B. If any green, blue, red or saturated color tends to appear, "
    "replace it with the closest brown tone. NO pure black, NO pure white. ABSOLUTELY NO TEXT."
): digital watercolor on "
    "heavily textured cold press paper, visible paper grain everywhere including sky, dry brush "
    "texture, wet-on-wet soft transitions, organic brown contour lines slightly thickened at "
    "intersections and broken in places (walnut, espresso — NEVER pure black), childlike minimal "
    "shapes, flat naive perspective, vegetation as suggested painted shapes. "
    "Recurring mascot 'Nviss': a small FLAT watercolor circle with two dot eyes and a simple curved "
    "smile, painted in cream/sand brown with walnut contour — NOT a cloud, NOT a sphere, completely "
    "flat like a paper cutout. "
    "STRICTLY monochrome brown palette only: cream #D4C4A8, sand #C4B08E, caramel #A67C52, "
    "honey #8B6340, chestnut #6B4E35, cinnamon #7A4A30, mocha #5C4033, chocolate #3E2723, "
    "coffee #2E1F16, espresso #1A120B. If any green, blue, red or saturated color tends to appear, "
    "replace it with the closest brown tone. NO pure black, NO pure white. ABSOLUTELY NO TEXT."
)

# ── Palette Pillow (mêmes CLÉS que nyavo → nyavo_media compatible sans modification) ──
COLORS = {
    "violet_profond": (62, 39, 35),    # chocolate
    "bleu_nuit":      (46, 31, 22),    # coffee
    "jaune_moutarde": (166, 124, 82),  # caramel
    "orange_accent":  (122, 74, 48),   # cinnamon
    "blanc":          (212, 196, 168), # cream (jamais #FFF)
    "gris_clair":     (196, 176, 142), # sand
    "gris_sombre":    (92, 64, 51),    # mocha
    "noir":           (26, 18, 11),    # espresso (jamais #000)
}
BOX_BG = {
    "noir_translucide": (62, 39, 35, 150),     # ombre chocolat
    "blanc_opaque":     (212, 196, 168, 225),  # papier crème
}
# Fonds sombres en [0]/[2] pour que le texte crème reste lisible
BACKGROUND_GRADIENT = ["#5C4033", "#6B4E35", "#3E2723", "#A67C52", "#C4B08E", "#1A120B"]

CANVAS_SIZE_TEXTE_SEUL = (1080, 1080)
CANVAS_MARGIN_TEXTE_SEUL = 90

# ── Polices douces (serif titres + sans humaniste) ──
FONT_DIR = "assets/fonts"
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "Nunito-VariableFont_wght.ttf")
FONT_BOLD_PATH = os.path.join(FONT_DIR, "Fraunces-VariableFont.ttf")

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            fallback = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            return ImageFont.truetype(fallback, size)
        except OSError:
            return ImageFont.load_default()

# ── Hiérarchie visuelle ──
ACCROCHE_FONTSIZE = 44
FAIT_CHOC_FONTSIZE = 58
CONSEQUENCE_FONTSIZE = 28
SOURCE_FONTSIZE = 22
DETAIL_FONTSIZE = 36
MARGIN = 70
BOX_BORDER = 24
LINE_SPACING = 14

# ── Dimensions cibles ──
POST_WIDTH, POST_HEIGHT = 1080, 1350
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
MAX_TEXT_WIDTH_POST = POST_WIDTH - 2 * MARGIN
MAX_TEXT_WIDTH_STORY = STORY_WIDTH - 2 * MARGIN

# ── Assets de la marque vis ──
EXPRESSIONS_DIR = "assets/expressions_vis"
PROFILE_IMAGE_PATH = "assets/profile_vis.png"   # = Nviss, le cercle plat
EMOJIS_DIR = "assets/emojis"

# ── Wrap texte mesuré au pixel (Pillow) ──
def wrap_text_pillow(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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
