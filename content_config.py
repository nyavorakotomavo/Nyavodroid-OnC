#!/usr/bin/env python3
"""
Nyavodroid — Dispatcher multi-marques (ÉTAPE 1 — définitif).
Route vers la config éditoriale de la marque désignée par la variable d'env BRAND :
  BRAND absent / "nyavo" → content_config_nyavo (page tech originale)
  BRAND = "vis"          → content_config_vis (page paraboles illustrées)
  BRAND = "<autre>"      → content_config_<autre> (marque future, sans toucher ce fichier)
Module inexistant → fallback sécurisé vers nyavo, jamais de crash.
Tous les `from content_config import ...` existants fonctionnent sans changement.
CE FICHIER NE SERA PLUS JAMAIS MODIFIÉ.
"""
import importlib
import os

BRAND = os.environ.get("BRAND", "nyavo").strip().lower()

try:
    _mod = importlib.import_module(f"content_config_{BRAND}")
    print(f"🎭 Marque active : {BRAND}")
except ImportError:
    _mod = importlib.import_module("content_config_nyavo")
    print(f"⚠️ Marque '{BRAND}' sans config → fallback nyavo")

globals().update({k: v for k, v in _mod.__dict__.items() if not k.startswith("_")})
