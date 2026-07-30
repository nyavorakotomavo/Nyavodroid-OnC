#!/usr/bin/env python3
"""
Nyavo Channel — Configuration éditoriale.
Alignée sur la ligne éditoriale officielle :
  Axe 1 : Secrets du code & mécanismes cachés du web
  Axe 2 : Découvertes scientifiques & technologies émergentes
  Axe 3 : Actualité IA, logiciels, gadgets & tendances tech
  Axe 4 : Coulisses des projets Nyavo (dev, défis, solutions)

Identité visuelle : cyber-minimaliste, sombre, futuriste,
  noir/anthracite, accents cyan/vert néon, ambiance synthwave.
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
    },
    "coulisses_nyavo": {
        "label": "Coulisses des Projets Nyavo",
        "description": (
            "Développement des applications créées par Nyavo, "
            "défis techniques rencontrés, solutions mises en œuvre, "
            "évolution des projets, architecture, choix techniques, "
            "lancement, behind the scenes."
        ),
        "mots_cles": [
            "Nyavo", "développement", "projet", "application",
            "défi technique", "solution", "architecture", "lancement",
            "backend", "frontend", "déploiement", "code",
        ],
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
TON_EDITORIAL = (
    "Vulgarisation captivante et accessible. Ton dynamique, immersif, "
    "légèrement mystérieux. Comme si tu révélais un secret au lecteur. "
    "Phrases courtes et percutantes. Pas de jargon inutile, mais "
    "toujours un terme technique précis pour crédibiliser. "
    "Tutoiement implicite. Pas de formules creuses."
)

# ──────────────────────────────────────────────
# Identité visuelle (style image)
# ──────────────────────────────────────────────
STYLE_IMAGE_SUFFIX = (
    "cyber-minimalist, dark futuristic aesthetic, black and anthracite "
    "background, cyan and neon green accents, glowing digital interfaces, "
    "synthwave atmosphere, sleek modern design, code fragments floating, "
    "holographic elements, high contrast, cinematic lighting, 4k quality, "
    "vertical composition"
)