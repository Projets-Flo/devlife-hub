"""
Analyseur LLM local via Ollama — analyse approfondie des offres d'emploi.
Utilise Mistral 7B en local, 100% gratuit et offline.

Prérequis :
    1. Installer Ollama : https://ollama.com
    2. ollama pull mistral
    3. ollama serve (ou lancer Ollama Desktop)

Usage :
    from src.jobs.matching.llm_analyzer import JobAnalyzer
    analyzer = JobAnalyzer()
    result = analyzer.analyze(title="Data Scientist", description="...", location="Paris")
"""

import json
import re
import time

import httpx
from loguru import logger

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral"

# Profil de Florian — injecté dans le prompt pour le matching personnalisé
FLORIAN_PROFILE = """
Profil candidat :
- Diplôme : Ingénieur Polytech Lyon, Mathématiques Appliquées & Modélisation (2025)
- Expérience 1 : Caisses Sociales de Monaco — Data Analyst/Scientist (6 mois)
  Compétences : XGBoost, Random Forest, clustering séries temporelles, tests statistiques,
  pandas, scikit-learn, SQL, détection fraudes, données médico-administratives
- Expérience 2 : Babolat — Chargé de missions data et digitales (6 mois)
  Compétences : Power BI, Tableau, Looker Studio, Google Analytics 4,
  ContentSquare (expert), automatisation reportings, e-commerce
- Compétences techniques : Python, R, SQL, SAS, C/C++, Matlab, Git,
  pandas, scikit-learn, XGBoost, PyTorch, PySpark, TensorFlow,
  Power BI, Tableau, Looker Studio, BO Web Intelligence
- Compétences stats : régressions Lasso/Ridge, ARIMA, Monte-Carlo,
  tests d'hypothèses, modèles bayésiens, K-means, SVM
- Langues : Français (natif), Anglais (courant), Allemand (bon niveau)
- Localisation : Saint-Julien-en-Genevois (proche Genève)
- Disponibilité : immédiate
"""

ANALYSIS_PROMPT = """Tu es un expert en recrutement data science. Analyse cette offre d'emploi et retourne UNIQUEMENT un JSON valide, sans aucun texte avant ou après.

OFFRE :
Titre : {title}
Localisation : {location}
Entreprise : {company}
Contrat : {contract_type}
Description : {description}

PROFIL CANDIDAT :
{profile}

Retourne exactement ce JSON (tous les champs obligatoires) :
{{
  "resume": "Résumé de l'offre en 2 phrases max",
  "poste_type": "junior|confirmé|senior",
  "culture_entreprise": "startup|scale-up|grand groupe|ESN/conseil|laboratoire/recherche|PME|inconnu",
  "domaine_metier": "data science|machine learning|data engineering|data analyst|bi analytics|biostatistique|simulation|mlops|autre",
  "experience_requise_ans": 0,
  "competences_requises": {{
    "indispensables": ["liste des compétences vraiment requises"],
    "souhaitees": ["liste des compétences appréciées mais pas obligatoires"]
  }},
  "stack_principale": ["les 5 technos les plus importantes du poste"],
  "salaire_estime": {{
    "min": 0,
    "max": 0,
    "base": "extrait|estimé",
    "note": "Explication courte de l'estimation"
  }},
  "remote": "full remote|hybride|présentiel|non précisé",
  "score_adequation": 0,
  "score_justification": "Pourquoi ce score (2-3 phrases)",
  "points_forts_candidature": ["Ce qui joue en faveur du candidat pour ce poste"],
  "competences_manquantes": ["Compétences du poste absentes du profil candidat"],
  "conseil_candidature": "Un conseil personnalisé et concret pour postuler à ce poste"
}}

Pour le score_adequation (0-100) : base-toi sur la correspondance entre le profil candidat et les exigences du poste.
Pour le salaire_estime : si non indiqué, estime en fonction du poste, niveau, localisation et marché FR/CH actuel.
IMPORTANT : retourne UNIQUEMENT le JSON, rien d'autre."""


