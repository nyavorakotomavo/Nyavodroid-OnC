# OnC — One Click Content

> **Automated AI-Powered Content Generation & Publishing System**
> *Powered by AI, Built for Automation*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Commercial](https://img.shields.io/badge/license-Commercial-orange.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Supported-brightgreen)](https://github.com/features/actions)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 📌 About OnC

**OnC (One Click Content)** is an automated content generation and publishing system designed to automate the complete content workflow — from research and generation to media creation, quality control and publishing.

OnC combines:

- AI providers
- RSS and online sources
- Fact-checking
- Image generation and retrieval
- Voice generation
- Video generation
- Video editing
- Quality control
- Social media publishing
- GitHub Actions automation

The system is designed to be configurable so that each user can adapt it to their own content strategy, services and infrastructure.

---

## 🎯 Core Mission

OnC aims to automate repetitive content-production tasks while keeping the workflow configurable and reliable.

### Main objectives

- **Automate** content creation from research to publishing.
- **Reduce manual work** through configurable workflows.
- **Improve reliability** with provider fallbacks.
- **Verify information** using external sources and fact-checking.
- **Generate multimedia content** including images, audio and video.
- **Automate recurring tasks** with GitHub Actions.
- **Allow users to adapt the system** to their own projects and businesses.

---

# ✨ Features

## 📰 Automated Content Generation

OnC can automate several stages of the content creation process:

| Feature | Description |
|---|---|
| **Text Generation** | Generate content using configurable AI providers |
| **Image Content** | Generate or retrieve images for publications |
| **Multi-Format Content** | Support different content formats |
| **Fact-Checking** | Verify information using external sources |
| **RSS Integration** | Retrieve information from configured RSS feeds |
| **AI Video Pipeline** | Generate videos from scripts, audio and visual assets |
| **Quality Control** | Validate generated media before publishing |
| **Automated Publishing** | Publish generated content through supported platforms |
| **Scheduled Automation** | Run recurring workflows through GitHub Actions |

---

# 🤖 AI Provider System

OnC can use multiple AI providers through a configurable fallback system.

The purpose of the fallback architecture is to improve availability when a provider:

- reaches its rate limit;
- becomes temporarily unavailable;
- returns an error;
- or cannot process a request.

### Text Generation

Example provider chain:

```text
Mistral
   ↓
Together
   ↓
Gemini
   ↓
Hugging Face