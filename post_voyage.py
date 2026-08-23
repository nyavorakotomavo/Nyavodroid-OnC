#!/usr/bin/env python3
"""
VoyageMadagascar - Moteur de publication avec Mistral + Pexels uniquement.
Generer et publie du contenu de voyage en utilisant :
  - Mistral pour le texte (guides, descriptions, conseils)
  - Pexels pour les images
  - Publication sur Facebook
"""

import os
import sys
import json
import random
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# ============================================
# CONFIGURATION
# ============================================
BRAND = "voyage_madagascar"

# Charger la configuration du theme
try:
    from content_config import get_config
    CONFIG = get_config(BRAND)
except Exception as e:
    print(f"Erreur chargement config: {e}")
    sys.exit(1)

# ============================================
# VALIDATION DES VARIABLES ENVIRONNEMENT
# ============================================
REQUIRED_ENV = {
    "MISTRAL_API_KEY": "Cle API Mistral pour la generation de texte",
    "PEXELS_API_KEY": "Cle API Pexels pour les images",
    "FACEBOOK_PAGE_ACCESS_TOKEN": "Token d'acces Facebook pour publier",
    "FACEBOOK_PAGE_ID": "ID de la page Facebook"
}

missing = []
for key, desc in REQUIRED_ENV.items():
    if key not in os.environ:
        missing.append(f"{key} ({desc})")

if missing:
    print(f"Variables manquantes: {', '.join(missing)}")
    sys.exit(1)

MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
FB_TOKEN = os.environ["FACEBOOK_PAGE_ACCESS_TOKEN"]
FB_PAGE_ID = os.environ["FACEBOOK_PAGE_ID"]

# ============================================
# FONCTIONS MISTRAL
# ============================================
def generate_text_with_mistral(prompt, max_tokens=1500, temperature=0.8):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erreur Mistral API: {e}")
        return CONFIG.get("fallback", {}).get("text", "Decouvrez Madagascar...")

# ============================================
# FONCTIONS PEXELS
# ============================================
def search_pexels_image(query, orientation="landscape", size="large"):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": orientation,
        "size": size,
        "per_page": 10
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("photos"):
            photo = random.choice(data["photos"])
            return photo["src"][size]
        return None
    except Exception as e:
        print(f"Erreur Pexels API: {e}")
        return None

# ============================================
# FONCTIONS FACEBOOK
# ============================================
def publish_to_facebook(text, image_url=None):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
    payload = {"message": text, "access_token": FB_TOKEN}
    
    if image_url:
        try:
            img_data = requests.get(image_url, timeout=30).content
            files = {"source": ("image.jpg", img_data)}
            response = requests.post(url, data={"access_token": FB_TOKEN, "message": text}, files=files, timeout=60)
        except Exception as e:
            print(f"Erreur telechargement image: {e}")
            response = requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed", data=payload, timeout=60)
    else:
        response = requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed", data=payload, timeout=60)
    
    try:
        result = response.json()
        if response.status_code == 200 and "id" in result:
            print(f"Publie sur Facebook: {result['id']}")
            return True
        else:
            print(f"Erreur publication Facebook: {result.get('error', response.text)}")
            return False
    except Exception as e:
        print(f"Erreur JSON Facebook: {e}")
        return False

# ============================================
# GENERATION DE CONTENU
# ============================================
def generate_travel_guide(destination=None):
    if not destination:
        destinations = ["Antananarivo", "Nosy Be", "Isalo", "Andasibe", "Tulear", "Morondava"]
        destination = random.choice(destinations)
    
    prompt = CONFIG.get("mistral_prompts", {}).get("travel_guide", {}).get("user", "")
    prompt = prompt.format(destination=destination, min_length=300, max_length=1500)
    text = generate_text_with_mistral(prompt)
    image_url = search_pexels_image(f"{destination} Madagascar travel")
    
    return {
        "type": "travel_guide",
        "content": text,
        "image_url": image_url,
        "destination": destination
    }

def generate_destination_highlight(destination=None):
    if not destination:
        destinations = ["Baobabs Avenue", "Plage Ifaty", "Parc National Isalo", 
                       "Lemurs Park", "Tsaranabanjina", "Canal des Pangalanes"]
        destination = random.choice(destinations)
    
    prompt = CONFIG.get("mistral_prompts", {}).get("destination_highlight", {}).get("user", "")
    prompt = prompt.format(destination=destination)
    text = generate_text_with_mistral(prompt)
    image_url = search_pexels_image(f"{destination} Madagascar")
    
    return {
        "type": "destination_highlight",
        "content": text,
        "image_url": image_url,
        "destination": destination
    }

def generate_travel_tip():
    prompt = CONFIG.get("mistral_prompts", {}).get("travel_tip", {}).get("user", "")
    text = generate_text_with_mistral(prompt)
    return {
        "type": "travel_tip",
        "content": text,
        "image_url": None
    }

# ============================================
# MAIN
# ============================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Publier du contenu VoyageMadagascar")
    parser.add_argument("--content-type", type=str, choices=["travel_guide", "destination_highlight", "travel_tip"],
                        help="Type de contenu a publier")
    parser.add_argument("--auto-publish", action="store_true", help="Publier automatiquement")
    parser.add_argument("--dry-run", action="store_true", help="Mode test")
    args = parser.parse_args()
    
    print(f"Demarrage publication VoyageMadagascar - Type: {args.content_type}")
    
    if args.content_type == "travel_guide":
        content = generate_travel_guide()
    elif args.content_type == "destination_highlight":
        content = generate_destination_highlight()
    elif args.content_type == "travel_tip":
        content = generate_travel_tip()
    else:
        print("Type de contenu invalide")
        sys.exit(1)
    
    print(f"Contenu genere: {content['type']}")
    print(f"Texte: {content['content'][:100]}...")
    if content.get('image_url'):
        print(f"Image: {content['image_url']}")
    
    if args.auto_publish and not args.dry_run:
        success = publish_to_facebook(content["content"], content.get("image_url"))
        if not success:
            print("Publication echouee, mais le contenu est pret")
    else:
        print("Mode dry-run ou auto-publish desactive - pas de publication")
    
    print("Termine!")

if __name__ == "__main__":
    main()
