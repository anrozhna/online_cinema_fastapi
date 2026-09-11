from celery import Celery

from config.dependencies import get_settings

settings = get_settings()

celery_app = Celery(
    "online_cinema",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(["database"])
