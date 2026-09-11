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


@shared_task(name="notifications.send_activation_complete_email_task")
def send_activation_complete_email_task(email: str, login_link: str) -> None:
    settings = Settings()
    email_sender = get_accounts_email_notificator(settings)

    asyncio.run(
        email_sender.send_activation_complete_email(email=email, login_link=login_link)
    )


@shared_task(name="notifications.send_password_reset_email_task")
def send_password_reset_email_task(email: str, reset_link: str) -> None:
    settings = Settings()
    email_sender = get_accounts_email_notificator(settings)

    asyncio.run(
        email_sender.send_password_reset_email(email=email, reset_link=reset_link)
    )


@shared_task(name="notifications.send_password_reset_complete_email_task")
def send_password_reset_complete_email_task(email: str, login_link: str) -> None:
    settings = Settings()
    email_sender = get_accounts_email_notificator(settings)

    asyncio.run(
        email_sender.send_password_reset_complete_email(
            email=email, login_link=login_link
        )
    )
