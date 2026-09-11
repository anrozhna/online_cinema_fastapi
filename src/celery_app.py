from celery import Celery
from celery.schedules import crontab

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
    beat_schedule={
        "clear-expired-tokens-every-midnight": {
            "task": "notifications.delete_expired_tokens_task",
            "schedule": crontab(hour=0, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["notifications"])
