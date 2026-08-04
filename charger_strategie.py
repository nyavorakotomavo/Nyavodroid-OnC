"""
charger_strategie.py — Module de chargement de la stratégie NAnaly pour Nyavodroid.
Lit STRATEGIE_JSON (env var), valide, et retourne un objet Strategie.
Fallback sécurisé si absente ou invalide.
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

@dataclass
class StrategieMetadata:
    posts_analyses_page: int = 0
    engagement_moyen_page: float = 0.0
    concurrents_surveilles: int = 0
    requetes_api_utilisees: int = 0
    date_generation: Optional[str] = None

@dataclass
class Strategie:
    meilleure_heure: Optional[int] = None
    format_prefere: Optional[str] = None
    longueur_texte_optimale: int = 200
    mots_cles_tendance: list[str] = field(default_factory=list)
    sujets_a_explorer: list[str] = field(default_factory=list)
    source: str = "valeurs_par_defaut"
    metadata: StrategieMetadata = field(default_factory=StrategieMetadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

STRATEGIE_PAR_DEFAUT = Strategie(
    meilleure_heure=None,
    format_prefere=None,
    longueur_texte_optimale=200,
    mots_cles_tendance=[],
    sujets_a_explorer=[],
    source="valeurs_par_defaut",
    metadata=StrategieMetadata()
)

VALID_FORMATS = {"photo", "video", "texte_seul", "carousel", "reel", "story", "image_texte"}

class StrategieValidationError(Exception):
    pass

def _validate_heure(heure: Any) -> Optional[int]:
    if heure is None:
        return None
    try:
        h = int(heure)
        return h if 0 <= h <= 23 else None
    except (TypeError, ValueError):
        return None

def _validate_format(fmt: Any) -> Optional[str]:
    if not isinstance(fmt, str):
        return None
    f = fmt.lower()
    return f if f in VALID_FORMATS else None

def _validate_liste(valeur: Any) -> list[str]:
    if not isinstance(valeur, list):
        return []
    return [str(item).strip() for item in valeur if isinstance(item, str) and str(item).strip()]

def _build_metadata(raw: Any) -> StrategieMetadata:
    if not isinstance(raw, dict):
        return StrategieMetadata()
    return StrategieMetadata(
        posts_analyses_page=int(raw.get("posts_analyses_page", 0)),
        engagement_moyen_page=float(raw.get("engagement_moyen_page", 0.0)),
        concurrents_surveilles=int(raw.get("concurrents_surveilles", 0)),
        requetes_api_utilisees=int(raw.get("requetes_api_utilisees", 0)),
        date_generation=raw.get("date_generation")
    )

def charger_strategie() -> Strategie:
    """Charge la stratégie depuis STRATEGIE_JSON ou retourne les valeurs par défaut."""
    brute = os.environ.get("STRATEGIE_JSON", "")
    if not brute or not brute.strip():
        logger.info("📭 Aucune stratégie reçue → valeurs par défaut")
        return STRATEGIE_PAR_DEFAUT

    try:
        data = json.loads(brute)
        if not isinstance(data, dict):
            raise StrategieValidationError("Payload non-dict")

        defaults = STRATEGIE_PAR_DEFAUT.to_dict()
        for k, v in defaults.items():
            data.setdefault(k, v)

        strategie = Strategie(
            meilleure_heure=_validate_heure(data.get("meilleure_heure")),
            format_prefere=_validate_format(data.get("format_prefere")),
            longueur_texte_optimale=int(data.get("longueur_texte_optimale", 200)),
            mots_cles_tendance=_validate_liste(data.get("mots_cles_tendance", [])),
            sujets_a_explorer=_validate_liste(data.get("sujets_a_explorer", [])),
            source=data.get("source", "NAnaly"),
            metadata=_build_metadata(data.get("metadata"))
        )
        logger.info(f"✅ Stratégie NAnaly chargée : {strategie.meilleure_heure}h, {strategie.format_prefere}, "
                    f"{len(strategie.mots_cles_tendance)} mots-clés, {len(strategie.sujets_a_explorer)} sujets")
        return strategie

    except Exception as e:
        logger.error(f"⚠️ Stratégie invalide ({e}) → valeurs par défaut")
        return STRATEGIE_PAR_DEFAUT

if __name__ == "__main__":
    s = charger_strategie()
    print(json.dumps(s.to_dict(), indent=2, ensure_ascii=False))