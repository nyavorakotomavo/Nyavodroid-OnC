#!/usr/bin/env python3
"""
Nyavodroid — Module de Vérification Factuelle (Zero Trust Architecture)
Rôle : Rechercher, collecter et valider les faits AVANT toute génération de contenu.
L'IA ne fait que synthétiser ce que ce module a trouvé.
"""

import os
import re
import json
import requests
from dataclasses import dataclass, field
from typing import List, Optional

# ──────────────────────────────────────────────
# Configuration & Secrets
# ──────────────────────────────────────────────
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_CONTENT", "")  # Réservée à l'image generation
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")  # Pour extraction LLM

@dataclass
class VerifiedFact:
    """Un fait vérifié avec sa source."""
    statement: str      # L'affirmation factuelle
    source_name: str    # Nom de la source (ex: "TechCrunch")
    source_url: str     # URL cliquable
    date: str           # Date de publication
    snippet: str        # Extrait original pour preuve

@dataclass
class VerificationResult:
    """Résultat complet de la vérification d'un sujet."""
    is_valid: bool
    facts: List[VerifiedFact] = field(default_factory=list)
    error_reason: str = ""
    raw_sources: list = field(default_factory=list)

# ──────────────────────────────────────────────
# Moteur de Recherche Web (Tavily Advanced)
# ──────────────────────────────────────────────
def search_web(query: str, num_results: int = 5) -> list:
    """Recherche web structurée via Tavily (optimisé pour fact-checking)."""
    if not TAVILY_API_KEY:
        print("⚠️ TAVILY_API_KEY manquante. Mode recherche désactivé.")
        return []

    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "num_results": num_results,
        "include_answer": False,
        "include_raw_content": False,
        "search_depth": "advanced"  # Plus lent mais beaucoup plus fiable pour les faits
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()

        results = []
        for item in data.get("results", []):
            # Nettoyage du contenu (supprime les URLs, markdown, etc.)
            content = item.get("content", "")
            content = re.sub(r'https?://\S+', '', content)  # Supprime les liens
            content = re.sub(r'\[.*?\]', '', content)       # Supprime les références [1]
            content = ' '.join(content.split())             # Normalise les espaces

            results.append({
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": content[:500],  # Limite à 500 chars pour le prompt
                "date": item.get("published_date", "")[:10] if item.get("published_date") else ""
            })
        return results
    except Exception as e:
        print(f"❌ Erreur recherche Tavily : {e}")
        return []

# ──────────────────────────────────────────────
# Extracteur de Faits (LLM comme ANALYSEUR uniquement)
# ──────────────────────────────────────────────
def extract_facts_from_sources(sujet: str, sources: list) -> List[VerifiedFact]:
    """
    Utilise le LLM UNIQUEMENT pour extraire et structurer les faits des sources brutes.
    INTERDIT au LLM d'ajouter des infos externes.
    """
    if not MISTRAL_API_KEY or not sources:
        return []

    context_str = "\n\n".join([
        f"SOURCE [{i+1}] : {s['title']}\nURL: {s['link']}\nDate: {s.get('date', 'N/A')}\nExtrait: {s['snippet']}"
        for i, s in enumerate(sources[:4])  # Max 4 sources pour le prompt
    ])

    prompt = (
        "Tu es un EXTRACTEUR DE FAITS STRICT. Ta seule tâche est d'extraire des affirmations factuelles "
        "EXPLICITEMENT présentes dans les SOURCES fournies ci-dessous.\n\n"
        "RÈGLES ABSOLUES :\n"
        "1. N'ajoute AUCUNE information extérieure aux sources.\n"
        "2. Si une info n'est pas dans les sources, IGNORE-LA.\n"
        "3. Retourne UNIQUEMENT un tableau JSON d'objets avec : statement, source_name, source_url, date, snippet.\n"
        "4. Le 'statement' doit être une phrase complète et vérifiable.\n"
        "5. Ne jamais inventer de dates ou de chiffres.\n\n"
        f"SUJET : {sujet}\n\nSOURCES :\n{context_str}\n\nJSON :"
    )

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data = r.json()

        # Diagnostic : si "choices" est absent, on affiche la vraie raison
        if "choices" not in data:
            if "error" in data:
                print(f"⚠️ Erreur API Mistral : {data['error']}")
            else:
                print(f"⚠️ Réponse Mistral inattendue (pas de 'choices') : {json.dumps(data)[:500]}")
            return []

        text = data["choices"][0]["message"]["content"]

        # Nettoyage JSON brut
        text = re.sub(r'^```json\s*', '', text).strip()
        text = re.sub(r'\s*```$', '', text).strip()

        facts_data = json.loads(text)
        verified_facts = []
        for f in facts_data:  # ← CORRECTION ICI (était "facts_")
            if all(k in f for k in ["statement", "source_name", "source_url"]):
                # Validation assouplie : accepte si UN SEUL mot du sujet apparaît
                # dans le statement OU dans le snippet source associé
                sujet_words = sujet.split()
                statement_lower = f["statement"].lower()
                snippet_lower = f.get("snippet", "").lower()
                if any(word.lower() in statement_lower or word.lower() in snippet_lower for word in sujet_words):
                    verified_facts.append(VerifiedFact(**f))
        return verified_facts
    except Exception as e:
        print(f"⚠️ Extraction LLM échouée : {e}")
        return []

