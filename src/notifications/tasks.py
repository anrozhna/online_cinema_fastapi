import asyncio
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.dependencies import get_accounts_email_notificator
from config.settings import Settings
from database.models.accounts import ActivationToken, PasswordResetToken


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


@shared_task(name="notifications.delete_expired_tokens_task")
def delete_expired_tokens_task() -> str:
    """Periodic task to delete expired tokens from the database."""
    settings = Settings()

    async def _delete_tokens():
        engine = create_async_engine(settings.database_url)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

        async with session_factory() as db:
            now = datetime.now(timezone.utc)

            stmt_activation = delete(ActivationToken).where(
                ActivationToken.expires_at < now
            )
            stmt_password = delete(PasswordResetToken).where(
                PasswordResetToken.expires_at < now
            )

            res_act = await db.execute(stmt_activation)
            res_pwd = await db.execute(stmt_password)
            await db.commit()
            await engine.dispose()

            return (
                f"Deleted expired tokens: activation ({res_act.rowcount}), "
                f"password ({res_pwd.rowcount})"
            )

    return asyncio.run(_delete_tokens())
