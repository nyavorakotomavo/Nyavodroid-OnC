# Nyavodroid — Agent Quickstart Guide

## Commands

- `pip install -r requirements.txt` — install deps (Pillow, requests, pyyaml)
- `python post_content.py` — publish multi-format (texte_seul, image_texte, reel) — brand "nyavo"
- `python post_vis.py` — publish VIS brand (parabole, morale, question, story) — requires `BRAND=vis`
- `python post_story.py` — publish story format with auto-fact-check
- `python video_pipeline/01_script.py` → `07_editor.py` → `08_qc.py` — 7-phase video pipeline (run in order)
- `python download_fonts.py` — download Inter + Nunito (fonts unified, run once per brand)
- `python charger_strategie.py` — test strategy loading from `STRATEGIE_JSON` env var

## Environment

- `BRAND` env var: `"nyavo"` or `"vis"` — determines theme YAML loaded (`themes/nyavo.yaml` or `themes/vis.yaml`)
- Critical secrets: `GEMINI_API_KEY_CONTENT`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
- `STRATEGIE_JSON` env var drives format/pillar selection via `charger_strategie()` (used by `post_content.py` and `reception-strategie.yml`)
- `VIS_FORCE_PILIER`, `VIS_EXCLUDE` — VIS brand control variables

## Key Conventions

- **Fact-check is mandatory** for `image_texte` format: `publier_image_texte()` calls `fact_checker.verify_topic()` and exits if invalid (zero-tolerance fake-news fail-safe)
- **Two brands, separate flows**:
  - `post_content.py` — nyavo: texte_seul / image_texte / reel
  - `post_vis.py` — vis: parabole / morale / question / story (no fact_checker; uses anti-repeat history)
  - `post_story.py` — story with LLM auto-verification of facts, numbers, and image prompts
- **published_history.json** — 30-day (vis) / 90-day (content) anti-repetition tracking; scripts auto-commit/push git changes
- **Fonts** — `assets/fonts/Inter-Regular.ttf` and `Inter-Bold.ttf` must exist; `download_fonts.py` downloads both Inter fonts; VIS also needs `Nunito-VariableFont_wght.ttf` (downloaded automatically if BRAND=vis); `download_fonts_vis.py` est désormais obsolète (contenu remplacé par un message de dépréciation)
- **ffmpeg** — required for video assembly, watermarking, and ratio cropping; workflows install it via `apt-get`
- **CLOUDFLARE_CREDS** — optional multi-account round-robin for image generation; if set, preferred over Gemini for images
- **Number format** — powers written `10^30` (no spaces), units glued (`30kg`, not `30 kg`); enforced in prompts
- **Text format** — no `**` or `*` markdown in final output; `clean_text()` strips them; `_auto_highlight()` adds `**` around numbers if missing
- **Gemini cascade** — text: `gemini-flash-latest → gemini-pro-latest → gemini-2.5-pro → gemini-2.5-flash`; image: `gemini-2.5-flash-image → gemini-2.0-flash-exp → gemini-1.5-flash`
- **429 quotas trigger immediate cascade** to next provider in all nyavo image/text pipelines
- **Legacy configs** — `content_config_nyavo.py` and `content_config_vis.py` sont toujours à la racine du dépôt (déplacement vers `legacy/` prévu mais non encore exécuté en raison de contraintes de environnement). `content_config.py` privilégie désormais les themes YAML. Conservés en secours mais plus activement utilisés.