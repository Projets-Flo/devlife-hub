"""
Connecteur France Travail (ex Pôle Emploi) — API officielle v2.
Recherche sur toute la France, sans filtre géographique.

Docs : https://francetravail.io/data/api/offres-emploi
"""

import hashlib
import time
from datetime import datetime

import httpx
from loguru import logger

from src.common.config import settings

AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

DEFAULT_KEYWORDS = [
    "data scientist",
    "machine learning engineer",
    "data analyst",
    "biostatisticien",
    "MLops",
    "statisticien",
    "ingenieur simulation",
]


class FranceTravailClient:
    def __init__(self):
        self.client_id = settings.france_travail_client_id
        self.client_secret = settings.france_travail_client_secret
        self._token: str | None = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        response = httpx.post(
            AUTH_URL,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": SCOPE,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]
        logger.info("Token France Travail obtenu")
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/json",
        }

    def search(
        self,
        keywords: str,
        published_since_days: int = 31,
        max_results: int = 150,
    ) -> list[dict]:
        """
        Recherche des offres sur toute la France sans filtre géographique.
        """
        params = {
            "motsCles": keywords,
            "publieeDepuis": published_since_days,
            "sort": "1",
        }

        headers = {
            **self._headers(),
            "Range": f"offres=0-{min(max_results - 1, 149)}",
        }

        try:
            response = httpx.get(
                SEARCH_URL,
                headers=headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 204:
                logger.info(f"Aucune offre pour '{keywords}'")
                return []

            response.raise_for_status()
            data = response.json()
            offres = data.get("resultats", [])
            logger.info(f"{len(offres)} offres trouvées pour '{keywords}'")
            return offres

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Erreur API {e.response.status_code} pour '{keywords}' : "
                f"{e.response.text[:300]}"
            )
            return []
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            return []

    def search_all_keywords(self) -> list[dict]:
        """Lance une recherche pour tous les mots-clés et déduplique."""
        all_results = []
        seen_ids = set()

        for keyword in DEFAULT_KEYWORDS:
            results = self.search(keywords=keyword)
            for offre in results:
                offre_id = offre.get("id")
                if offre_id and offre_id not in seen_ids:
                    seen_ids.add(offre_id)
                    all_results.append(offre)
            time.sleep(0.5)

        logger.success(f"{len(all_results)} offres uniques collectées au total")
        return all_results

    def normalize(self, raw: dict) -> dict:
        """Convertit une offre brute en format interne standardisé."""
        salary = raw.get("salaire", {})
        salary_min = salary_max = None
        if salary.get("libelle"):
            parts = salary["libelle"].replace("Euros", "").replace("euros", "")
            numbers = [
                float(p.strip())
                for p in parts.split()
                if p.strip().replace(".", "").replace(",", "").isdigit()
            ]
            if len(numbers) >= 2:
                salary_min, salary_max = numbers[0], numbers[1]
            elif len(numbers) == 1:
                salary_min = numbers[0]

        description = raw.get("description", "")
        remote = any(w in description.lower() for w in ["télétravail", "remote", "full remote"])

        competences = [c.get("libelle", "") for c in raw.get("competences", [])]

        hash_key = hashlib.md5(
            f"{raw.get('intitule', '')}{raw.get('entreprise', {}).get('nom', '')}".encode()
        ).hexdigest()

        return {
            "external_id": f"ft_{raw.get('id', hash_key)}",
            "source": "france_travail",
            "title": raw.get("intitule", ""),
            "company": raw.get("entreprise", {}).get("nom", "Entreprise confidentielle"),
            "location": raw.get("lieuTravail", {}).get("libelle", ""),
            "contract_type": raw.get("typeContratLibelle", ""),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "currency": "EUR",
            "description": description,
            "url": raw.get("origineOffre", {}).get("urlOrigine", ""),
            "remote": remote,
            "tags": {
                "competences": competences,
                "experience": raw.get("experienceLibelle", ""),
                "secteur": raw.get("secteurActiviteLibelle", ""),
            },
            "scraped_at": datetime.now().isoformat(),
        }

    def normalize_all(self, raw_offres: list[dict]) -> list[dict]:
        return [self.normalize(o) for o in raw_offres]
