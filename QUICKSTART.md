# OnC — Quick Start

> Complete setup guide for a fresh OnC installation.

---

# 📖 Table of Contents

1. [Before You Start](#1-before-you-start)
2. [Clone the Repository](#2-clone-the-repository)
3. [Python Environment](#3-python-environment)
4. [Install Dependencies](#4-install-dependencies)
5. [Install FFmpeg](#5-install-ffmpeg)
6. [Install ImageMagick](#6-install-imagemagick)
7. [Configure Environment Variables](#7-configure-environment-variables)
8. [Configure API Keys](#8-configure-api-keys)
9. [Configure Social Media IDs](#9-configure-social-media-ids)
10. [Configure Search and Verification APIs](#10-configure-search-and-verification-apis)
11. [Configure Image Generation APIs](#11-configure-image-generation-apis)
12. [Configure AI Text Providers](#12-configure-ai-text-providers)
13. [Configure Themes](#13-configure-themes)
14. [Configure Images and Assets](#14-configure-images-and-assets)
15. [Configure GitHub Actions](#15-configure-github-actions)
16. [Configure GitHub Secrets](#16-configure-github-secrets)
17. [Run a Local Test](#17-run-a-local-test)
18. [Run a Dry Run](#18-run-a-dry-run)
19. [Test Content Generation](#19-test-content-generation)
20. [Test Image Generation](#20-test-image-generation)
21. [Test Video Pipeline](#21-test-video-pipeline)
22. [Test Publishing](#22-test-publishing)
23. [Enable Automatic Workflows](#23-enable-automatic-workflows)
24. [Troubleshooting](#24-troubleshooting)
25. [Pre-Production Checklist](#25-pre-production-checklist)

---

# 1. Before You Start

Before installing OnC, make sure you have:

- Python 3.11 or newer
- Git
- FFmpeg
- FFprobe
- ImageMagick
- An internet connection
- A GitHub account if GitHub Actions will be used
- The required API accounts
- The required API keys/tokens
- The required social-media account/page
- The required social-media IDs
- The OnC repository URL

You do **not** receive the seller's API keys or social-media accounts.

Every buyer must configure their own external services.

---

# 2. Clone the Repository

Clone your licensed copy of OnC:

```bash
git clone <YOUR_ONC_REPOSITORY_URL>
cd Nyavodroid-OnC
```

If your repository uses another directory name, enter that directory instead.

Verify that the repository is correct:

```bash
git status
```

You should see the OnC Git repository information.

---

# 3. Python Environment

Using a virtual environment is strongly recommended.

## Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

If `python` is not recognized, try:

```bash
py -m venv .venv
.venv\Scripts\activate
```

## Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, verify Python:

```bash
python --version
```

Expected:

```text
Python 3.11.x
```

or a newer supported version.

---

# 4. Install Dependencies

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install OnC dependencies:

```bash
pip install -r requirements.txt
```

If a development requirements file exists:

```bash
pip install -r requirements-dev.txt
```

---

# 5. Install FFmpeg

FFmpeg is required for media and video processing.

Verify the installation:

```bash
ffmpeg -version
```

Also verify FFprobe:

```bash
ffprobe -version
```

Both commands must work from the terminal.

If `ffmpeg` is not recognized, install FFmpeg and add its `bin` directory to your system PATH.

---

# 6. Install ImageMagick

ImageMagick is used by workflows that require image processing or conversion.

Verify:

```bash
magick -version
```

If your installation uses the older command:

```bash
convert -version
```

Make sure ImageMagick is available from the terminal.

---

# 7. Configure Environment Variables

OnC uses environment variables for API credentials, IDs and runtime configuration.

If `.env.example` exists, copy it:

```bash
cp .env.example .env
```

On Windows, you can also simply duplicate:

```text
.env.example
```

and rename the copy to:

```text
.env
```

Your final structure should look like:

```text
Nyavodroid-OnC/
├── .env
├── .env.example
├── requirements.txt
└── ...
```

### IMPORTANT

Never upload your real `.env` file to GitHub.

Your `.env` file contains private credentials.

---

# 8. Configure API Keys

Open:

```text
.env
```

You will find variables similar to:

```env
API_KEY=your_api_key_here
```

Replace placeholder values with your own credentials.

Never put quotation marks around a value unless the configuration specifically requires them.

Example:

```env
MISTRAL_API_KEY=xxxxxxxx
```

Not:

```env
MISTRAL_API_KEY=your_real_key_here
```

---

# 9. Configure Social Media IDs

Social-media automation generally requires both:

1. An account/page ID
2. An access token

For example:

```env
FB_PAGE_ID=YOUR_PAGE_ID
FB_PAGE_ACCESS_TOKEN=YOUR_PAGE_ACCESS_TOKEN
```

These are two different values.

### Page ID

The Page ID identifies the social-media page.

Example:

```env
FB_PAGE_ID=123456789012345
```

### Access Token

The access token authorizes OnC to perform the operations allowed by that token.

Example:

```env
FB_PAGE_ACCESS_TOKEN=EAABxxxxxxxxxxxxxxxx
```

### IMPORTANT

Never publish your access token in:

- GitHub
- README files
- screenshots
- public issues
- Discord
- public forums
- source code

If a token becomes public, revoke it immediately and create a new one.

---

# 10. Configure Search and Verification APIs

If your installation uses external search or fact-checking services, configure their API keys.

For example:

```env
TAVILY_API_KEY=YOUR_TAVILY_API_KEY
```

If image search/retrieval is enabled:

```env
PEXELS_API_KEY=YOUR_PEXELS_API_KEY
```

Only configure services actually used by your OnC installation.

---

# 11. Configure Image Generation APIs

OnC may support several image-generation providers.

Depending on your configuration, variables can include:

```env
CLOUDFLARE_ACCOUNT_ID=YOUR_ACCOUNT_ID
CLOUDFLARE_API_TOKEN=YOUR_API_TOKEN
```

Other providers may require variables such as:

```env
FAL_API_KEY=YOUR_FAL_KEY
REPLICATE_API_TOKEN=YOUR_REPLICATE_TOKEN
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
```

Do not configure a provider simply because its variable exists in an example.

Only activate providers you intend to use.

---

# 12. Configure AI Text Providers

Configure the AI providers required by your installation.

Example:

```env
MISTRAL_API_KEY=YOUR_MISTRAL_KEY
GEMINI_API_KEY_CONTENT=YOUR_GEMINI_KEY
TOGETHER_API_KEY=YOUR_TOGETHER_KEY
HF_TOKEN=YOUR_HUGGINGFACE_TOKEN
```

OnC may use a fallback chain.

For example:

```text
Provider 1
    ↓
Provider 2
    ↓
Provider 3
    ↓
Provider 4
```

This means that if a provider fails or reaches a limit, another configured provider may be used.

### Important

A fallback provider is only available if:

- the API key is configured;
- the account is active;
- the selected model is available;
- the API quota is sufficient.

---

# 13. Configure Themes

OnC uses YAML configuration files for themes and content configuration where enabled.

Look inside:

```text
themes/
```

Typical structure:

```text
themes/
├── theme_1.yaml
├── theme_2.yaml
└── ...
```

The exact filenames depend on the version of OnC you purchased.

---

## Creating a Theme

A theme can contain configuration such as:

```yaml
name: "My Theme"

colors:
  primary: "#000000"
  secondary: "#FFFFFF"

fonts:
  title: "Inter"
  body: "Inter"

style:
  image_style: "modern"

content:
  language: "fr"
```

Use the structure already expected by the OnC configuration loader.

**Do not invent new YAML fields unless the code supports them.**

Before changing a theme, inspect the existing YAML files and the configuration loader.

---

## Theme Checklist

For every theme you want to use:

- [ ] YAML file exists
- [ ] YAML syntax is valid
- [ ] Referenced fonts exist
- [ ] Referenced images exist
- [ ] Referenced directories exist
- [ ] Theme name matches the configuration
- [ ] No personal credentials are inside the YAML file

---

## Validate YAML

If PyYAML is installed, you can perform a basic syntax test:

```bash
python -c "import yaml; print(yaml.safe_load(open('themes/your_theme.yaml', encoding='utf-8')))"
```

Replace:

```text
themes/your_theme.yaml
```

with the actual theme filename.

---

# 14. Configure Images and Assets

OnC may require local assets such as:

- logos
- background images
- icons
- fonts
- sound effects
- video assets
- templates
- other media

Check:

```text
assets/
```

and other asset directories included in your release.

---

## Image Checklist

For every image referenced by the code:

- [ ] File exists
- [ ] Filename is correct
- [ ] Extension is correct
- [ ] File is readable
- [ ] The path used by the code is correct
- [ ] The image is not a personal/private asset
- [ ] The image can legally be used

Common supported formats may include:

```text
.png
.jpg
.jpeg
.webp
```

depending on the specific workflow.

---

## Missing Image Error

If OnC reports something similar to:

```text
FileNotFoundError
```

or:

```text
No such file or directory
```

check:

1. The filename.
2. The directory.
3. Uppercase/lowercase differences.
4. The path inside the configuration.
5. Whether the asset was included in your purchased release.

---

# 15. Configure GitHub Actions

GitHub Actions allows OnC workflows to run automatically.

Workflows are stored in:

```text
.github/workflows/
```

You may find files such as:

```text
.github/
└── workflows/
    ├── auto_content.yml
    ├── auto_story.yml
    ├── auto_video.yml
    └── ...
```

The exact workflow files depend on your release.

---

# 16. Configure GitHub Secrets

GitHub Actions should **not** read private credentials from committed files.

Instead, configure repository secrets.

Go to:

```text
GitHub Repository
    ↓
Settings
    ↓
Secrets and variables
    ↓
Actions
    ↓
New repository secret
```

Create the secrets required by your workflows.

For example:

```text
MISTRAL_API_KEY
GEMINI_API_KEY_CONTENT
TOGETHER_API_KEY
HF_TOKEN
TAVILY_API_KEY
PEXELS_API_KEY
FB_PAGE_ID
FB_PAGE_ACCESS_TOKEN
```

The secret names must match the names used by your workflow files.

---

# 17. Run a Local Test

Before enabling automatic publishing, test OnC locally.

First verify that Python can import the required modules.

For example:

```bash
python -m compileall .
```

This checks Python files for syntax errors.

A successful run should complete without Python syntax errors.

---

# 18. Run a Dry Run

If your workflow supports a dry-run option, enable it before publishing real content.

For example:

```env
DRY_RUN=1
```

or the exact variable supported by your workflow.

Check the code/workflow to determine the correct variable name.

A dry run should allow you to verify:

- configuration;
- API access;
- content generation;
- image generation;
- file creation;
- formatting;
- workflow logic;

without publishing real content.

---

# 19. Test Content Generation

Run the appropriate content-generation script.

For example:

```bash
python post_content.py
```

Verify that:

- the script starts successfully;
- the AI provider responds;
- content is generated;
- no API authentication error occurs;
- the output is saved correctly;
- no unexpected personal configuration is used.

---

# 20. Test Image Generation

Run the workflow responsible for image generation or run a complete content workflow that uses images.

Verify:

- the API key is accepted;
- an image is generated or retrieved;
- the image is saved;
- the expected file format is produced;
- the image can be opened;
- no fallback provider fails unexpectedly.

If the primary provider fails, verify that the configured fallback provider works.

---

# 21. Test Video Pipeline

If video generation is enabled, test the pipeline step by step.

```bash
python video_pipeline/01_script.py
```

Then:

```bash
python video_pipeline/02_voice.py
```

Then:

```bash
python video_pipeline/03_analyze.py
```

Then:

```bash
python video_pipeline/04_visuals.py
```

Then:

```bash
python video_pipeline/05_animate.py
```

Then:

```bash
python video_pipeline/06_audio.py
```

Then:

```bash
python video_pipeline/07_editor.py
```

Then:

```bash
python video_pipeline/08_qc.py
```

Only proceed to publishing after the quality-control step succeeds.

---

# 22. Test Publishing

Publishing should be the final test.

Before doing this:

- Verify the destination page/account.
- Verify the access token.
- Verify the Page ID.
- Verify the generated content.
- Disable dry-run mode only when you are ready.
- Make sure you are testing on the correct account.

Run the publishing workflow.

After publishing, verify the result directly on the destination platform.

---

# 23. Enable Automatic Workflows

Only enable automatic workflows after local testing is successful.

Go to:

```text
GitHub
    ↓
Repository
    ↓
Actions
```

Select the desired workflow.

If the workflow supports manual execution:

```text
Run workflow
```

Run it manually first.

Check the execution logs.

Only after a successful manual run should you rely on the scheduled trigger.

---

# 24. Troubleshooting

## API authentication error

Example:

```text
401 Unauthorized
```

Check:

- API key is correct.
- API key is active.
- Variable name is correct.
- `.env` is loaded.
- GitHub Secret name matches the workflow.
- The provider account has access to the requested model/service.

---

## Rate limit

Example:

```text
429 Too Many Requests
```

Possible causes:

- API quota reached.
- Too many requests.
- Free-tier limit.
- Provider temporarily limiting requests.

If a fallback provider is configured, OnC may switch to another provider.

Otherwise, wait for the provider quota to reset or configure another provider.

---

## Missing environment variable

Example:

```text
KeyError
```

or:

```text
API key not found
```

Check `.env` and compare the variable name with the name used in the Python code.

For GitHub Actions, check:

```text
Settings
→ Secrets and variables
→ Actions
```

---

## Missing file

Example:

```text
FileNotFoundError
```

Check:

- filename;
- directory;
- file extension;
- relative path;
- theme configuration;
- asset configuration.

---

## FFmpeg error

Verify:

```bash
ffmpeg -version
ffprobe -version
```

If either command fails, install FFmpeg correctly and make sure it is available in PATH.

---

## ImageMagick error

Verify:

```bash
magick -version
```

If this fails, reinstall ImageMagick or correct the PATH configuration.

---

## GitHub Actions failure

Open:

```text
GitHub
→ Actions
→ Failed workflow
→ Failed job
→ Logs
```

Read the first meaningful error rather than only looking at the final line.

Common causes:

- missing secret;
- invalid API key;
- missing dependency;
- incorrect path;
- unavailable third-party service;
- invalid configuration;
- workflow permissions.

---

# 25. Pre-Production Checklist

Before using OnC continuously, verify every item below.

## Installation

- [ ] Repository cloned
- [ ] Python installed
- [ ] Virtual environment created
- [ ] `requirements.txt` installed
- [ ] FFmpeg installed
- [ ] FFprobe installed
- [ ] ImageMagick installed

## Configuration

- [ ] `.env` created
- [ ] `.env` is ignored by Git
- [ ] API keys configured
- [ ] Social-media IDs configured
- [ ] Access tokens configured
- [ ] Search APIs configured
- [ ] Image APIs configured
- [ ] AI providers configured

## Themes

- [ ] Required YAML themes exist
- [ ] YAML syntax is valid
- [ ] Theme references are correct
- [ ] Required fonts exist
- [ ] Required images exist

## Assets

- [ ] Required images exist
- [ ] Required fonts exist
- [ ] Required sound effects exist
- [ ] Required video assets exist
- [ ] File paths are correct

## Testing

- [ ] Python compilation test passed
- [ ] Configuration test passed
- [ ] AI generation test passed
- [ ] Image generation test passed
- [ ] Fact-checking test passed
- [ ] Video pipeline tested if enabled
- [ ] Quality control passed
- [ ] Dry run passed
- [ ] Publishing test passed

## GitHub Actions

- [ ] Repository secrets configured
- [ ] Workflow permissions checked
- [ ] Manual workflow test passed
- [ ] Scheduled workflow checked
- [ ] Logs checked
- [ ] No credentials committed

---

# 🔐 Final Security Check

Before pushing anything to GitHub, run:

```bash
git status
```

Make sure `.env` is not listed.

You can also check tracked files:

```bash
git ls-files
```

Confirm that private credentials are not included.

Never commit:

```text
.env
private API keys
access tokens
passwords
cookies
private credentials
```

If you accidentally commit a secret:

1. Revoke the secret immediately.
2. Generate a replacement.
3. Remove the secret from the repository.
4. Check Git history if necessary.

---

# 🎉 Installation Complete

When all tests pass, OnC is ready for normal operation.

Recommended workflow:

```text
Install
   ↓
Configure APIs
   ↓
Configure IDs
   ↓
Configure Themes
   ↓
Configure Assets
   ↓
Configure GitHub Secrets
   ↓
Local Test
   ↓
Dry Run
   ↓
Manual Publishing Test
   ↓
GitHub Actions Test
   ↓
Enable Automation
```

---

# 📞 Support

If something does not work, collect:

- Operating system
- Python version
- OnC version
- Command executed
- Complete error message
- Relevant workflow log
- Configuration variable name involved

**Never send API keys, access tokens or passwords when requesting support.**

---

# ⚠️ Important

OnC integrates with third-party APIs and platforms.

Third-party services can change:

- APIs
- authentication systems
- quotas
- pricing
- available models
- permissions
- terms of service

Therefore, an API or platform may require configuration changes after an external service update.

The buyer is responsible for maintaining their own third-party accounts and credentials.

---

## OnC

**One Click Content**

Automate. Generate. Verify. Publish.

© 2026 Nyavo Rakotomavo — All Rights Reserved.