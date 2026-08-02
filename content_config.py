#!/usr/bin/env python3
"""
Nyavodroid — Configuration éditoriale.
Alignée sur la ligne éditoriale officielle :
  Axe 1 : Secrets du code & mécanismes cachés du web
  Axe 2 : Découvertes scientifiques & technologies émergentes
  Axe 3 : Actualité IA, logiciels, gadgets & tendances tech
  Axe 4 : Coulisses des projets Nyavodroid (dev, défis, solutions)

Identité visuelle : violet/magenta profond, formes 3D, glow magenta,
  fond noir violet (#0A0514 → #120A26), accents orange (#F4511E),
  cube 3D suggéré. Plus de cyan/rouge néon.
"""

# ──────────────────────────────────────────────
# Les 4 axes éditoriaux officiels
# ──────────────────────────────────────────────
PILLARS = { ... }  # inchangé

PILLAR_KEYS = list(PILLARS.keys())
PILLAR_WEIGHTS = { ... }

SUJETS_PAR_PILIER = { ... }  # inchangé

STORY_PROMPTS = [ ... ]      # inchangé

TON_EDITORIAL = (
    "Vulgarisation captivante et accessible. Ton dynamique, immersif, "
    "légèrement mystérieux. Comme si tu révélais un secret au lecteur. "
    "Phrases courtes et percutantes. Pas de jargon inutile, mais "
    "toujours un terme technique précis pour crédibiliser. "
    "Tutoiement implicite. Pas de formules creuses."
)

# ──────────────────────────────────────────────
# NOUVELLE IDENTITÉ VISUELLE (Problème 5)
# ──────────────────────────────────────────────
STYLE_IMAGE_SUFFIX = (
    "deep violet and magenta aesthetic, dark violet-black background (#0A0514), "
    "floating 3D cubes with magenta glow (#EA4FD9), soft orange accents (#F4511E), "
    "abstract digital art, code particles floating in space, "
    "no cyan, no red neon, no circuit boards, no holograms. "
    "Composition intentional and credible, not artificially smooth. "
    "Cinematic lighting, high quality, 4k, vertical composition"
)

# Tailles de texte pour la hiérarchie 3 niveaux (Problème 1)
HOOK_FONTSIZE = 78
EXPL_FONTSIZE = 42
DETAIL_FONTSIZE = 26
MARGIN = 54  # 5% de 1080px