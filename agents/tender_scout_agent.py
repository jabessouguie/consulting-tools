"""
Agent TenderScout AI
Scrape les appels d'offres depuis BOAMP et Francemarches.com,
puis analyse chaque AO avec Gemini via LLMClient (décision GO/NO-GO/A_ETUDIER).
"""

import json
import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from utils.llm_client import LLMClient


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

BOAMP_API_URL = (
    "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
)
FRANCEMARCHES_SEARCH_URL = "https://www.francemarches.com/appels-offres/"

VALID_SOURCES = {"boamp", "francemarches"}

_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "decision": "GO | NO-GO | A_ETUDIER",
    "score": "integer entre 0 et 100",
    "resume": "string — résumé de l'appel d'offres",
    "budget_estime": "string — budget estimé ou 'Non précisé'",
    "echeance": "string — date limite de remise des offres",
    "criteres_notation": ["string — critère de notation"],
    "risques": ["string — risque identifié"],
    "atouts": ["string — atout / point fort"],
    "recommandation": "string — recommandation finale",
}

_ANALYSIS_SYSTEM_PROMPT = (
    "Tu es un expert en réponse aux appels d'offres publics pour une société de conseil. "
    "Analyse l'appel d'offres fourni et détermine si notre société doit répondre (GO), "
    "ne pas répondre (NO-GO) ou étudier davantage (A_ETUDIER). "
    "Sois précis, concis et orienté business."
)

_REQUEST_TIMEOUT = 15  # secondes


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScrapingError(Exception):
    """Erreur lors du scraping d'une source d'appels d'offres."""


class AnalysisError(Exception):
    """Erreur lors de l'analyse Gemini d'un appel d'offres."""


# ---------------------------------------------------------------------------
# TenderScoutAgent
# ---------------------------------------------------------------------------


