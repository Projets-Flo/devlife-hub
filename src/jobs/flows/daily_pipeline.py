"""
Pipeline quotidien — collecte + analyse LLM des nouvelles offres uniquement.

Lancement manuel :
    python -m src.jobs.flows.daily_pipeline

Lancement automatique via Prefect :
    prefect deployment run daily-job-pipeline/default
"""

from datetime import datetime

from loguru import logger


def collect_new_offers() -> int:
    """Collecte les nouvelles offres et retourne le nombre insérées."""
    from src.jobs.scrapers.job_collector import collect

    result = collect()
    inserted = result.get("total_inserted", 0)
    logger.info(f"Collecte : {inserted} nouvelles offres")
    return inserted


def analyze_new_offers() -> int:
    """Lance l'analyse LLM uniquement sur les offres non encore analysées."""
    import copy
    import time

    from sqlalchemy.orm import Session
    from sqlalchemy.orm.attributes import flag_modified

    from src.common.database import JobOffer, engine
    from src.jobs.matching.llm_analyzer import JobAnalyzer

    analyzer = JobAnalyzer()

    with Session(engine) as session:
        # Uniquement les offres sans analyse LLM
        to_analyze = [
            o for o in session.query(JobOffer).all() if not (o.tags or {}).get("llm_analyzed")
        ]

        if not to_analyze:
            logger.info("Aucune nouvelle offre à analyser")
            return 0

        logger.info(f"{len(to_analyze)} nouvelles offres à analyser")
        analyzed = 0
        errors = 0

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
                score = result.get("score_adequation")
                if score is not None:
                    offer.match_score = float(score)
                analyzed += 1
            else:
                errors += 1

            if i % 10 == 0:
                session.commit()
                logger.info(f"Checkpoint : {analyzed} analysées, {errors} erreurs")

            time.sleep(0.1)

        session.commit()

    logger.success(f"Analyse terminée : {analyzed} nouvelles offres traitées, {errors} erreurs")
    return analyzed


def clean_old_offers(days: int = 60) -> int:
    """Supprime les offres de plus de N jours."""
    from datetime import timedelta

    from sqlalchemy.orm import Session

    from src.common.database import JobOffer, engine

    cutoff = datetime.now() - timedelta(days=days)
    with Session(engine) as session:
        old = session.query(JobOffer).filter(JobOffer.scraped_at < cutoff).all()
        count = len(old)
        for o in old:
            session.delete(o)
        session.commit()

    if count:
        logger.info(f"{count} offres de plus de {days} jours supprimées")
    return count


def run_pipeline():
    """Pipeline complet : nettoyage → collecte → analyse."""
    logger.info("=" * 50)
    logger.info(f"Démarrage pipeline — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info("=" * 50)

    # 1. Nettoyage des vieilles offres
    clean_old_offers(days=60)

    # 2. Collecte des nouvelles offres
    new_offers = collect_new_offers()

    # 3. Analyse LLM uniquement sur les nouvelles
    if new_offers > 0:
        logger.info(f"Lancement analyse LLM sur {new_offers} nouvelles offres…")
        analyze_new_offers()
    else:
        logger.info("Pas de nouvelles offres — analyse LLM ignorée")

    logger.success("Pipeline terminé")


if __name__ == "__main__":
    run_pipeline()
