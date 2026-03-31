"""
Orchestrateur de collecte — lance tous les scrapers et stocke en base.

Usage :
    python -m src.jobs.scrapers.job_collector
    python -m src.jobs.scrapers.job_collector --france   # France entière
    python -m src.jobs.scrapers.job_collector --radius 100
"""

from datetime import datetime

from loguru import logger
from sqlalchemy.orm import Session

from src.common.config import settings
from src.common.database import JobOffer, create_all_tables, engine
from src.jobs.scrapers.france_travail import FranceTravailClient


def upsert_offers(offers: list[dict], session: Session) -> tuple[int, int]:
    """
    Insère les nouvelles offres, ignore les doublons (par external_id).
    Retourne (nb_inserted, nb_skipped).
    """
    inserted = skipped = 0

    for o in offers:
        existing = session.query(JobOffer).filter_by(external_id=o["external_id"]).first()

        if existing:
            skipped += 1
            continue

        offer = JobOffer(
            external_id=o["external_id"],
            source=o["source"],
            title=o["title"],
            company=o["company"],
            location=o["location"],
            contract_type=o["contract_type"],
            salary_min=o.get("salary_min"),
            salary_max=o.get("salary_max"),
            currency=o.get("currency", "EUR"),
            description=o.get("description", ""),
            url=o.get("url", ""),
            remote=o.get("remote", False),
            tags=o.get("tags", {}),
        )
        session.add(offer)
        inserted += 1

    session.commit()
    return inserted, skipped


def collect() -> dict:
    create_all_tables()
    summary = {
        "started_at": datetime.now().isoformat(),
        "sources": {},
        "total_inserted": 0,
        "total_skipped": 0,
    }

    if settings.france_travail_client_id:
        logger.info("Démarrage collecte France Travail…")
        client = FranceTravailClient()
        raw = client.search_all_keywords()
        normalized = client.normalize_all(raw)

        EXCLUDED_KEYWORDS = {
            "alternance",
            "apprentissage",
            "stage",
            "stagiaire",
            "professionnalisation",
            "contrat pro",
        }
        normalized = [
            o
            for o in normalized
            if not any(kw in (o.get("title") or "").lower() for kw in EXCLUDED_KEYWORDS)
        ]
        logger.info(f"{len(normalized)} offres après exclusion alternances/stages")

        with Session(engine) as session:
            inserted, skipped = upsert_offers(normalized, session)

        summary["sources"]["france_travail"] = {
            "fetched": len(raw),
            "inserted": inserted,
            "skipped": skipped,
        }
        summary["total_inserted"] += inserted
        summary["total_skipped"] += skipped
        logger.success(f"France Travail : {inserted} nouvelles offres, {skipped} doublons")
    else:
        logger.warning("FRANCE_TRAVAIL_CLIENT_ID manquant dans .env")

    summary["finished_at"] = datetime.now().isoformat()
    logger.success(f"Collecte terminée : {summary['total_inserted']} nouvelles offres au total")
    return summary


if __name__ == "__main__":
    result = collect()
    print(result)
