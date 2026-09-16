from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from config.settings import GetSettings, Settings, get_settings
from database.models.accounts import User, UserGroupEnum
from database.session import DataBase
from exceptions.security import BaseSecurityError
from notifications.emails import EmailSender
from notifications.interfaces import EmailSenderInterface
from repositories import (
    ActivationTokenRepository,
    PasswordResetTokenRepository,
    ProfileRepository,
    RefreshTokenRepository,
    UserGroupRepository,
    UserRepository,
)
from security.interfaces import JWTAuthManagerInterface
from security.token_manager import JWTAuthManager
from storages.interfaces import S3StorageInterface
from storages.s3 import S3StorageClient


def get_jwt_auth_manager(
    settings: Settings = Depends(get_settings),
) -> JWTAuthManagerInterface:
    """FastAPI dependency that builds a JWTAuthManager from current settings."""
    return JWTAuthManager(
        secret_key_access=settings.SECRET_KEY_ACCESS,
        secret_key_refresh=settings.SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


JWTManager = Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)]


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/accounts/login/")


async def get_current_user(
    db: DataBase,
    jwt_manager: JWTManager,
    token: str = Depends(oauth2_scheme),
) -> User:
    """Resolve the currently authenticated user from a bearer access token."""
    try:
        payload = jwt_manager.decode_access_token(token)
    except BaseSecurityError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_accounts_email_notificator(
    settings: GetSettings,
) -> EmailSenderInterface:
    """
    Retrieve an instance of the EmailSenderInterface configured with the application settings.

    This function creates an EmailSender using the provided settings, which include details such as the email host,
    port, credentials, TLS usage, and the directory and filenames for email templates. This allows the application
    to send various email notifications (e.g., activation, password reset) as required.

    Args:
        settings (BaseAppSettings, optional): The application settings,
        provided via dependency injection from `get_settings`.

    Returns:
        EmailSenderInterface: An instance of EmailSender configured with the appropriate email settings.
    """
    return EmailSender(
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        email=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME,
    )


AccountsNotifier = Annotated[
    EmailSenderInterface, Depends(get_accounts_email_notificator)
]


def get_s3_storage(settings: Settings = Depends(get_settings)) -> S3StorageInterface:
    return S3StorageClient(settings=settings)


S3Storage = Annotated[S3StorageInterface, Depends(get_s3_storage)]


def verify_profile_owner(user_id: int, current_user: CurrentUser) -> int:
    """FastAPI dependency to ensure the current user owns the profile being modified."""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )
    return user_id


def require_admin(current_user: CurrentUser) -> User:
    """FastAPI dependency to restrict an endpoint to users in the ADMIN group."""
    if not current_user.has_group(UserGroupEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


UserRepo = Annotated[UserRepository, Depends()]
UserGroupRepo = Annotated[UserGroupRepository, Depends()]
ActivationTokenRepo = Annotated[ActivationTokenRepository, Depends()]
PasswordResetTokenRepo = Annotated[PasswordResetTokenRepository, Depends()]
RefreshTokenRepo = Annotated[RefreshTokenRepository, Depends()]
ProfileRepo = Annotated[ProfileRepository, Depends()]
