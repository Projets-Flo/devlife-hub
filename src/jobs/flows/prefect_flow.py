"""
Flow Prefect — pipeline quotidien automatisé.

Déploiement :
    python src/jobs/flows/prefect_flow.py

Puis dans l'UI Prefect (localhost:4200) :
    → Deployments → daily-job-pipeline → Schedule → Every day at 8:00
"""

from loguru import logger
from prefect import flow, task


@task(name="clean-old-offers", retries=1)
def task_clean():
    from src.jobs.flows.daily_pipeline import clean_old_offers

    return clean_old_offers(days=60)


@task(name="collect-offers", retries=2)
def task_collect():
    from src.jobs.flows.daily_pipeline import collect_new_offers

    return collect_new_offers()


@task(name="analyze-new-offers", retries=1)
def task_analyze():
    from src.jobs.flows.daily_pipeline import analyze_new_offers

    return analyze_new_offers()


@flow(
    name="daily-job-pipeline",
    description="Collecte et analyse quotidienne des offres d'emploi",
)
def daily_pipeline():
    task_clean()
    new_offers = task_collect()
    if new_offers > 0:
        analyzed = task_analyze()
        logger.success(f"Pipeline OK : {new_offers} collectées, {analyzed} analysées")
    else:
        logger.info("Aucune nouvelle offre aujourd'hui")


if __name__ == "__main__":
    daily_pipeline.serve(
        name="default",
        cron="0 8 * * *",  # tous les jours à 8h
    )