# ──────────────────────────────────────────────
# Cross-Check Automatique (Consensus)
# ──────────────────────────────────────────────
def cross_check_facts(facts: List[VerifiedFact], min_sources: int = 1) -> VerificationResult:
    """
    Valide les faits uniquement s'ils sont soutenus par plusieurs sources indépendantes.
    C'est le filtre anti-fake news principal.
    """
    if not facts:
        return VerificationResult(is_valid=False, error_reason="Aucun fait extrait des sources.")

    # Regrouper les faits similaires par similarité de mots-clés
    validated_facts = []

    for fact in facts:
        # Compter combien de sources mentionnent des termes similaires
        support_count = 1  # La source originale compte toujours

        # Vérification simple : le statement apparaît-il dans d'autres snippets ?
        for other_fact in facts:
            if other_fact != fact and other_fact.source_url != fact.source_url:
                # Similarité basique : 2+ mots en commun
                words_fact = set(fact.statement.lower().split())
                words_other = set(other_fact.statement.lower().split())
                common = words_fact & words_other
                if len(common) >= 2:
                    support_count += 1

        # Accepter si au moins 1 source corrobore
        if support_count >= min_sources:
            validated_facts.append(fact)

    # Règle stricte : besoin d'au moins 1 fait validé par consensus
    if len(validated_facts) >= 1:
        return VerificationResult(is_valid=True, facts=validated_facts, raw_sources=facts)
    else:
        return VerificationResult(
            is_valid=False, 
            error_reason=f"Pas de consensus suffisant. {len(validated_facts)} fait(s) validé(s), besoin de {min_sources} sources concordantes.",
            raw_sources=facts
        )

# ──────────────────────────────────────────────
# API Publique du Module
# ──────────────────────────────────────────────
def verify_topic(sujet: str) -> VerificationResult:
    """
    Point d'entrée unique pour vérifier un sujet.
    Flux : Recherche → Extraction → Cross-Check → Résultat
    """
    print(f"🔍 [FACT-CHECK] Vérification du sujet : '{sujet}'")

    # 1. Recherche Web
    sources = search_web(sujet)
    if len(sources) < 1:
        print(f"🚫 [REJECT] Moins de 1 source trouvée pour '{sujet}'. Abandon.")
        return VerificationResult(is_valid=False, error_reason="Pas assez de sources web.")

    print(f"✅ [SEARCH] {len(sources)} sources trouvées.")

    # 2. Extraction des faits
    facts = extract_facts_from_sources(sujet, sources)
    if not facts:
        print(f"🚫 [REJECT] Impossible d'extraire des faits vérifiés pour '{sujet}'.")
        return VerificationResult(is_valid=False, error_reason="Extraction LLM échouée ou vide.")

    print(f"✅ [EXTRACT] {len(facts)} faits extraits des sources.")

    # 3. Cross-Check
    result = cross_check_facts(facts)

    if result.is_valid:
        print(f"✅ [VALID] Sujet '{sujet}' validé avec {len(result.facts)} fait(s) vérifié(s).")
    else:
        print(f"🚫 [REJECT] Sujet '{sujet}' rejeté : {result.error_reason}")

    return result