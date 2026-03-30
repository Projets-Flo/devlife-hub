"""
Extracteur de compétences et métadonnées depuis les descriptions d'offres.
Approche par règles : dictionnaire de compétences + regex expérience.
Gratuit, instantané, fonctionne hors ligne.
"""

import re

from loguru import logger

# ── Dictionnaire de compétences ───────────────────────────────────────────────

SKILLS = {
    "langages": [
        "python",
        "r",
        "sql",
        "scala",
        "julia",
        "matlab",
        "sas",
        "java",
        "c++",
        "javascript",
        "typescript",
        "bash",
        "spark",
        "pyspark",
    ],
    "ml_ia": [
        "machine learning",
        "deep learning",
        "nlp",
        "computer vision",
        "xgboost",
        "lightgbm",
        "random forest",
        "sklearn",
        "scikit-learn",
        "tensorflow",
        "keras",
        "pytorch",
        "hugging face",
        "transformers",
        "llm",
        "rag",
        "reinforcement learning",
        "time series",
        "prophet",
        "arima",
        "regression",
        "classification",
        "clustering",
        "neural network",
        "gradient boosting",
    ],
    "data_engineering": [
        "pandas",
        "numpy",
        "polars",
        "dbt",
        "airflow",
        "prefect",
        "luigi",
        "kafka",
        "spark",
        "hadoop",
        "hive",
        "databricks",
        "snowflake",
        "bigquery",
        "redshift",
        "etl",
        "pipeline",
        "datalake",
        "datawarehouse",
    ],
    "cloud": [
        "aws",
        "gcp",
        "azure",
        "s3",
        "ec2",
        "lambda",
        "cloud run",
        "docker",
        "kubernetes",
        "terraform",
        "mlflow",
        "dvc",
        "mlops",
        "ci/cd",
        "github actions",
        "fastapi",
        "api rest",
    ],
    "bi_analytics": [
        "power bi",
        "tableau",
        "looker",
        "metabase",
        "grafana",
        "google analytics",
        "contentsquare",
        "amplitude",
        "excel",
        "google sheets",
    ],
    "statistiques": [
        "statistiques",
        "probabilités",
        "bayésien",
        "tests hypothèses",
        "monte carlo",
        "simulation",
        "modélisation",
        "inférence",
        "biostatistique",
        "épidémiologie",
        "analyse survie",
    ],
    "bases_de_donnees": [
        "postgresql",
        "mysql",
        "mongodb",
        "elasticsearch",
        "redis",
        "sqlite",
        "oracle",
        "sql server",
    ],
}

# Liste à plat pour la recherche rapide
ALL_SKILLS = {skill: category for category, skills in SKILLS.items() for skill in skills}

# ── Patterns expérience ───────────────────────────────────────────────────────

EXPERIENCE_PATTERNS = [
    (r"sans\s+exp[eé]rience|d[eé]butant|junior|[eé]tudiant|stage|alternance", "junior"),
    (r"1\s*[àa]\s*2\s*ans?|moins\s+de\s+2\s*ans?|1\s*an", "junior"),
    (r"2\s*[àa]\s*4\s*ans?|[23]\s*ans?\s+d.exp[eé]rience", "confirmé"),
    (r"3\s*[àa]\s*5\s*ans?|exp[eé]riment[eé]|confirm[eé]", "confirmé"),
    (r"5\s*ans?\s+et\s+plus|plus\s+de\s+5\s*ans?|senior|[56789]\s*ans?\s+d.exp", "senior"),
    (r"exp[eé]rience\s+significative|expert", "senior"),
]

# ── Patterns salaire ──────────────────────────────────────────────────────────

