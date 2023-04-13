from celery import Celery
from config import CELERY_BROKER_URL


scraper_sa_aqar = Celery(
    'scraper_sa_aqar',
    broker=CELERY_BROKER_URL,
)
scraper_sa_aqar.autodiscover_tasks()
import scraper.tasks