class JobAnalyzer:
    """Analyse les offres d'emploi avec un LLM local via Ollama."""

    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = 120):
        self.model = model
        self.timeout = timeout
        self._check_ollama()

    def _check_ollama(self) -> bool:
        """Vérifie qu'Ollama est disponible."""
        try:
            resp = httpx.get("http://localhost:11434/api/tags", timeout=5)
            models = [m["name"] for m in resp.json().get("models", [])]
            if not any(self.model in m for m in models):
                logger.warning(
                    f"Modèle '{self.model}' non trouvé. " f"Lance : ollama pull {self.model}"
                )
                return False
            logger.info(f"Ollama OK — modèle {self.model} disponible")
            return True
        except Exception:
            logger.warning("Ollama non disponible. Lance Ollama Desktop ou 'ollama serve'")
            return False

    def analyze(
        self,
        title: str,
        description: str,
        location: str = "",
        company: str = "",
        contract_type: str = "",
    ) -> dict | None:
        """
        Analyse une offre d'emploi et retourne un dict structuré.
        Retourne None si Ollama n'est pas disponible.
        """
        prompt = ANALYSIS_PROMPT.format(
            title=title,
            description=description[:3000],  # limite tokens
            location=location,
            company=company,
            contract_type=contract_type,
            profile=FLORIAN_PROFILE,
        )

        try:
            response = httpx.post(
                OLLAMA_URL,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # déterministe pour JSON
                        "num_predict": 1024,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            raw_text = response.json().get("response", "")
            return self._parse_json(raw_text)

        except httpx.TimeoutException:
            logger.warning(f"Timeout pour '{title}' — offre ignorée")
            return None
        except Exception as e:
            logger.error(f"Erreur analyse '{title}' : {e}")
            return None

    def _parse_json(self, text: str) -> dict | None:
        """Extrait et parse le JSON depuis la réponse du LLM."""
        # Cherche un bloc JSON dans la réponse
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            logger.warning("Pas de JSON trouvé dans la réponse LLM")
            return None
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON invalide : {e}")
            # Tentative de nettoyage
            cleaned = re.sub(r",\s*}", "}", json_match.group())
            cleaned = re.sub(r",\s*]", "]", cleaned)
            try:
                return json.loads(cleaned)
            except Exception:
                return None


def analyze_all_offers(batch_size: int = 10, max_offers: int = None) -> int:
    """
    Lance l'analyse LLM sur toutes les offres non encore analysées.
    Sauvegarde les résultats dans le champ `tags` de chaque offre.

    Args:
        batch_size: Commit toutes les N offres (évite de tout perdre si crash)
        max_offers: Limite le nombre d'offres à analyser (None = toutes)
    """
    from sqlalchemy.orm import Session

    from src.common.database import JobOffer, engine

    analyzer = JobAnalyzer()
    analyzed = 0
    errors = 0

    with Session(engine) as session:
        query = session.query(JobOffer)
        if max_offers:
            query = query.limit(max_offers)
        offers = query.all()

        # Filtre celles déjà analysées
        to_analyze = [o for o in offers if not (o.tags or {}).get("llm_analyzed")]

        logger.info(f"{len(to_analyze)} offres à analyser sur {len(offers)} total")

        for i, offer in enumerate(to_analyze, 1):
            logger.info(f"[{i}/{len(to_analyze)}] {offer.title} — {offer.company}")

            result = analyzer.analyze(
                title=offer.title or "",
                description=offer.description or "",
                location=offer.location or "",
                company=offer.company or "",
                contract_type=offer.contract_type or "",
            )

            if result:
                tags = offer.tags or {}
                tags["llm_analysis"] = result
                tags["llm_analyzed"] = True
                tags["llm_model"] = analyzer.model
                offer.tags = tags

                # Met à jour le score de matching directement sur l'objet
                score = result.get("score_adequation")
                if score is not None:
                    offer.match_score = float(score)

                analyzed += 1
            else:
                errors += 1

            # Commit par batch
            if i % batch_size == 0:
                session.commit()
                logger.info(f"Checkpoint : {analyzed} analysées, {errors} erreurs")

            time.sleep(0.1)  # respiration

        session.commit()

    logger.success(f"Analyse terminée : {analyzed} offres analysées, {errors} erreurs")
    return analyzed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=None, help="Nombre max d'offres")
    parser.add_argument("--model", type=str, default="mistral", help="Modèle Ollama")
    args = parser.parse_args()

    analyze_all_offers(max_offers=args.max)
