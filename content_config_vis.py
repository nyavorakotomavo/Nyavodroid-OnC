#!/usr/bin/env python3
"""
Nyavodroid — Configuration éditoriale VIS (définitif).
Univers : album jeunesse aquarelle brune (esprit Ella, Oscar & Hoo).
4 piliers : parabole / morale / question / story. Sans mascotte, sans fact-check.
"""
import os
from PIL import ImageFont

PILLARS = {
    "parabole": {
        "label": "Parabole illustrée",
        "description": "Histoire morale courte en 6 slides, protagoniste abstrait ou environnement.",
        "mots_cles": ["patience", "confiance", "gratitude", "résilience", "acceptation"],
        "categorie": "fiction",
    },
    "morale": {
        "label": "Morale de la semaine",
        "description": "Une phrase-leçon sur fond papier brun, texte crème.",
        "mots_cles": [], "categorie": "fiction",
    },
    "question": {
        "label": "Question du jour",
        "description": "Question bienveillante sur fond brun pour provoquer les commentaires.",
        "mots_cles": [], "categorie": "fiction",
    },
    "story": {
        "label": "Story éphémère",
        "description": "Morale ou question en format 9:16 pour la story Facebook.",
        "mots_cles": [], "categorie": "fiction",
    },
}
PILLAR_KEYS = list(PILLARS.keys())
PILLAR_WEIGHTS = {"parabole": 35, "morale": 20, "question": 20, "story": 25}

SUJETS_PAR_PILIER = {
    "parabole": [
        "Le corbeau est le seul oiseau qui ose attaquer un aigle. Mais l'aigle ne riposte jamais.",
        "On te dit que tu parles trop ? Lance un podcast.",
        "Les chauves-souris propagent des maladies, dit-on. Pendant ce temps, les humains polluent les rivières.",
        "Le renard n'a rien à faire en ville, dit-on. Pendant ce temps, les humains rasent les forêts.",
        "Un aigle peut vivre 70 ans, mais à 40 ans il doit choisir : mourir ou se transformer.",
        "Le bambou pousse 3 cm les 4 premières années. La 5e année : 30 cm par jour.",
        "Les fourmis portent 50 fois leur poids. Sans se plaindre. Sans audience.",
        "L'eau chaude ne sent pas qu'elle bout. La grenouille non plus.",
        "Un diamant n'est qu'un morceau de charbon qui a supporté la pression.",
        "Le phare ne court pas après les bateaux. Il reste debout et brille.",
        "Les loups ne votent pas pour décider du chef. Ils suivent le plus fort naturellement.",
        "Une flèche ne recule que pour être tirée plus loin.",
        "Le silence d'un lion fait plus peur que le cri d'un chien.",
        "Les étoiles ont besoin de l'obscurité totale pour briller.",
        "Un navire est en sécurité au port. Mais ce n'est pas pour ça qu'il a été construit.",
        "La pression transforme le charbon en diamant. Le confort ne transforme rien.",
        "Les grands arbres ont les racines les plus profondes dans la terre sombre.",
        "Un crayon doit être taillé pour écrire à nouveau. La douleur fait grandir.",
        "Les rivières creusent la roche par persévérance, pas par force.",
        "Le feu teste l'or. L'adversité teste l'homme courageux.",
    ],
    "morale": [
        "Ne riposte pas à chaque attaque. Garde ton altitude.",
        "Ce qu'on te reproche est souvent ton super-pouvoir.",
        "La pression d'aujourd'hui est le diamant de demain.",
        "Reste debout et brille. Les bons finiront par te voir.",
        "Reculer, c'est parfois prendre de l'élan.",
        "La persévérance bat toujours la force brute.",
    ],
    "question": [
        "Quelle pression es-tu en train de supporter pour devenir un diamant ?",
        "À quoi refuses-tu de riposter aujourd'hui pour garder ton altitude ?",
        "Quel est ton super-pouvoir déguisé en défaut aux yeux des autres ?",
        "Es-tu au port par sécurité, ou en mer par mission ?",
        "Que dois-tu laisser brûler pour révéler ton or ?",
        "Où prends-tu de l'élan en reculant aujourd'hui ?",
    ],
    "story": [
        "Le corbeau attaque l'aigle. L'aigle ne riposte jamais. Et toi, tu réponds à quoi aujourd'hui ?",
        "Un diamant n'est qu'un charbon qui a tenu sous pression. Tu tiens bon ?",
        "Le phare ne court après personne. Il brille. Que fais-tu briller ?",
        "Une flèche recule pour aller plus loin. Où prends-tu ton élan ?",
        "Les étoiles ont besoin du noir total. Ton obscurité prépare quoi ?",
    ],
}

