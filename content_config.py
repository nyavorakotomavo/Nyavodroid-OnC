# -*- coding: utf-8 -*-
"""Configuration Nyavo Channel v2 — intègre les specs de performance
(horaires, formats, structure de légende) issues de l'étude Perplexity.
"""

# ---------------------------------------------------------------------------
# IDENTITÉ VISUELLE
# ---------------------------------------------------------------------------
PALETTE = {
    "bg": "0x0D0D0D",
    "accent_cyan": "0x00E5FF",
    "accent_lime": "0x39FF14",
    "gray": "0x2B2B2B",
}

STYLE_IMAGE_SUFFIX = (
    "dark cyberpunk aesthetic, minimalist, black background, "
    "neon cyan and lime green accents, high contrast, saturated colors, "
    "single strong central visual element, tension visuelle, "
    "no face, partial hand or silhouette allowed, no text, no watermark"
)

# Specs image : format vertical 4:5, surperforme le carré (données Perplexity)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1350

# Specs vidéo : format 9:16 plein écran, 7-10s = zone de rétention max
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_DURATION_SECONDS = 9
VIDEO_FPS = 25

# ---------------------------------------------------------------------------
# RÈGLES DE LÉGENDE (structure hook / contexte / question / hashtags)
# ---------------------------------------------------------------------------
MAX_HOOK_CHARS = 80          # posts <80 caractères = engagement le plus haut
MAX_OVERLAY_WORDS = 8        # règle image : 1 seul message court sur le visuel
HASHTAG_COUNT = 3            # 2-3 hashtags max sur Facebook (pas plus)

HOOK_FORMULAS = [
    "statistique surprenante (ex: '97% des devs ignorent ça')",
    "teasing de révélation (ex: 'Ce que X ne montre JAMAIS')",
    "contradiction d'une croyance répandue",
]

# ---------------------------------------------------------------------------
# 4 PILIERS DE CONTENU
# ---------------------------------------------------------------------------
PILLARS = {
    "deep_code": {
        "label": "Deep Code & Secrets du Web",
        "hook_style": "révélation, 'voici ce que X ne veut pas que tu saches'",
        "topics": [
            "comment l'algorithme de recommandation de TikTok choisit vraiment ce que tu vois",
            "la technique cachée derrière l'auto-complétion de Google",
            "pourquoi certains sites chargent plus vite que d'autres (le secret du lazy loading)",
            "comment fonctionne le chiffrement de bout en bout de WhatsApp",
            "le tracking invisible que font 90% des sites sans te le dire",
            "comment une app peut deviner ta localisation sans GPS",
            "la logique cachée derrière le feed infini d'Instagram",
            "comment les mots de passe sont vraiment stockés (hash vs clair)",
            "le fonctionnement réel d'un VPN, au-delà du marketing",
            "comment un site sait que t'as déjà visité même en navigation privée",
        ],
    },
    "dark_science": {
        "label": "Dark Science & Physique de Pointe",
        "hook_style": "fascination, 'ça va te faire douter de la réalité'",
        "topics": [
            "pourquoi le vide spatial n'est jamais totalement vide",
            "la théorie qui dit que le temps ralentit près d'un trou noir",
            "comment l'ordinateur quantique casse la logique classique",
            "pourquoi la lumière n'a pas de masse mais peut être 'piégée'",
            "l'expérience qui prouve qu'observer change la réalité (physique quantique)",
            "pourquoi l'univers pourrait être une simulation selon certains physiciens",
            "comment les matériaux intelligents changent de forme tout seuls",
            "la théorie des cordes expliquée en 30 secondes",
            "pourquoi le zéro absolu n'existe pas vraiment dans notre univers",
            "comment un satellite doit corriger sa vitesse à cause d'Einstein",
        ],
    },
    "fast_tech": {
        "label": "Fast Tech & Nouveautés IA",
        "hook_style": "urgence/exclusivité, 'avant que tout le monde le sache'",
        "topics": [
            "un outil IA gratuit que personne n'utilise encore",
            "la fonctionnalité cachée de ton smartphone que tu n'as jamais activée",
            "comment tester une IA avant sa sortie officielle",
            "l'astuce pour utiliser une IA payante gratuitement (usage légal)",
            "le gadget tech qui va changer ta façon de coder",
            "comment une IA peut générer une app entière en quelques minutes",
            "la tendance tech que les devs sous-estiment en ce moment",
            "un raccourci clavier ou terminal qui fait gagner un temps fou",
        ],
    },
    "devlog": {
        "label": "DevLog & Projets (le pont vers tes ventes)",
        "hook_style": "authenticité, coulisses, 'voici où j'en suis vraiment'",
        "topics": [
            "le bug le plus tordu que j'ai résolu cette semaine sur mon app",
            "pourquoi j'ai choisi Kotlin/Compose plutôt qu'un autre framework",
            "une fonctionnalité inédite que je viens d'ajouter à mon app",
            "comment je développe une app Android entièrement depuis mon téléphone",
            "le before/after d'une interface que j'ai refaite cette semaine",
            "ce que j'ai appris en cassant volontairement mon build",
            "un aperçu exclusif d'une feature pas encore sortie",
        ],
    },
}

PILLAR_KEYS = list(PILLARS.keys())

PILLAR_WEIGHTS = {
    "deep_code": 3,
    "dark_science": 2,
    "fast_tech": 3,
    "devlog": 2,
}

HASHTAGS = {
    "deep_code": ["#DeepCode", "#CodeSecrets", "#TechSecrets"],
    "dark_science": ["#DarkScience", "#Physique", "#ScienceInsolite"],
    "fast_tech": ["#FastTech", "#IA", "#TechSecrets"],
    "devlog": ["#DevLog", "#BuildInPublic", "#TechSecrets"],
}

CTA_QUESTIONS = [
    "Tu savais ou pas ? Dis-le en commentaire.",
    "Team surpris ou team je savais déjà ? Commente.",
    "Partage à un dev qui doit voir ça.",
    "Ça change quoi pour toi ? Réagis en commentaire.",
]

# ---------------------------------------------------------------------------
# RATIO FORMAT (feed uniquement — les stories sont gérées séparément)
# ---------------------------------------------------------------------------
FORMAT_WEIGHTS = {"photo": 55, "video": 45}

HISTORY_WINDOW = 12

# ---------------------------------------------------------------------------
# CONTENU STORIES (courts, factuels, sans légende longue)
# ---------------------------------------------------------------------------
STORY_PROMPTS = [
    "un chiffre choc et vérifiable sur l'IA ou la tech, en une phrase",
    "une astuce dev en une phrase actionnable",
    "une question ouverte qui lance le débat sur une tendance tech du moment",
    "un fait scientifique surprenant en une phrase",
    "un teaser d'une phrase sur ce que tu développes en ce moment",
]
