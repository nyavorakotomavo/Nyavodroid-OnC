#!/usr/bin/env python3
"""
Nyavodroid — Configuration éditoriale.
Alignée sur la ligne éditoriale officielle :
  Axe 1 : Secrets du code & mécanismes cachés du web
  Axe 2 : Découvertes scientifiques & technologies émergentes
  Axe 3 : Actualité IA, logiciels, gadgets & tendances tech
  Axe 4 : Coulisses des projets Nyavodroid (dev, défis, solutions)

Identité visuelle : Infographie Narrative d'Expert.
  Palette premium : violet profond (#2D1B4E), jaune moutarde (#E5B83B),
  bleu nuit (#1A2A47), accents orange (#F4511E).
  Composition aérée, badge de sourcing, CTA visuel.
"""

# ──────────────────────────────────────────────
# Les 4 axes éditoriaux officiels
# ──────────────────────────────────────────────
PILLARS = {
    "secrets_code": {
        "label": "Secrets du Code & Mécanismes Cachés",
        "description": (
            "Algorithmes, reverse engineering, astuces méconnues du web, "
            "fonctionnement des grandes plateformes, protocoles, "
            "architecture logicielle, coulisses techniques."
        ),
        "mots_cles": [
            "algorithme", "reverse engineering", "protocole", "API",
            "serveur", "navigateur", "open source", "framework",
            "base de données", "compilateur", "Linux", "Python",
        ],
        "categorie": "tech",  # pour décider IA vs Pexels
    },
    "science_tech": {
        "label": "Découvertes Scientifiques & Technologies Émergentes",
        "description": (
            "Physique moderne, laboratoires de recherche, innovations "
            "de rupture, technologies quantiques, biotechnologies, "
            "énergie, espace, matériaux du futur."
        ),
        "mots_cles": [
            "quantique", "physique", "laboratoire", "innovation",
            "énergie", "espace", "biotechnologie", "matériau",
            "recherche", "découverte", "futur", "science",
        ],
        "categorie": "science",
    },
    "actu_ia_tech": {
        "label": "Actualité IA, Logiciels & Tendances Tech",
        "description": (
            "Intelligences artificielles, applications, logiciels, "
            "gadgets, tendances technologiques, outils numériques, "
            "mises à jour, sorties, comparatifs."
        ),
        "mots_cles": [
            "IA", "intelligence artificielle", "LLM", "application",
            "logiciel", "gadget", "startup", "outil", "mise à jour",
            "tendance", "tech", "numérique",
        ],
        "categorie": "tech",
    },
    "coulisses_nyavo": {
        "label": "Coulisses des Projets Nyavodroid",
        "description": (
            "Développement des applications créées par Nyavodroid, "
            "défis techniques rencontrés, solutions mises en œuvre, "
            "évolution des projets, architecture, choix techniques, "
            "lancement, behind the scenes."
        ),
        "mots_cles": [
            "Nyavodroid", "développement", "projet", "application",
            "défi technique", "solution", "architecture", "lancement",
            "backend", "frontend", "déploiement", "code",
        ],
        "categorie": "tech",
    },
}

PILLAR_KEYS = list(PILLARS.keys())

# Poids de sélection (somme libre)
PILLAR_WEIGHTS = {
    "secrets_code": 30,
    "science_tech": 25,
    "actu_ia_tech": 30,
    "coulisses_nyavo": 15,
}

