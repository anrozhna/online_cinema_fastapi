from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from config.dependencies import (
    ActivationTokenRepo,
    JWTManager,
    PasswordResetTokenRepo,
    ProfileRepo,
    RefreshTokenRepo,
    UserGroupRepo,
    UserRepo,
)
from config.settings import GetSettings
from database.models.accounts import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
    UserProfile,
)
from exceptions.security import BaseSecurityError
from notifications.tasks import (
    send_activation_complete_email_task,
    send_activation_email_task,
    send_password_reset_complete_email_task,
    send_password_reset_email_task,
)
from schemas.accounts import (
    LogoutRequestSchema,
    MessageResponseSchema,
    PasswordChangeRequestSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserActivationRequestSchema,
    UserActivationResendRequestSchema,
    UserGroupUpdateRequestSchema,
    UserGroupUpdateResponseSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
)


class AccountsService:
    def __init__(
        self,
        settings: GetSettings,
        jwt_manager: JWTManager,
        user_repo: UserRepo,
        user_group_repo: UserGroupRepo,
        activation_token_repo: ActivationTokenRepo,
        password_reset_token_repo: PasswordResetTokenRepo,
        refresh_token_repo: RefreshTokenRepo,
        profile_repo: ProfileRepo,
    ):
        self.settings = settings
        self.jwt_manager = jwt_manager
        self.user_repo = user_repo
        self.user_group_repo = user_group_repo
        self.activation_token_repo = activation_token_repo
        self.password_reset_token_repo = password_reset_token_repo
        self.refresh_token_repo = refresh_token_repo
        self.profile_repo = profile_repo
        # db needed for commit/rollback and flush — repositories own the queries
        self.db = user_repo.db

    @staticmethod
    def raise_404_if_user_is_none_or_not_active(user: User | None) -> None:
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or not active.",
            )

    async def commit_or_raise_500(self, error_detail: str) -> None:
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail,
            )

    async def commit_and_refresh_or_raise_500(
        self, instance, error_detail: str
    ) -> None:
        """Commit, then refresh `instance` from the DB;
        rollback and raise 500 on failure.

        Consolidates the "commit -> refresh" pair previously duplicated
        between register_user and change_user_group.
        """
        await self.commit_or_raise_500(error_detail)
        await self.db.refresh(instance)

    @staticmethod
    def is_token_expired(token) -> bool:
        """Works for any token model exposing an `expires_at` datetime column."""
        expires_at = token.expires_at.replace(tzinfo=timezone.utc)
        return expires_at < datetime.now(timezone.utc)

    async def raise_400_if_token_expired(self, token, error_detail: str) -> None:
        """Delete an expired token and raise 400. No-op if the token is still valid.

        Consolidates the "check expiry -> delete -> commit -> raise" sequence
        previously duplicated between activate_account (ActivationToken) and
        reset_password (PasswordResetToken).
        """
        if self.is_token_expired(token):
            await self.db.delete(token)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail
            )

    def _send_activation_email(self, email: str, token: str) -> None:
        """Consolidates the activation-link template previously duplicated
        between register_user and resend_activation_link."""
        activation_link = (
            f"{self.settings.SITE_URL}/accounts/activate/"
            f"?email={email}&token={token}"
        )
        send_activation_email_task.delay(str(email), activation_link)

    def _send_activation_complete_email(self, email: str) -> None:
        login_link = f"{self.settings.SITE_URL}/accounts/login/"
        send_activation_complete_email_task.delay(str(email), login_link)

    def _send_password_reset_complete_email(self, email: str) -> None:
        """Consolidates the login-link template previously duplicated
        between activate_account and reset_password."""
        login_link = f"{self.settings.SITE_URL}/accounts/login/"
        send_password_reset_complete_email_task.delay(
            email=email, login_link=login_link
        )

    async def _get_or_raise_user_group(self, group_name: UserGroupEnum) -> UserGroup:
        user_group = await self.user_group_repo.get_by_name(group_name)
        if user_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Requested user group is not configured.",
            )
        return user_group

    async def register_user(self, user_data: UserRegistrationRequestSchema) -> User:
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with this email {user_data.email} already exists.",
            )

        user_group = await self._get_or_raise_user_group(UserGroupEnum.USER)

        new_user = User.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        self.user_repo.add(new_user)
        await self.db.flush()

        activation_token = ActivationToken(user_id=new_user.id)
        self.activation_token_repo.add(activation_token)
        self.profile_repo.add(UserProfile(user_id=new_user.id))

        await self.commit_and_refresh_or_raise_500(
            new_user, "An error occurred during user creation."
        )

        self._send_activation_email(new_user.email, activation_token.token)

        return new_user

    async def activate_account(
        self, activation_data: UserActivationRequestSchema
    ) -> MessageResponseSchema:
        activation_token = await self.activation_token_repo.get_by_email_and_token(
            activation_data.email, activation_data.token
        )
        if not activation_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired activation token.",
            )

        await self.raise_400_if_token_expired(
            activation_token, "Invalid or expired activation token."
        )

        user = activation_token.user  # eager-loaded via joinedload in the repository
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active.",
            )

        user.is_active = True
        await self.activation_token_repo.delete(activation_token)
        await self.db.commit()

        self._send_activation_complete_email(activation_data.email)

        return MessageResponseSchema(message="User account activated successfully.")

    async def resend_activation_link(
        self, request_data: UserActivationResendRequestSchema
    ) -> MessageResponseSchema:
        user = await self.user_repo.get_by_email(request_data.email)

        generic_response = MessageResponseSchema(
            message="If the account exists and is not active, "
            "a new activation link has been sent."
        )

        if not user or user.is_active:
            return generic_response

        existing = await self.activation_token_repo.get_by_user_id(user.id)
        if existing:
            await self.activation_token_repo.delete(existing)
            await self.db.flush()

        new_token = ActivationToken(user_id=user.id)
        self.activation_token_repo.add(new_token)
        await self.db.commit()

        self._send_activation_email(user.email, new_token.token)

        return generic_response

    async def login(
        self, login_data: UserLoginRequestSchema
    ) -> UserLoginResponseSchema:
        user = await self.user_repo.get_by_email(login_data.email)
        if not user or not user.verify_password(raw_password=login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not activated.",
            )

        access_token = self.jwt_manager.create_access_token({"user_id": user.id})
        refresh_token = self.jwt_manager.create_refresh_token({"user_id": user.id})

        refresh_token_record = RefreshToken.create(
            user_id=user.id,
            days_valid=self.settings.LOGIN_TIME_DAYS,
            raw_token=refresh_token,
        )
        self.refresh_token_repo.add(refresh_token_record)
        await self.commit_or_raise_500(
            "An error occurred while processing the request."
        )

        return UserLoginResponseSchema(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    async def refresh_access_token(
        self, token_data: TokenRefreshRequestSchema
    ) -> TokenRefreshResponseSchema:
        try:
            decoded_refresh_token = self.jwt_manager.decode_refresh_token(
                token_data.refresh_token
            )
        except BaseSecurityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
            )

        user_id = decoded_refresh_token.get("user_id")

        refresh_token = await self.refresh_token_repo.get_by_raw_token(
            token_data.refresh_token
        )
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        if not user_id or user_id != refresh_token.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token."
            )

        user = await self.user_repo.get_by_id(refresh_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        new_access_token = self.jwt_manager.create_access_token({"user_id": user.id})
        return TokenRefreshResponseSchema(access_token=new_access_token)

    async def logout(self, logout_data: LogoutRequestSchema) -> MessageResponseSchema:
        refresh_token = await self.refresh_token_repo.get_by_raw_token(
            logout_data.refresh_token
        )
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        await self.refresh_token_repo.delete(refresh_token)
        await self.db.commit()

        return MessageResponseSchema(message="User logged out successfully.")

    async def change_password(
        self, current_user: User, password_data: PasswordChangeRequestSchema
    ) -> MessageResponseSchema:
        if not current_user.verify_password(raw_password=password_data.old_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong old password."
            )

        if current_user.verify_password(raw_password=password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="New password must be different from the old password.",
            )

        current_user.password = password_data.new_password
        await self.commit_or_raise_500("An error occurred while changing the password.")

        return MessageResponseSchema(message="Password changed successfully.")

    async def request_password_reset_token(
        self, data: PasswordResetRequestSchema
    ) -> MessageResponseSchema:
        user = await self.user_repo.get_by_email(data.email)

        success_message = MessageResponseSchema(
            message="If you are registered, "
            "you will receive an email with instructions."
        )

        if not user or not user.is_active:
            return success_message

        await self.password_reset_token_repo.delete_all_for_user(user.id)
        reset_token = PasswordResetToken(user_id=user.id)
        self.password_reset_token_repo.add(reset_token)
        await self.db.commit()

        reset_link = (
            f"{self.settings.SITE_URL}/accounts/password-reset/complete/"
            f"?email={user.email}&token={reset_token.token}"
        )
        send_password_reset_email_task.delay(email=user.email, reset_link=reset_link)

        return success_message

    async def reset_password(
        self, data: PasswordResetCompleteRequestSchema
    ) -> MessageResponseSchema:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or token.",
            )

        reset_token = await self.password_reset_token_repo.get_by_user_id(user.id)
        if reset_token is None or reset_token.token != data.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or token.",
            )

        await self.raise_400_if_token_expired(reset_token, "Invalid email or token.")

        user.password = data.password
        await self.password_reset_token_repo.delete(reset_token)
        await self.commit_or_raise_500(
            "An error occurred while resetting the password."
        )

        self._send_password_reset_complete_email(user.email)

        return MessageResponseSchema(message="Password reset successfully.")

    async def change_user_group(
        self, user_id: int, group_data: UserGroupUpdateRequestSchema
    ) -> UserGroupUpdateResponseSchema:
        user = await self.user_repo.get_by_id(user_id)
        self.raise_404_if_user_is_none_or_not_active(user)
        assert user is not None

        user_group = await self._get_or_raise_user_group(group_data.group)

        user.group_id = user_group.id
        await self.commit_and_refresh_or_raise_500(
            user, "An error occurred while updating the user group."
        )

        return UserGroupUpdateResponseSchema(
            user_id=user.id, email=user.email, group=group_data.group
        )

    async def activate_user_manually(self, user_id: int) -> MessageResponseSchema:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active.",
            )

        user.is_active = True

        activation_token = await self.activation_token_repo.get_by_user_id(user_id)
        if activation_token:
            await self.activation_token_repo.delete(activation_token)

        await self.commit_or_raise_500("An error occurred while activating the user.")

        return MessageResponseSchema(message="User account activated successfully.")


AccountServiceDep = Annotated[AccountsService, Depends()]
