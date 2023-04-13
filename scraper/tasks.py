from .celery_app import scraper_sa_aqar
from .scraper import Scraper


@scraper_sa_aqar.task(name='collect_photos')
def collect_photos(
        filter_name: str,
        category_id: int,
        city_id: int,
) -> None:
    scraper = Scraper(
        filter_name=filter_name,
        category_id=category_id,
        city_id=city_id,
    )
    scraper.collect_photos()