class TenderScoutAgent:
    """Scrape BOAMP et Francemarches, analyse les AOs avec Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.llm = LLMClient(api_key=api_key, model=model)

    # ------------------------------------------------------------------
    # Scraping BOAMP
    # ------------------------------------------------------------------

    def scrape_boamp(self, keywords: List[str], limit: int = 20) -> List[dict]:
        """Scrape l'API publique BOAMP pour les mots-clés donnés.

        Args:
            keywords: Liste de mots-clés de recherche.
            limit: Nombre max d'AOs par mot-clé.

        Returns:
            Liste de dicts normalisés (reference, titre, acheteur, source,
            url, date_publication, date_limite, description).

        Raises:
            ScrapingError: En cas d'erreur HTTP ou de réponse invalide.
        """
        results: List[dict] = []
        seen_refs: set = set()

        for keyword in keywords:
            try:
                # La version 2.1 de l'API Opendatasoft utilise search() pour le plein texte
                response = requests.get(
                    BOAMP_API_URL,
                    params={
                        "where": f'search("{keyword}")',
                        "limit": limit,
                        "order_by": "-dateparution",
                    },
                    timeout=_REQUEST_TIMEOUT,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ScrapingError(
                    f"Erreur HTTP BOAMP pour '{keyword}' : {exc}"
                ) from exc

            try:
                data = response.json()
            except ValueError as exc:
                raise ScrapingError(
                    f"Réponse BOAMP non-JSON pour '{keyword}'."
                ) from exc

            for record in data.get("results", []):
                # Utilisation de id ou idweb (idweb est souvent plus stable pour les liens)
                ref = str(record.get("idweb") or record.get("id") or "")
                if not ref or ref in seen_refs:
                    continue
                seen_refs.add(ref)

                # Fonction utilitaire locale pour garantir une chaine (BOAMP renvoie parfois des listes)
                def to_str(val) -> str:
                    if val is None:
                        return ""
                    if isinstance(val, list):
                        return " ".join(str(v) for v in val if v)
                    return str(val)

                # Extraction robuste des champs
                titre = to_str(record.get("objet") or record.get("titre") or "Sans titre")
                acheteur = to_str(record.get("nomacheteur") or "")
                if not acheteur and isinstance(record.get("donnees"), dict):
                     acheteur = to_str(record.get("donnees", {}).get("PA", {}).get("denomination"))
                
                date_pub = to_str(record.get("dateparution") or "")
                date_limite = to_str(record.get("datelimitereponse") or "")
                
                # 'descripteur_libelle' est souvent une liste de tags/mots-clés
                description = to_str(record.get("descripteur_libelle") or record.get("objet") or "")
                url = f"https://www.boamp.fr/avis/detail/{ref}"

                results.append(
                    {
                        "reference": f"BOAMP-{ref}",
                        "titre": titre,
                        "acheteur": acheteur,
                        "source": "boamp",
                        "url": url,
                        "date_publication": date_pub,
                        "date_limite": date_limite,
                        "description": description,
                    }
                )

        return results

    # ------------------------------------------------------------------
    # Scraping Francemarches
    # ------------------------------------------------------------------

    def scrape_francemarches(
        self, keywords: List[str], limit: int = 20
    ) -> List[dict]:
        """Scrape Francemarches.com pour les mots-clés donnés.

        Args:
            keywords: Liste de mots-clés de recherche.
            limit: Nombre max d'AOs par mot-clé.

        Returns:
            Liste de dicts normalisés.

        Raises:
            ScrapingError: En cas d'erreur HTTP ou de parsing.
        """
        results: List[dict] = []
        seen_urls: set = set()

        for keyword in keywords:
            try:
                response = requests.get(
                    FRANCEMARCHES_SEARCH_URL,
                    params={"q": keyword, "per_page": limit},
                    timeout=_REQUEST_TIMEOUT,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (compatible; TenderScoutBot/1.0)"
                        ),
                        "Accept": "text/html,application/xhtml+xml",
                    },
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ScrapingError(
                    f"Erreur HTTP Francemarches pour '{keyword}' : {exc}"
                ) from exc

            soup = BeautifulSoup(response.text, "html.parser")

            # Chercher les cards d'appels d'offres
            cards = soup.select(".avis-list-item, .tender-card, article.post")
            if not cards:
                # Fallback: chercher des liens contenant /avis/ ou /appel-offres/
                cards = soup.select("a[href*='/avis/'], a[href*='/appel']")

            count = 0
            for card in cards:
                if count >= limit:
                    break

                # Extraire le lien
                link_tag = card if card.name == "a" else card.find("a", href=True)
                if not link_tag:
                    continue
                url = link_tag.get("href", "")
                if not url.startswith("http"):
                    url = "https://www.francemarches.com" + url
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Extraire le titre
                titre_tag = card.find(
                    ["h2", "h3", "h4", ".title", ".tender-title"]
                )
                titre = (
                    titre_tag.get_text(strip=True)
                    if titre_tag
                    else link_tag.get_text(strip=True)
                )
                if not titre:
                    titre = "Sans titre"

                # Extraire acheteur, date, description
                acheteur = ""
                date_pub = ""
                description = ""

                acheteur_tag = card.find(class_=re.compile(r"buyer|acheteur|org"))
                if acheteur_tag:
                    acheteur = acheteur_tag.get_text(strip=True)

                date_tag = card.find(["time", "span"], class_=re.compile(r"date|pub"))
                if date_tag:
                    date_pub = date_tag.get("datetime") or date_tag.get_text(strip=True)

                desc_tag = card.find(class_=re.compile(r"desc|excerpt|summary"))
                if desc_tag:
                    description = desc_tag.get_text(strip=True)

                # Référence basée sur l'URL
                ref = re.sub(r"[^a-zA-Z0-9_-]", "_", url.split("/")[-1] or url[-20:])

                results.append(
                    {
                        "reference": f"FM-{ref}",
                        "titre": titre,
                        "acheteur": acheteur,
                        "source": "francemarches",
                        "url": url,
                        "date_publication": date_pub,
                        "date_limite": "",
                        "description": description,
                    }
                )
                count += 1

        return results

    # ------------------------------------------------------------------
    # Analyse Gemini
    # ------------------------------------------------------------------

    def analyze_tender(self, tender: dict) -> dict:
        """Analyse un appel d'offres avec Gemini et retourne une décision structurée.

        Args:
            tender: Dict avec au moins titre, description, acheteur, date_limite.

        Returns:
            Dict avec decision, score, resume, budget_estime, echeance,
            criteres_notation, risques, atouts, recommandation.

        Raises:
            AnalysisError: Si LLMClient échoue ou retourne un résultat vide/invalide.
        """
        prompt = (
            f"Appel d'offres à analyser :\n\n"
            f"Titre : {tender.get('titre', 'N/A')}\n"
            f"Acheteur : {tender.get('acheteur', 'N/A')}\n"
            f"Source : {tender.get('source', 'N/A')}\n"
            f"Date de publication : {tender.get('date_publication', 'N/A')}\n"
            f"Date limite : {tender.get('date_limite', 'N/A')}\n"
            f"Description : {tender.get('description', 'N/A')}\n\n"
            "Analyse cet appel d'offres et fournis ta recommandation."
        )

        try:
            result = self.llm.extract_structured_data(
                prompt=prompt,
                output_schema=_ANALYSIS_SCHEMA,
                system_prompt=_ANALYSIS_SYSTEM_PROMPT,
            )
        except Exception as exc:
            raise AnalysisError(
                f"Erreur LLM lors de l'analyse : {exc}"
            ) from exc

        if not result or not isinstance(result, dict):
            raise AnalysisError(
                "L'analyse Gemini a retourné un résultat vide ou invalide."
            )

        # Normaliser la décision
        decision = str(result.get("decision", "")).upper().strip()
        if decision not in {"GO", "NO-GO", "A_ETUDIER"}:
            decision = "A_ETUDIER"
        result["decision"] = decision

        # Normaliser le score
        try:
            result["score"] = int(result.get("score", 0))
        except (ValueError, TypeError):
            result["score"] = 0

        return result
