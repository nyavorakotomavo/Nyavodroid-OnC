# OnC — Quick Start

> **Complete setup guide for buyers**
>
> OnC is designed to run automatically through **GitHub Actions**.  
> Once the initial configuration is complete, your personal computer or phone does **not** need to remain powered on or connected to the Internet for scheduled workflows to run.
>
> **This guide is written for non-developers. You do not need to know Python to perform the standard installation.**

---

# 📌 Table of Contents

1. [How OnC Works](#1-how-onc-works)
2. [What You Need Before Starting](#2-what-you-need-before-starting)
3. [Important Security Rules](#3-important-security-rules)
4. [Create or Prepare Your GitHub Account](#4-create-or-prepare-your-github-account)
5. [Create Your OnC Repository](#5-create-your-onc-repository)
6. [Upload the OnC Files](#6-upload-the-onc-files)
7. [Check the Repository Structure](#7-check-the-repository-structure)
8. [Configure GitHub Actions](#8-configure-github-actions)
9. [Configure GitHub Secrets](#9-configure-github-secrets)
10. [Configure Social Media IDs](#10-configure-social-media-ids)
11. [Configure AI Providers](#11-configure-ai-providers)
12. [Configure Search and Fact-Checking APIs](#12-configure-search-and-fact-checking-apis)
13. [Configure Image Generation Providers](#13-configure-image-generation-providers)
14. [Configure Other API Services](#14-configure-other-api-services)
15. [Configure YAML Themes](#15-configure-yaml-themes)
16. [Configure Images and Assets](#16-configure-images-and-assets)
17. [Configure Content Settings](#17-configure-content-settings)
18. [Verify Workflow Configuration](#18-verify-workflow-configuration)
19. [First Manual Test](#19-first-manual-test)
20. [Read the Workflow Logs](#20-read-the-workflow-logs)
21. [Test Real Publishing](#21-test-real-publishing)
22. [Enable Automatic Publishing](#22-enable-automatic-publishing)
23. [What Happens When Your Device Is Off](#23-what-happens-when-your-device-is-off)
24. [Local Testing for Developers](#24-local-testing-for-developers)
25. [Troubleshooting](#25-troubleshooting)
26. [Final Production Checklist](#26-final-production-checklist)

---

# 1. How OnC Works

## ☁️ OnC runs through GitHub Actions

The standard OnC installation is designed around GitHub Actions.

Your personal device is primarily used for the **initial setup and configuration**.

After the setup is complete, GitHub can execute the OnC workflows on its own hosted runners.

```text
                 YOUR DEVICE
              PC / Phone / Tablet
                     │
                     │
              Initial configuration
                     │
                     ▼
              ┌───────────────┐
              │    GitHub     │
              │   Repository  │
              └───────┬───────┘
                      │
             GitHub Actions
                      │
                      ▼
              ┌───────────────┐
              │      OnC      │
              │    Workflows  │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
         AI        Images       Video
          │           │           │
          └───────────┼───────────┘
                      ▼
                 Fact-checking
                      │
                      ▼
                  Publishing
                      │
                      ▼
                Social Media
```

## Your device does NOT need to stay on

After the configuration is complete:

```text
PC turned off       → OnC can continue running
Phone turned off    → OnC can continue running
VS Code closed      → OnC can continue running
Browser closed      → OnC can continue running
Internet disconnected
from your device    → OnC can continue running
```

The important condition is that:

- GitHub Actions is available;
- the workflow is enabled;
- the repository is correctly configured;
- the required secrets exist;
- third-party APIs are available;
- API quotas have not been exceeded.

---

# 2. What You Need Before Starting

You will need:

## Required

- A GitHub account
- Access to your licensed OnC source code
- A repository where OnC will be installed
- An account/page on the social platform you want OnC to publish to
- The required social-media permissions
- The required API accounts
- Your API keys/tokens
- The required page/account IDs

## Optional

Depending on the features you want to use:

- AI text-generation providers
- AI image-generation providers
- Search/fact-checking providers
- Image providers
- Video-related services

You do **not** need to keep your computer running after the GitHub Actions installation is complete.

---

# 3. Important Security Rules

## 🔴 NEVER publish your API keys

Never put private credentials inside:

```text
README.md
QUICKSTART.md
LICENSE
Python source files
YAML themes
GitHub Issues
GitHub Discussions
screenshots
```

Never send your private API keys to another person.

---

## Never commit `.env`

Your local `.env` file is private.

Do not upload it to GitHub.

The repository should contain:

```text
.env.example
```

but not:

```text
.env
```

---

## GitHub Actions secrets

For automatic execution, private credentials should normally be stored as:

```text
GitHub Repository
        ↓
Settings
        ↓
Secrets and variables
        ↓
Actions
        ↓
Repository secrets
```

This prevents the secret from being written directly into the workflow file.

---

# 4. Create or Prepare Your GitHub Account

Go to GitHub and sign in.

If you do not already have an account:

1. Create a GitHub account.
2. Verify your email address.
3. Sign in.
4. Make sure you can create repositories.

You do not need to install Git locally for the standard GitHub web-based setup.

---

# 5. Create Your OnC Repository

You need a GitHub repository containing your licensed OnC installation.

## Option A — You received a complete repository

If the seller provided a repository or repository access:

1. Open the repository.
2. Follow the seller's instructions for creating your licensed copy.
3. Make sure you have your own repository.
4. Do not modify the original seller repository.

---

## Option B — You received an archive

If you received something such as:

```text
OnC.zip
```

create a new GitHub repository.

Recommended:

```text
Repository name:
Nyavodroid-OnC
```

or another name of your choice.

You may choose the repository visibility according to your license and security requirements.

### Recommended

Use a **private repository** when the source code is licensed for private use.

---

# 6. Upload the OnC Files

If you received an archive:

1. Extract the archive.
2. Open your GitHub repository.
3. Select **Add file**.
4. Select **Upload files**.
5. Upload the OnC project files.
6. Make sure the `.github` directory is included.
7. Make sure the workflow files are included.
8. Commit the changes.

Your repository should contain the OnC source code and configuration files.

---

# 7. Check the Repository Structure

Before configuring anything, open the repository and verify that important directories are present.

A typical OnC installation may look similar to:

```text
Nyavodroid-OnC/
│
├── .github/
│   └── workflows/
│       ├── auto_content.yml
│       ├── auto_story.yml
│       ├── auto_video.yml
│       ├── vis.yml
│       ├── vis_stories.yml
│       └── voyage_madagascar.yml
│
├── assets/
│
├── themes/
│
├── video_pipeline/
│
├── .env.example
├── LICENSE
├── README.md
├── QUICKSTART.md
├── requirements.txt
└── Python source files
```

The exact files may differ depending on your purchased version.

### Important

Do not delete files simply because you do not immediately understand their purpose.

A workflow, image, font, YAML file, or Python module may be required by another part of OnC.

---

# 8. Configure GitHub Actions

GitHub Actions is the part of GitHub that executes OnC automatically.

Open your repository:

```text
GitHub
   ↓
Your Repository
   ↓
Actions
```

You should see the workflows included with OnC.

For example:

```text
Auto Content
Auto Story
Auto Video
VIS
VIS Stories
Voyage Madagascar
```

The exact workflow names depend on your version.

---

## If the Actions tab shows your workflows

Good.

Continue to the next step.

---

## If no workflows appear

Check:

```text
.github/workflows/
```

The YAML workflow files must be present there.

For example:

```text
.github/workflows/auto_content.yml
```

---

# 9. Configure GitHub Secrets

This is one of the most important steps.

GitHub Actions needs access to the APIs used by OnC.

Instead of putting API keys inside the source code, add them as GitHub Actions secrets.

Open:

```text
Repository
   ↓
Settings
   ↓
Secrets and variables
   ↓
Actions
```

Select:

```text
New repository secret
```

You will enter:

```text
Name
Secret
```

---

## Example

Suppose OnC requires:

```text
MISTRAL_API_KEY
```

Enter:

```text
Name:
MISTRAL_API_KEY
```

Then put your real Mistral API key in:

```text
Secret:
YOUR_REAL_MISTRAL_API_KEY
```

Click:

```text
Add secret
```

---

# 10. Configure Social Media IDs

Social-media publishing normally requires both an **ID** and an **access token**.

These are different things.

## Page ID

The Page ID identifies the destination page.

Example:

```text
123456789012345
```

## Access Token

The access token gives OnC permission to perform the actions allowed by the token.

Example:

```text
EAABxxxxxxxxxxxxxxxx
```

Do not copy these example values.

Use the values belonging to your own account.

---

## Example GitHub Secrets

Depending on your OnC version, you may need variables such as:

```text
FB_PAGE_ID
FB_PAGE_ACCESS_TOKEN
VIS_FB_PAGE_ID
VIS_FB_PAGE_TOKEN
FACEBOOK_PAGE_ID
FACEBOOK_PAGE_ACCESS_TOKEN
```

### IMPORTANT

The names must match the names used by your actual workflow files.

Do not create random variable names.

For example, if your workflow contains:

```yaml
${{ secrets.FB_PAGE_ACCESS_TOKEN }}
```

the secret must be named:

```text
FB_PAGE_ACCESS_TOKEN
```

not:

```text
FACEBOOK_TOKEN
```

---

# 11. Configure AI Providers

OnC can use external AI providers for content generation.

The exact providers available depend on your version.

Examples may include:

```text
Mistral
Gemini
Together
Hugging Face
```

Possible secret names include:

```text
MISTRAL_API_KEY
GEMINI_API_KEY_CONTENT
GEMINI_API_KEY_STORY
TOGETHER_API_KEY
HF_TOKEN
```

Only configure providers actually used by your workflows.

---

## AI fallback system

If your version uses provider fallback, the system can operate conceptually like:

```text
Primary provider
       │
       ├── Success → continue
       │
       └── Failure
             ↓
       Backup provider
             │
             ├── Success → continue
             │
             └── Failure
                   ↓
             Next provider
```

A fallback is only possible when:

- the provider is configured;
- the API key is valid;
- the account has available quota;
- the requested service/model is available.

---

# 12. Configure Search and Fact-Checking APIs

Some OnC workflows use external services for research, search, or verification.

For example:

```text
TAVILY_API_KEY
```

If your version uses Pexels:

```text
PEXELS_API_KEY
```

Add the required credentials as GitHub Actions secrets.

Example:

```text
Name:
TAVILY_API_KEY

Secret:
YOUR_REAL_TAVILY_KEY
```

---

# 13. Configure Image Generation Providers

Depending on your installation, OnC may use one or more image providers.

Possible services include:

```text
Cloudflare
Hugging Face
Together
Fal.ai
Replicate
Pollinations
```

Possible variables may include:

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
FAL_API_KEY
REPLICATE_API_TOKEN
HF_TOKEN
```

Only configure services actually required by your workflows.

---

## Cloudflare example

If your workflow expects:

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

create both secrets.

Do not combine them into one secret.

---

# 14. Configure Other API Services

Some versions of OnC may require additional services.

Before creating a secret:

1. Open the relevant workflow.
2. Look for:

```yaml
secrets.
```

3. Write down every required secret.
4. Create the corresponding GitHub Actions secrets.

For example:

```yaml
${{ secrets.EXAMPLE_API_KEY }}
```

means that GitHub needs a secret named:

```text
EXAMPLE_API_KEY
```

---

# 15. Configure YAML Themes

OnC uses YAML configuration files for themes and content configuration where supported.

Open:

```text
themes/
```

You may find files such as:

```text
nyavo.yaml
vis.yaml
voyage_madagascar.yaml
```

The exact files depend on your OnC version.

---

## What is a YAML theme?

A YAML theme contains configuration that controls how content is generated or presented.

For example:

```yaml
name: "My Theme"

colors:
  primary: "#000000"
  secondary: "#FFFFFF"

fonts:
  title: "Inter"
  body: "Inter"
```

The actual fields supported by OnC depend on the version.

---

## Do not invent configuration fields

If the existing theme contains:

```yaml
colors:
fonts:
style:
content:
```

do not automatically add:

```yaml
something_random:
```

unless the OnC code supports it.

---

## Editing a theme

1. Open the desired `.yaml` file.
2. Change only the values you want to customize.
3. Keep the YAML structure intact.
4. Save the file.
5. Commit the change.

---

## YAML indentation is important

This is valid:

```yaml
colors:
  primary: "#000000"
  secondary: "#FFFFFF"
```

This may break the configuration:

```yaml
colors:
primary: "#000000"
secondary: "#FFFFFF"
```

Be careful with spaces and indentation.

---

# 16. Configure Images and Assets

OnC may require local assets.

Look inside:

```text
assets/
```

You may find:

```text
images
fonts
emojis
sfx
logos
```

The exact structure depends on your version.

---

## Replacing an image

If the project expects:

```text
assets/images/logo.png
```

and you want to replace it:

1. Prepare your new image.
2. Use the expected filename.
3. Put it in the expected directory.
4. Commit the change.

Example:

```text
assets/
└── images/
    └── logo.png
```

---

## Do not randomly rename files

If Python or YAML references:

```text
assets/images/logo.png
```

and you rename the file to:

```text
assets/images/mylogo.png
```

the workflow may fail.

If you want to change the filename, update every corresponding reference.

---

# 17. Configure Content Settings

Depending on your version, OnC may use environment variables or configuration files to control content generation.

Examples may include:

```text
BRAND
FORCE_FORMAT
STRATEGIE_JSON
VIS_FORCE_PILIER
VIS_EXCLUDE
VIS_DRY_RUN
```

Only use variables that actually exist in your version.

---

## Example

If your workflow expects:

```text
BRAND=nyavo
```

use:

```text
nyavo
```

Do not use:

```text
NyavoBrand
```

unless the code explicitly supports it.

---

# 18. Verify Workflow Configuration

Before running OnC automatically, open each workflow.

Go to:

```text
.github/workflows/
```

Open the YAML files one by one.

Check:

### Secrets

Look for:

```yaml
secrets.
```

Example:

```yaml
${{ secrets.MISTRAL_API_KEY }}
```

Make sure the corresponding secret exists.

---

### Repository files

Check that scripts referenced by the workflow actually exist.

Example:

```yaml
python post_content.py
```

means that:

```text
post_content.py
```

must exist in the expected location.

---

### Python version

Check the Python version used by the workflow.

It should be compatible with the version required by OnC.

---

### Schedule

Look for:

```yaml
schedule:
```

Example:

```yaml
schedule:
  - cron: "00 07 * * *"
```

The exact schedule depends on your workflow.

Remember:

> GitHub Actions cron schedules use **UTC** unless the workflow specifically handles another timezone.

---

# 19. First Manual Test

Do **not** immediately activate automatic publishing.

First perform a manual test.

Open:

```text
GitHub
   ↓
Repository
   ↓
Actions
```

Select the workflow you want to test.

If the workflow supports manual execution, you will see:

```text
Run workflow
```

Click it.

---

## What you should see

GitHub will create a workflow run.

You should see stages similar to:

```text
Queued
   ↓
Set up job
   ↓
Checkout
   ↓
Set up Python
   ↓
Install dependencies
   ↓
Load configuration
   ↓
Call APIs
   ↓
Generate content
   ↓
Generate/retrieve media
   ↓
Quality control
   ↓
Publish
```

The exact steps depend on the workflow.

---

# 20. Read the Workflow Logs

If the workflow succeeds:

```text
✓ Success
```

Good.

If it fails:

```text
✗ Failure
```

click the failed job.

Open the failed step.

Read the error message.

---

## Common errors

### `401 Unauthorized`

Usually means:

```text
Invalid API key
Invalid token
Incorrect authentication
```

---

### `403 Forbidden`

Usually means:

```text
Missing permission
Insufficient access
Platform restriction
```

---

### `404 Not Found`

Usually means:

```text
Wrong ID
Wrong endpoint
Missing resource
```

---

### `429 Too Many Requests`

Usually means:

```text
Rate limit
API quota exceeded
Too many requests
```

---

### `ModuleNotFoundError`

Usually means:

```text
A Python dependency is missing.
```

Check:

```text
requirements.txt
```

and the workflow installation step.

---

### `FileNotFoundError`

Usually means:

```text
A required file/image/font/configuration is missing.
```

Check:

```text
assets/
themes/
```

and the paths used by the code.

---

# 21. Test Real Publishing

Only perform this after the workflow itself successfully runs.

Before the first real publication, verify:

- correct destination page;
- correct Page ID;
- correct access token;
- correct brand;
- correct theme;
- correct image;
- correct content;
- correct publishing format.

If a dry-run mode exists in your version, use it first.

---

## First real publication

Run one workflow manually.

Wait for:

```text
✓ Workflow successful
```

Then check the destination social-media page.

Verify:

- content was published;
- image/video is correct;
- text is correct;
- formatting is correct;
- no unexpected content was published.

---

# 22. Enable Automatic Publishing

Once manual testing is successful, automatic scheduling can be used.

Go to:

```text
GitHub
   ↓
Actions
   ↓
Your workflow
```

Make sure the workflow is enabled.

The scheduled trigger will then run according to the schedule defined in its YAML file.

---

## Important

GitHub Actions scheduling is not the same thing as a program running permanently.

Instead:

```text
Scheduled time
      ↓
GitHub starts a runner
      ↓
OnC executes
      ↓
OnC finishes
      ↓
Runner stops
```

This is normal.

OnC does not need to remain running continuously.

---

# 23. What Happens When Your Device Is Off

After successful configuration:

```text
10:00
Your PC → OFF

Your phone → OFF

Internet on your device → OFF

        ↓

GitHub
        ↓
Scheduled workflow
        ↓
GitHub-hosted runner
        ↓
OnC
        ↓
AI APIs
        ↓
Media generation
        ↓
Publishing
```

Your personal device is not required for the workflow execution.

However, the workflow can only run if the external requirements are available.

For example:

```text
GitHub Actions available       ✓
Workflow enabled               ✓
Secrets valid                  ✓
API quota available            ✓
Social-media permissions valid ✓
Third-party services available ✓
```

---

# 24. Local Testing for Developers

This section is optional.

Normal buyers do **not** need to run OnC locally for scheduled automation.

Local execution is useful for:

- development;
- debugging;
- testing;
- modifying the code;
- testing themes;
- investigating errors.

---

## Install Python

```bash
python --version
```

Create a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Syntax test

Run:

```bash
python -m compileall .
```

If no Python syntax errors are reported, the compilation check passes.

---

## Local configuration

If local execution is supported, create:

```text
.env
```

from:

```text
.env.example
```

Never commit the real `.env`.

---

# 25. Troubleshooting

## OnC does not appear in GitHub Actions

Check:

```text
.github/workflows/
```

Make sure the workflow files are actually committed.

---

## Workflow starts but immediately fails

Check:

1. Python version.
2. Dependencies.
3. Missing secrets.
4. Workflow permissions.
5. File paths.

---

## API key error

Check the secret name.

For example, if the workflow contains:

```yaml
${{ secrets.GEMINI_API_KEY_CONTENT }}
```

the GitHub secret must be exactly:

```text
GEMINI_API_KEY_CONTENT
```

Capitalization and spelling matter.

---

## Social-media publishing fails

Check:

```text
Page ID
Access Token
Permissions
Token expiration
API availability
```

Do not assume that a valid token automatically has every permission required by the platform.

---

## Theme causes an error

Check:

```text
YAML syntax
Indentation
Filename
Referenced assets
Supported configuration fields
```

---

## Image is missing

Check:

```text
assets/
```

Then verify that the filename used by the code or YAML exactly matches the actual filename.

---

## Workflow cannot find a Python file

Example:

```text
python post_content.py
```

but GitHub reports:

```text
No such file or directory
```

Check the repository structure.

The workflow command must match the actual location of the script.

---

## GitHub Actions does not run at the exact scheduled minute

Scheduled workflows can sometimes start later than their nominal schedule.

Do not design a workflow that assumes execution will begin at the exact second specified by a cron expression.

---

# 26. Final Production Checklist

Do not consider the installation complete until these checks pass.

## 🟢 Repository

- [ ] OnC source code uploaded
- [ ] `.github/workflows/` exists
- [ ] `requirements.txt` exists
- [ ] `README.md` exists
- [ ] `QUICKSTART.md` exists
- [ ] `LICENSE` exists
- [ ] `.env.example` exists
- [ ] `.env` is NOT committed

---

## 🟢 GitHub Actions

- [ ] Actions tab is available
- [ ] Workflows are visible
- [ ] Workflows are enabled
- [ ] Required permissions are configured
- [ ] Manual workflow can start
- [ ] Manual workflow completes successfully

---

## 🟢 Secrets

- [ ] Social-media IDs configured
- [ ] Social-media tokens configured
- [ ] AI API keys configured
- [ ] Search API keys configured
- [ ] Image API keys configured
- [ ] Other required secrets configured
- [ ] Secret names exactly match workflow names
- [ ] No secret is written directly in source code

---

## 🟢 Themes

- [ ] Required YAML files exist
- [ ] YAML syntax is valid
- [ ] Theme names are correct
- [ ] Referenced fonts exist
- [ ] Referenced images exist
- [ ] No personal credentials are inside YAML files

---

## 🟢 Assets

- [ ] Required images exist
- [ ] Required fonts exist
- [ ] Required sound effects exist
- [ ] Required video assets exist
- [ ] Paths are correct
- [ ] No private/personal asset is included accidentally

---

## 🟢 Testing

- [ ] Python syntax check passed
- [ ] Dependencies installed successfully
- [ ] AI generation tested
- [ ] Image generation tested
- [ ] Fact-checking tested if enabled
- [ ] Video pipeline tested if enabled
- [ ] Dry run tested if available
- [ ] Manual workflow tested
- [ ] Real publication tested

---

## 🟢 Automation

- [ ] Scheduled workflow is enabled
- [ ] Cron schedule has been checked
- [ ] UTC timezone has been understood
- [ ] GitHub Actions logs show successful runs
- [ ] The user does not need to keep their computer running

---

# 🎉 Installation Complete

If every required item above is checked, your OnC installation is ready for automated operation through GitHub Actions.

The normal operating model is:

```text
             ONE-TIME SETUP
                   │
                   ▼
          GitHub Repository
                   │
                   ▼
        Configure API Secrets
                   │
                   ▼
        Configure IDs & Themes
                   │
                   ▼
          Test Manually
                   │
                   ▼
        Test Real Publication
                   │
                   ▼
        Enable Scheduled Runs
                   │
                   ▼
             AUTOMATION
                   │
                   ▼
        ┌────────────────────┐
        │    GitHub Actions  │
        └─────────┬──────────┘
                  │
                  ▼
                 OnC
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
       Text     Images    Videos
        │         │         │
        └─────────┼─────────┘
                  ▼
             Verification
                  │
                  ▼
              Publishing
```

## Your device can now be turned off.

OnC does not require your personal computer or phone to remain powered on for scheduled GitHub Actions workflows.

The automation depends on the availability and limits of:

- GitHub Actions;
- your configured APIs;
- social-media platforms;
- third-party services;
- API quotas;
- account permissions;
- the OnC workflow configuration.

---

# 🔐 Final Security Reminder

Never share:

```text
API keys
Access tokens
Passwords
GitHub tokens
Cookies
Private credentials
```

If a credential is accidentally exposed:

1. Revoke it immediately.
2. Create a replacement.
3. Update the corresponding GitHub secret.
4. Check the repository history if necessary.

---

# 📦 Buyer Responsibility

The buyer is responsible for:

- creating and maintaining their own third-party accounts;
- obtaining their own API keys;
- maintaining their own social-media permissions;
- paying any third-party API costs;
- respecting the terms of the services they connect to OnC;
- maintaining their GitHub account;
- monitoring API quotas and limits.

OnC does not include the seller's private API credentials, social-media accounts, access tokens, or personal configuration.

---

# ⚠️ Third-Party Services

OnC depends on external services.

Those services may change:

- APIs;
- authentication;
- permissions;
- pricing;
- quotas;
- models;
- rate limits;
- availability;
- terms of service.

An external service change may therefore require configuration or code updates.

---

# 🏁 OnC Ready

Once the final checklist passes:

```text
Repository       ✓
Secrets          ✓
IDs              ✓
Themes           ✓
Assets           ✓
Workflows        ✓
Manual test      ✓
Publishing test  ✓
Automation       ✓
```

Your OnC installation is ready to operate automatically through GitHub Actions.

**One Click Content — Automate. Generate. Verify. Publish.**

© 2026 Nyavo Rakotomavo — All Rights Reserved.