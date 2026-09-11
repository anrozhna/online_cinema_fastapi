import asyncio

from celery import shared_task

from config.dependencies import get_accounts_email_notificator
from config.settings import Settings


@shared_task(name="notifications.send_activation_email_task")
def send_activation_email_task(email: str, activation_link: str) -> None:
    settings = Settings()
    email_sender = get_accounts_email_notificator(settings)

    asyncio.run(
        email_sender.send_activation_email(email=email, activation_link=activation_link)
    )
