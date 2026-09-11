from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.settings import TestingSettings
from notifications.emails import EmailSender
from notifications.tasks import (
    delete_expired_tokens_task,
    send_activation_complete_email_task,
    send_activation_email_task,
    send_password_reset_complete_email_task,
    send_password_reset_email_task,
)
from src.celery_app import celery_app


class TestCeleryTasks:
    """Group of unit tests for verifying Celery background notification tasks."""

    @pytest.fixture(autouse=True)
    def setup_celery_eager_mode(self):
        """Switch Celery to synchronous mode for this test class."""
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        yield
        celery_app.conf.task_always_eager = False

    @patch("notifications.tasks.get_accounts_email_notificator")
    def test_send_activation_email_task(self, mock_get_notificator):
        """Verify send_activation_email_task triggers the email sender correctly."""
        mock_email_sender = AsyncMock()
        mock_get_notificator.return_value = mock_email_sender

        send_activation_email_task("test@cinema.com", "http://test/activate")

        mock_get_notificator.assert_called_once()
        mock_email_sender.send_activation_email.assert_called_once_with(
            email="test@cinema.com", activation_link="http://test/activate"
        )

    @patch("notifications.tasks.get_accounts_email_notificator")
    def test_send_activation_complete_email_task(self, mock_get_notificator):
        """Verify send_activation_complete_email_task triggers the success email."""
        mock_email_sender = AsyncMock()
        mock_get_notificator.return_value = mock_email_sender

        send_activation_complete_email_task("test@cinema.com", "http://test/login")

        mock_get_notificator.assert_called_once()
        mock_email_sender.send_activation_complete_email.assert_called_once_with(
            email="test@cinema.com", login_link="http://test/login"
        )

    @patch("notifications.tasks.get_accounts_email_notificator")
    def test_send_password_reset_email_task(self, mock_get_notificator):
        """Verify send_password_reset_email_task triggers reset link email."""
        mock_email_sender = AsyncMock()
        mock_get_notificator.return_value = mock_email_sender

        send_password_reset_email_task("test@cinema.com", "http://test/reset")

        mock_get_notificator.assert_called_once()
        mock_email_sender.send_password_reset_email.assert_called_once_with(
            email="test@cinema.com", reset_link="http://test/reset"
        )

    @patch("notifications.tasks.get_accounts_email_notificator")
    def test_send_password_reset_complete_email_task(self, mock_get_notificator):
        """Verify send_password_reset_complete_email_task triggers
        success confirmation."""
        mock_email_sender = AsyncMock()
        mock_get_notificator.return_value = mock_email_sender

        send_password_reset_complete_email_task("test@cinema.com", "http://test/login")

        mock_get_notificator.assert_called_once()
        mock_email_sender.send_password_reset_complete_email.assert_called_once_with(
            email="test@cinema.com", login_link="http://test/login"
        )


class TestEmailSenderWorkflow:
    """Group of unit tests for verifying Jinja2 rendering
    and SMTP mechanics in EmailSender."""

    @pytest.fixture
    def email_sender(self):
        """Create a real instance of EmailSender configured with testing settings."""
        settings = TestingSettings()
        return EmailSender(
            hostname="localhost",
            port=1025,
            email="test@cinema.com",
            password="password",
            use_tls=False,
            template_dir=str(settings.BASE_DIR / "notifications" / "templates"),
            activation_email_template_name="activation_request.html",
            activation_complete_email_template_name="activation_complete.html",
            password_email_template_name="password_reset_request.html",
            password_complete_email_template_name="password_reset_complete.html",
        )

    @patch("aiosmtplib.SMTP")
    @pytest.mark.asyncio
    async def test_send_activation_email_html_rendering(
        self, mock_smtp_class, email_sender
    ):
        """Verify that activation email correctly renders
        and executes the full SMTP pipeline."""
        mock_smtp_instance = AsyncMock()
        mock_smtp_class.return_value = mock_smtp_instance

        await email_sender.send_activation_email(
            email="user@example.com", activation_link="http://test/activate?token=123"
        )

        mock_smtp_class.assert_called_once()
        mock_smtp_instance.connect.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("test@cinema.com", "password")
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()

    @patch("aiosmtplib.SMTP")
    @pytest.mark.asyncio
    async def test_send_password_reset_email_html_rendering(
        self, mock_smtp_class, email_sender
    ):
        """Verify that password reset email correctly renders
        and executes the full SMTP pipeline."""
        mock_smtp_instance = AsyncMock()
        mock_smtp_class.return_value = mock_smtp_instance

        await email_sender.send_password_reset_email(
            email="user@example.com", reset_link="http://test/reset?token=abc"
        )

        mock_smtp_class.assert_called_once()
        mock_smtp_instance.connect.assert_called_once()
        mock_smtp_instance.sendmail.assert_called_once()


class TestPeriodicTasks:
    """Group of unit tests for verifying Celery Beat periodic background tasks."""

    @patch("notifications.tasks.create_async_engine")
    @patch("notifications.tasks.async_sessionmaker")
    def test_delete_expired_tokens_task_execution(
        self, mock_sessionmaker, mock_create_engine
    ):
        """
        Verify that delete_expired_tokens_task executes database delete statements.

        Ensures that the task initializes an async engine, creates a session,
        executes DELETE commands for both activation and password tokens,
        commits changes, and disposes of the connection properly.
        """
        mock_db_session = AsyncMock()

        mock_result_activation = MagicMock(rowcount=5)
        mock_result_password = MagicMock(rowcount=3)
        mock_db_session.execute.side_effect = [
            mock_result_activation,
            mock_result_password,
        ]

        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        mock_sessionmaker.return_value = MagicMock(return_value=mock_session_context)

        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        result = delete_expired_tokens_task()

        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once_with(
            bind=mock_engine, expire_on_commit=False
        )
        mock_engine.dispose.assert_called_once()

        assert mock_db_session.execute.call_count == 2
        mock_db_session.commit.assert_called_once()

        assert result == "Deleted expired tokens: activation (5), password (3)"