STORY_PROMPTS = [
    "une petite difficulté surmontée", "un déclic tout simple",
    "un geste minuscule mais juste", "un moment de doute doux",
    "une petite victoire tranquille",
]

TON_EDITORIAL = (
    "Rédige UNIQUEMENT en français. Ton chaleureux, doux, poétique, jamais injonctif. "
    "Maximum 3 phrases. Termine TOUJOURS par une question bienveillante au lecteur. "
    "Pas de chiffre choc, pas de coaching agressif."
)

STYLE_IMAGE_SUFFIX = (
    "Children's picture book illustration in the spirit of 1950s-70s European youth "
    "illustration and the poetic universe of Michaël Dudok de Wit (Ella, Oscar & Hoo): "
    "digital watercolor on heavily textured cold press paper, visible paper grain "
    "everywhere including sky, dry brush texture, wet-on-wet soft transitions, organic "
    "brown contour lines slightly thickened at intersections and broken in places "
    "(walnut, espresso — NEVER pure black), childlike minimal shapes, flat naive "
    "perspective, vegetation as suggested painted shapes. STRICTLY monochrome brown "
    "palette only: cream #D4C4A8, sand #C4B08E, caramel #A67C52, honey #8B6340, "
    "chestnut #6B4E35, cinnamon #7A4A30, mocha #5C4033, chocolate #3E2723, coffee "
    "#2E1F16, espresso #1A120B. If any green, blue, red or saturated color tends to "
    "appear, replace it with the closest brown tone. NO pure black, NO pure white. "
    "ABSOLUTELY NO TEXT."
)

COLORS = {
    "violet_profond": (62, 39, 35),
    "bleu_nuit":      (46, 31, 22),
    "jaune_moutarde": (166, 124, 82),
    "orange_accent":  (122, 74, 48),
    "blanc":          (212, 196, 168),
    "gris_clair":     (196, 176, 142),
    "gris_sombre":    (92, 64, 51),
    "noir":           (26, 18, 11),
}
BOX_BG = {
    "noir_translucide": (62, 39, 35, 150),
    "blanc_opaque":     (212, 196, 168, 225),
}
BACKGROUND_GRADIENT = ["#5C4033", "#6B4E35", "#3E2723", "#A67C52", "#C4B08E", "#1A120B"]

CANVAS_SIZE_TEXTE_SEUL = (1080, 1080)
CANVAS_MARGIN_TEXTE_SEUL = 90

FONT_DIR = "assets/fonts"
FONT_REGULAR_PATH = os.path.join(FONT_DIR, "Nunito-VariableFont_wght.ttf")
FONT_BOLD_PATH    = os.path.join(FONT_DIR, "Inter-Bold.ttf")

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            fb = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            return ImageFont.truetype(fb, size)
        except OSError:
            return ImageFont.load_default()

ACCROCHE_FONTSIZE = 44
FAIT_CHOC_FONTSIZE = 58
CONSEQUENCE_FONTSIZE = 28
SOURCE_FONTSIZE = 22
DETAIL_FONTSIZE = 36
MARGIN = 70
BOX_BORDER = 24
LINE_SPACING = 14

POST_WIDTH, POST_HEIGHT = 1080, 1350
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
MAX_TEXT_WIDTH_POST = POST_WIDTH - 2 * MARGIN
MAX_TEXT_WIDTH_STORY = STORY_WIDTH - 2 * MARGIN

EXPRESSIONS_DIR = "assets/expressions"
PROFILE_IMAGE_PATH = "assets/profile_vis.png"
EMOJIS_DIR = "assets/emojis"

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
