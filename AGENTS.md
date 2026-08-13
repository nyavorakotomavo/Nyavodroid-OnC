# Nyavodroid — Agent Quickstart Guide

Social-media publishing bots (Facebook) for two brands: **nyavo** (tech news) and **vis** (motivational). Single Python package, no build step.

## Commands

- `pip install -r requirements.txt` — deps: requests, Pillow, pyyaml (CI also installs `ffmpeg` + `fonts-dejavu-core` via apt)
- `python post_content.py` — nyavo multi-format (texte_seul / image_texte / reel)
- `python post_vis.py` — vis brand (parabole / morale / question / story); **requires `BRAND=vis` or it exits**
- `python post_story.py` — Facebook story with LLM self fact-check (nyavo)
- `python video_pipeline/01_script.py` → `02_voice.py` → `03_analyze.py` → `04_visuals.py` → `05_animate.py` → `06_audio.py` → `07_editor.py` → `08_qc.py` → `publish_video.py` — run in order; they share working files in cwd
- `python download_fonts.py` — installs Inter + (if `BRAND=vis`) Nunito; run once
- `python charger_strategie.py` — print the resolved `STRATEGIE_JSON` strategy (defaults if unset)

## Environment / Secrets

Required per script (missing key → `KeyError` → clean exit):
- `post_content.py` / `post_vis.py`: `GEMINI_API_KEY_CONTENT`, `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
- `post_story.py`: `GEMINI_API_KEY_STORY` (NOT `_CONTENT`), `FB_PAGE_ID`, `FB_PAGE_ACCESS_TOKEN`
- nyavo `image_texte` fact-check needs `TAVILY_API_KEY` + `MISTRAL_API_KEY` (see gotcha below)

Optional provider keys (absent = provider silently skipped): `MISTRAL_API_KEY`, `TOGETHER_API_KEY`, `HF_TOKEN`, `REPLICATE_API_TOKEN`, `FAL_API_KEY`, `FREEAI_API_KEY`, `PEXELS_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`/`CLOUDFLARE_API_TOKEN` (+ `_2`/`_3` for round-robin).

Control env vars:
- `BRAND` — `nyavo` (default) or `vis`; selects `themes/<brand>.yaml`
- `STRATEGIE_JSON` — NAnaly payload (JSON) driving format/pillar/sujets selection via `charger_strategie()`
- `FORCE_FORMAT` — `texte_seul`/`image_texte`/`reel` to override post_content's strategy/hourly pick
- `VIS_FORCE_PILIER`, `VIS_EXCLUDE` (comma list) — vis pillar control; `VIS_DRY_RUN=1` skips actual FB publish

## Key Conventions

- **Provider cascade (real order, from `nyavo_media.py`):** text = Mistral → Together → Gemini (multi-model) → Hugging Face. image (nyavo `image_avec_fallback`) = Gemini → Cloudflare → HF → Together → Fal.ai → Pollinations. vis images use Cloudflare → Pollinations only. **A 429 forces immediate switch to the next provider.** (The old "Gemini cascade" is wrong — Mistral/Together are tried first.)
- **Fact-check fail-safe:** nyavo `image_texte` calls `fact_checker.verify_topic()` (Tavily web search + Mistral extraction). If `TAVILY_API_KEY` is missing it finds 0 sources and the script **`sys.exit(0)`s with no post** — looks like success but publishes nothing. `post_story.py` does NOT use fact_checker; it self-verifies via the prompt.
- **Two-brand flows:** nyavo = texte_seul / image_texte / reel (fact-check on image_texte). vis = parabole / morale / question / story, no fact-checker, anti-repeat history. `content_config.py` prefers `themes/*.yaml`; `content_config_nyavo.py`/`content_config_vis.py` are legacy and no longer routed.
- **`published_history.json` is auto git-committed/pushed** by the publish scripts. Running them mutates the git repo. vis excludes subjects published in the last ~60 days; content flow prunes at 90 days.
- **Text/number formatting is enforced:** no `**`/`*` markdown in final output (`clean_text()` strips them); powers written `10^30` (no spaces), units glued (`30kg`). Prompts demand this — preserve it in edits.
- **Fonts:** `assets/fonts/Inter-Regular.ttf` + `Inter-Bold.ttf` required (`get_font` falls back to DejaVu if missing). `download_fonts.py` installs Inter + (if `BRAND=vis`) Nunito; the old `download_fonts_vis.py` stub has been removed.
- **ffmpeg** required for reel assembly, ratio cropping, and watermarking.