SALARY_PATTERNS = [
    r"(\d{2,3}[\s.,]?\d{0,3})\s*[k€]\s*[àa/-]\s*(\d{2,3}[\s.,]?\d{0,3})\s*[k€]",
    r"entre\s+(\d{2,3}[\s.,]?\d{0,3})\s*€?\s*et\s+(\d{2,3}[\s.,]?\d{0,3})\s*€?",
    r"(\d{2,3}[\s.,]?\d{0,3})\s*€?\s*brut",
    r"salaire\s*:\s*(\d{2,3}[\s.,]?\d{0,3})",
]


class JobExtractor:
    """Extrait compétences, expérience et salaire depuis une description d'offre."""

    def extract(self, title: str, description: str) -> dict:
        """
        Analyse complète d'une offre.
        Retourne un dict structuré avec toutes les métadonnées extraites.
        """
        text = f"{title} {description}".lower()

        return {
            "skills": self._extract_skills(text),
            "experience_level": self._extract_experience(text),
            "salary_range": self._extract_salary(description),
            "remote_type": self._extract_remote(text),
            "keywords": self._extract_keywords(title),
        }

    def _extract_skills(self, text: str) -> dict:
        """Retourne les compétences trouvées groupées par catégorie."""
        found: dict[str, list[str]] = {}
        for skill, category in ALL_SKILLS.items():
            if re.search(r"\b" + re.escape(skill) + r"\b", text):
                found.setdefault(category, []).append(skill)
        return found

    def _extract_experience(self, text: str) -> str:
        """Retourne le niveau : junior / confirmé / senior / non précisé."""
        for pattern, level in EXPERIENCE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return level
        return "non précisé"

    def _extract_salary(self, text: str) -> dict | None:
        """Tente d'extraire une fourchette salariale."""
        for pattern in SALARY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    nums = [
                        float(g.replace(" ", "").replace(",", ".").replace("k", "000"))
                        for g in groups
                        if g
                    ]
                    # Normalise en salaire annuel (si < 200 → c'est en k€)
                    nums = [n * 1000 if n < 200 else n for n in nums]
                    if len(nums) == 2:
                        return {"min": nums[0], "max": nums[1]}
                    elif len(nums) == 1:
                        return {"min": nums[0], "max": None}
                except ValueError:
                    continue
        return None

    def _extract_remote(self, text: str) -> str:
        """Détecte le type de télétravail."""
        if re.search(r"full\s*remote|100%\s*t[eé]l[eé]travail|entièrement\s+à\s+distance", text):
            return "full remote"
        if re.search(
            r"t[eé]l[eé]travail\s+partiel|hybrid|hybride|\d+\s*jour.?\s+de\s+t[eé]l[eé]", text
        ):
            return "hybride"
        if re.search(r"t[eé]l[eé]travail|remote", text):
            return "remote possible"
        return "présentiel"

    def _extract_keywords(self, title: str) -> list[str]:
        """Extrait les mots-clés du titre pour le matching rapide."""
        stopwords = {
            "de",
            "du",
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "et",
            "en",
            "pour",
            "avec",
            "sur",
            "au",
            "aux",
            "h/f",
            "f/h",
        }
        words = re.findall(r"\b\w{3,}\b", title.lower())
        return [w for w in words if w not in stopwords]


def enrich_all_offers() -> int:
    """
    Lance l'extraction sur toutes les offres en base qui n'ont pas encore
    de compétences extraites. Met à jour le champ `tags`.
    """
    from sqlalchemy.orm import Session

    from src.common.database import JobOffer, engine

    extractor = JobExtractor()

    with Session(engine) as session:
        # Offres sans extraction (tags vide ou sans clé 'skills')
        offers = session.query(JobOffer).all()
        updated = 0

        for offer in offers:
            tags = offer.tags or {}
            if "skills" in tags:
                continue  # déjà enrichi

            extracted = extractor.extract(
                title=offer.title or "",
                description=offer.description or "",
            )

            # Merge avec les tags existants
            tags.update(extracted)
            offer.tags = tags
            updated += 1

        session.commit()

    logger.success(f"{updated} offres enrichies avec extraction de compétences")
    return updated


if __name__ == "__main__":
    enrich_all_offers()
