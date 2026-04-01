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

import copy
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
- Diplôme : Ingénieur Polytech Lyon, Mathématiques Appliquées & Modélisation (diplôme déjà obtenu en octobre 2025)
- Expérience 1 : Caisses Sociales de Monaco — Data Analyst/Scientist (stage de fin d'études, 6 mois)
  Compétences : XGBoost, Random Forest, clustering séries temporelles, tests statistiques robustes,
  pandas, scikit-learn, SQL, détection de fraudes, données médico-administratives
- Expérience 2 : Babolat, Lyon — Chargé de missions data et digitales (stage, 6 mois)
  Compétences : Power BI, Tableau, Looker Studio, Google Analytics 4,
  ContentSquare (niveau expert), automatisation de reportings, e-commerce
- Compétences techniques : Très bon niveau en Python, en R et en SQL, SAS, C/C++, Matlab, Git,
  pandas, scikit-learn, XGBoost, PyTorch, PySpark, TensorFlow,
  Power BI, Tableau, Looker Studio, BO Web Intelligence
- Compétences statistiques : régressions Lasso/Ridge, ARIMA, Monte-Carlo,
  tests d'hypothèses, modèles bayésiens, K-means, SVM
- Langues : Français (natif), Anglais (courant), Allemand (bon niveau)
- Mobilité : ouvert à une relocalisation partout en France
- Disponibilité : immédiate
- Contexte : jeune diplômé cherchant son premier emploi, avec 2 stages significatifs
"""

ANALYSIS_PROMPT = """Tu es un expert senior en recrutement data science/data analyst/data enginner/machine learning en France. Analyse cette offre d'emploi et retourne UNIQUEMENT un JSON valide en français, sans aucun texte avant ou après.

OFFRE :
Titre : {title}
Localisation : {location}
Entreprise : {company}
Contrat : {contract_type}
Description : {description}

PROFIL CANDIDAT :
{profile}

Retourne exactement ce JSON (tous les champs obligatoires, toutes les valeurs textuelles en français) :
{{
  "resume": "Résumé clair et concis de l'offre en 2-3 phrases",
  "poste_type": "Junior|Confirmé|Senior",
  "culture_entreprise": "Startup|Scale-up|Grand groupe|ESN/conseil|Laboratoire/recherche|PME|Inconnu",
  "domaine_metier": "Data Science|Machine Learning|Data Engineering|Data analyst|Bi analytics|Biostatistique|Simulation|MLOps|Autre",
  "type_missions": "Technique/Développement|Analyse/Reporting|Conseil/Client|Recherche/R&D|Mixte",
  "experience_requise_ans": 0,
  "competences_requises": {{
    "indispensables": ["compétences vraiment requises pour le poste"],
    "souhaitees": ["compétences appréciées mais pas bloquantes"]
  }},
  "stack_principale": ["les 5 technos/outils les plus importants du poste"],
  "salaire_estime": {{
    "min": 0,
    "max": 0,
    "base": "extrait|estimé",
    "note": "Courte explication de l'estimation ou de la source"
  }},
  "remote": "Full remote|Hybride|Présentiel|Non précisé",
  "score_adequation": 0,
  "score_justification": "Explication précise du score en 2-3 phrases, en mentionnant les éléments clés qui ont influencé la note",
  "points_forts_candidature": ["Points forts concrets du profil candidat pour CE poste spécifique"],
  "faiblesses_candidature": ["Faiblesses ou manques concrets du profil pour CE poste, par exemple vis à vis de l'expérience requise, des compétences techniques, .., soyez honnête, "],
  "competences_manquantes": ["Compétences demandées dans l'offre absentes du profil candidat"],
  "probabilite_succes": 0,
  "probabilite_succes_note": "Explication de la probabilité : concurrence estimée, niveau requis vs profil, contexte marché",
  "urgence_candidature": "Haute|Moyenne|Faible",
  "urgence_note": "Explication : indices d'urgence dans l'offre (poste clé, délai, croissance entreprise...)",
  "conseil_candidature": "Conseil personnalisé, concret et actionnable pour maximiser les chances sur CE poste précis"
}}

Règles importantes :
- Toutes les valeurs textuelles DOIVENT être en français
- Le score_adequation (0-100) mesure la correspondance profil/poste
- La probabilite_succes (0-100) estime les chances réelles d'être retenu, en tenant compte de la concurrence et du niveau junior du candidat
- Pour le salaire_estime : si non mentionné, estime selon le poste, niveau, localisation et marché FR actuel (fourchette réaliste)
- Sois honnête et nuancé, pas trop optimiste
- Dans les points forts/faiblesses, mentionne des éléments concrets de l'offre et du profil, pas des généralités
- Dans les atouts, fais référence à des atouts utiles pour ce poste précis, pas des atouts que j'ai mais qui ne sont pas forcément pertinents pour ce poste
- Globalement dans l'analyse de l'offre, sois très concret et spécifique à CE poste précis, pas de généralités ou de conseils vagues qui pourraient s'appliquer à n'importe quelle offre.
- Dans le conseil, parle de ce qui pourrait vraiment faire la différence pour CE poste précis, pas des conseils génériques
- Dans le conseil, parle moi directemnent à la première personne du singulier ("je te conseille de...") pour que ce soit plus personnalisé
- RETOURNE UNIQUEMENT LE JSON, rien d'autre"""


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
    from sqlalchemy.orm.attributes import flag_modified

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
                tags = copy.deepcopy(offer.tags or {})
                tags["llm_analysis"] = result
                tags["llm_analyzed"] = True
                tags["llm_model"] = analyzer.model
                offer.tags = tags
                flag_modified(offer, "tags")

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