# ──────────────────────────────────────────────
# Banque de sujets par axe (anti-répétition)
# ──────────────────────────────────────────────
SUJETS_PAR_PILIER = {
    "secrets_code": [
        "Comment fonctionne réellement le DNS",
        "Les secrets du protocole HTTP/3",
        "Pourquoi Python est lent mais domine le monde",
        "Le fonctionnement caché des WebSockets",
        "Comment les navigateurs rendent une page en 100ms",
        "Les coulisses du système Git",
        "Comment les CDN accélèrent Internet",
        "SQL vs NoSQL : le vrai duel",
        "Le fonctionnement des conteneurs Docker",
        "Les secrets du chiffrement HTTPS",
        "Comment fonctionne un compilateur",
        "Les astuces cachées de Linux",
        "Le reverse engineering expliqué simplement",
        "Comment les API REST communiquent",
        "Les mécanismes du cache navigateur",
    ],
    "science_tech": [
        "L'ordinateur quantique expliqué simplement",
        "La fusion nucléaire : où en est-on ?",
        "Les matériaux qui changeront le futur",
        "La biotechnologie et l'ADN synthétique",
        "Les télescopes de nouvelle génération",
        "L'énergie solaire du futur",
        "Les interfaces cerveau-machine",
        "La physique des trous noirs",
        "Les robots mous de la recherche",
        "L'impression 3D d'organes",
        "Les nanotechnologies médicales",
        "La supraconductivité à température ambiante",
        "Les satellites de nouvelle génération",
        "L'hydrogène vert comme énergie du futur",
        "Les cristaux temporels en physique",
    ],
    "actu_ia_tech": [
        "Les dernières avancées des LLM",
        "L'IA générative dans le cinéma",
        "Les nouveaux outils de coding assisté par IA",
        "Les lunettes AR de nouvelle génération",
        "L'IA dans la médecine diagnostique",
        "Les agents IA autonomes",
        "Les modèles open source vs propriétaires",
        "L'IA et la cybersécurité",
        "Les gadgets tech les plus innovants",
        "Les tendances dev à suivre",
        "L'IA dans la musique et l'art",
        "Les nouveaux frameworks JavaScript",
        "L'edge computing et l'IA locale",
        "Les robots humanoïdes de 2026",
        "L'IA et la traduction en temps réel",
    ],
    "coulisses_nyavo": [
        "Comment j'ai automatisé mes publications",
        "Le défi du déploiement sur GitHub Actions",
        "Pourquoi j'ai choisi Python pour mes outils",
        "Les bugs les plus difficiles à résoudre",
        "L'architecture de mon bot de publication",
        "Comment je gère les API externes",
        "Le passage de l'idée au prototype",
        "Les erreurs de débutant à éviter",
        "Comment j'optimise mes scripts",
        "Le choix des bases de données",
        "La gestion des erreurs en production",
        "Comment je teste mes applications",
        "Le déploiement sur le cloud",
        "La sécurité de mes applications",
        "L'évolution de mon stack technique",
    ],
}

# ──────────────────────────────────────────────
# Styles de prompts (formats de contenu)
# ──────────────────────────────────────────────
STORY_PROMPTS = [
    "un fait surprenant et méconnu",
    "une question qui pique la curiosité",
    "un chiffre impressionnant",
    "une anecdote technique méconnue",
    "un mythe à débunker",
    "une prédiction audacieuse mais crédible",
    "un conseil pratique de développeur",
    "une comparaison inattendue",
    "un secret bien gardé",
    "une révélation contre-intuitive",
]

# ──────────────────────────────────────────────
# Ton éditorial
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# Ton éditorial (français impératif, formule Cultination)
# ──────────────────────────────────────────────
TON_EDITORIAL = (
    "Rédige UNIQUEMENT en français. "
    "Sois extrêmement concis : maximum 3 phrases. "
    "Structure : [contexte général] → [FAIT CHOC avec un chiffre précis] → [conséquence concrète]. "
    "Jamais d’abstraction, jamais de comparaison vague. "
    "Le fait choc doit être surprenant et vérifiable."
)


# ──────────────────────────────────────────────
# Identité visuelle — NOUVEAU STYLE "INFOGRAPHIE NARRATIVE D'EXPERT"
# ──────────────────────────────────────────────
STYLE_IMAGE_SUFFIX = (
    "premium editorial infographic style, expert narrative design, "
    "deep violet (#2D1B4E) and midnight blue (#1A2A47) background, "
    "mustard yellow (#E5B83B) and soft orange (#F4511E) accents, "
    "clean geometric composition, elegant data visualization elements, "
    "subtle grid patterns, thin golden lines, airy layout with ample negative space, "
    "professional typography-ready zones, no clutter, no neon, no circuit boards, "
    "high-end magazine quality, 4k, vertical composition"
)

# ──────────────────────────────────────────────
# Palette pour les fonds générés (posts texte seul)
# ──────────────────────────────────────────────
BACKGROUND_GRADIENT = [
    "#2D1B4E",  # violet profond (prioritaire)
    "#3D2B5E",  # violet moyen
    "#1A2A47",  # bleu nuit
    "#E5B83B",  # jaune moutarde
    "#F4511E",  # orange
    "#8B1A4A",  # rouge foncé
]

CANVAS_SIZE_TEXTE_SEUL = (1080, 1080)  # format carré pour les posts texte

# ──────────────────────────────────────────────
# Hiérarchie de texte pour les visuels
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# Tailles de police pour la nouvelle hiérarchie visuelle
# ──────────────────────────────────────────────
ACCROCHE_FONTSIZE = 44          # phrase de contexte en haut
FAIT_CHOC_FONTSIZE = 58         # chiffre / fait marquant (dans l'encadré)
CONSEQUENCE_FONTSIZE = 28       # conséquence en dessous
SOURCE_FONTSIZE = 22            # source en bas
MARGIN = 54
# ──────────────────────────────────────────────
# Dossiers des assets
# ──────────────────────────────────────────────
EXPRESSIONS_DIR = "assets/expressions"
PROFILE_IMAGE_PATH = "assets/profile.png"
EMOJIS_DIR = "assets/emojis"