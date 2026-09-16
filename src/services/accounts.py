from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from config.dependencies import DataBase, GetSettings, JWTManager
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
        db: DataBase,
        settings: GetSettings,
        jwt_manager: JWTManager,
    ):
        self.db = db
        self.settings = settings
        self.jwt_manager = jwt_manager

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def raise_404_if_user_is_none_or_not_active(user: User | None) -> None:
        """Guarantee the given user exists and is active, or raise 404."""
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or not active.",
            )

    async def get_user_group_by_name_or_500(
        self, group_name: UserGroupEnum
    ) -> UserGroup | None:
        stmt = select(UserGroup).where(UserGroup.name == group_name)
        result = await self.db.execute(stmt)
        user_group = result.scalar_one_or_none()
        if user_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Requested user group is not configured.",
            )
        return user_group

    async def get_default_user_group(self) -> UserGroup | None:
        return await self.get_user_group_by_name_or_500(UserGroupEnum.USER)

    async def get_activation_token_by_user_id(
        self, user_id: int
    ) -> ActivationToken | None:
        stmt = select(ActivationToken).where(ActivationToken.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_password_reset_token_by_user_id(
        self, user_id: int
    ) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_refresh_token_or_401(self, token: str) -> RefreshToken:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.db.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )
        return refresh_token

    async def commit_or_raise_500(self, error_detail: str) -> None:
        """Commit the current transaction; on failure,
        rollback and raise a clean 500."""
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail,
            )

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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail,
            )

    async def replace_activation_token(self, user_id: int) -> ActivationToken:
        existing = await self.get_activation_token_by_user_id(user_id)
        if existing:
            await self.db.delete(existing)
            await self.db.flush()
        new_token = ActivationToken(user_id=user_id)
        self.db.add(new_token)
        return new_token

    async def replace_password_reset_token(self, user_id: int) -> PasswordResetToken:
        await self.db.execute(
            delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        new_token = PasswordResetToken(user_id=user_id)
        self.db.add(new_token)
        return new_token

    async def register_user(self, user_data: UserRegistrationRequestSchema) -> User:
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with this email {user_data.email} already exists.",
            )

        user_group = await self.get_default_user_group()
        assert user_group is not None

        new_user = User.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id,
        )
        self.db.add(new_user)
        await self.db.flush()

        activation_token = ActivationToken(user_id=new_user.id)
        self.db.add(activation_token)
        self.db.add(UserProfile(user_id=new_user.id))

        await self.commit_or_raise_500("An error occurred during user creation.")
        await self.db.refresh(new_user)

        activation_link = (
            f"{self.settings.SITE_URL}/accounts/activate/"
            f"?email={new_user.email}&token={activation_token.token}"
        )
        send_activation_email_task.delay(str(user_data.email), activation_link)

        return new_user

    async def activate_account(
        self, activation_data: UserActivationRequestSchema
    ) -> MessageResponseSchema:
        stmt = (
            select(ActivationToken)
            .options(joinedload(ActivationToken.user))
            .join(User)
            .where(
                User.email == activation_data.email,
                ActivationToken.token == activation_data.token,
            )
        )
        result = await self.db.execute(stmt)
        activation_token = result.scalars().first()

        if not activation_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired activation token.",
            )

        await self.raise_400_if_token_expired(
            activation_token, "Invalid or expired activation token."
        )

        user = activation_token.user
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active.",
            )

        user.is_active = True
        await self.db.delete(activation_token)
        await self.db.commit()

        login_link = f"{self.settings.SITE_URL}/accounts/login/"
        send_activation_complete_email_task.delay(
            str(activation_data.email), login_link
        )

        return MessageResponseSchema(message="User account activated successfully.")

    async def resend_activation_link(
        self, request_data: UserActivationResendRequestSchema
    ) -> MessageResponseSchema:
        user = await self.get_user_by_email(request_data.email)

        generic_response = MessageResponseSchema(
            message="If the account exists and is not active, "
            "a new activation link has been sent."
        )

        if not user or user.is_active:
            return generic_response

        new_token = await self.replace_activation_token(user.id)
        await self.db.commit()

        activation_link = (
            f"{self.settings.SITE_URL}/accounts/activate/"
            f"?email={user.email}&token={new_token.token}"
        )
        send_activation_email_task.delay(str(request_data.email), activation_link)

        return generic_response

    async def login(
        self, login_data: UserLoginRequestSchema
    ) -> UserLoginResponseSchema:
        user = await self.get_user_by_email(login_data.email)
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
            token=refresh_token,
        )
        self.db.add(refresh_token_record)
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
        refresh_token = await self.get_refresh_token_or_401(token_data.refresh_token)

        if not user_id or user_id != refresh_token.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refresh token."
            )

        user = await self.get_user_by_id(refresh_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        new_access_token = self.jwt_manager.create_access_token({"user_id": user.id})
        return TokenRefreshResponseSchema(access_token=new_access_token)

    async def logout(self, logout_data: LogoutRequestSchema) -> MessageResponseSchema:
        refresh_token = await self.get_refresh_token_or_401(logout_data.refresh_token)

        await self.db.delete(refresh_token)
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
        user = await self.get_user_by_email(data.email)

        success_message = MessageResponseSchema(
            message="If you are registered, "
            "you will receive an email with instructions."
        )

        if not user or not user.is_active:
            return success_message

        reset_token = await self.replace_password_reset_token(user.id)
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
        user = await self.get_user_by_email(data.email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or token.",
            )

        reset_token = await self.get_password_reset_token_by_user_id(user.id)
        if reset_token is None or reset_token.token != data.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email or token.",
            )

        await self.raise_400_if_token_expired(reset_token, "Invalid email or token.")

        user.password = data.password
        await self.db.delete(reset_token)
        await self.commit_or_raise_500(
            "An error occurred while resetting the password."
        )

        login_link = f"{self.settings.SITE_URL}/accounts/login/"
        send_password_reset_complete_email_task.delay(
            email=user.email, login_link=login_link
        )

        return MessageResponseSchema(message="Password reset successfully.")

    async def change_user_group(
        self, user_id: int, group_data: UserGroupUpdateRequestSchema
    ) -> UserGroupUpdateResponseSchema:
        user = await self.get_user_by_id(user_id)
        self.raise_404_if_user_is_none_or_not_active(user)
        assert user is not None

        user_group = await self.get_user_group_by_name_or_500(group_data.group)
        assert user_group is not None

        user.group_id = user_group.id
        await self.commit_or_raise_500(
            "An error occurred while updating the user group."
        )
        await self.db.refresh(user)

        return UserGroupUpdateResponseSchema(
            user_id=user.id, email=user.email, group=group_data.group
        )

    async def activate_user_manually(self, user_id: int) -> MessageResponseSchema:
        user = await self.get_user_by_id(user_id)
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

        activation_token = await self.get_activation_token_by_user_id(user_id)
        if activation_token:
            await self.db.delete(activation_token)

        await self.commit_or_raise_500("An error occurred while activating the user.")

        return MessageResponseSchema(message="User account activated successfully.")


AccountServiceDep = Annotated[AccountsService, Depends()]
