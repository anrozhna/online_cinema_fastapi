from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import CurrentUser, get_db, get_jwt_auth_manager, get_settings
from config.settings import BaseAppSettings
from database.models.accounts import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
)
from exceptions.security import BaseSecurityError
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
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
from security.interfaces import JWTAuthManagerInterface
from security.utils import generate_secure_token

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    path="/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Register a new user with an email and password.",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User registered successfully."},
        409: {"description": "User with this email already exists."},
        500: {"description": "An error occurred during user creation."},
    },
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    db: DB,
):
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with this email {user_data.email} already exists.",
        )

    stmt_group = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
    result_group = await db.execute(stmt_group)
    user_group = result_group.scalar()

    try:
        new_user = User.create(
            email=user_data.email,
            raw_password=user_data.password,
            group_id=user_group.id,
        )

        db.add(new_user)
        await db.flush()

        activation_token = ActivationToken(user_id=new_user.id)
        db.add(activation_token)

        await db.commit()
        await db.refresh(new_user)

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation.",
        )

    return new_user


@router.post(
    path="/activate/",
    response_model=MessageResponseSchema,
    summary="Activate user account",
    description="Activate a user's account using their email and activation token.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "The user's account was successfully activated."},
        400: {
            "description": "Activation token is invalid or expired, "
            "or account is already active."
        },
    },
)
async def activate_account(
    activation_data: UserActivationRequestSchema,
    db: DB,
):
    stmt = (
        select(ActivationToken)
        .options(joinedload(ActivationToken.user))
        .join(User)
        .where(
            User.email == activation_data.email,
            ActivationToken.token == activation_data.token,
        )
    )
    result = await db.execute(stmt)
    activation_token = result.scalars().first()

    if not activation_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    expires_at = activation_token.expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        await db.delete(activation_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired activation token.",
        )

    user = activation_token.user
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active.",
        )

    user.is_active = True
    await db.delete(activation_token)
    await db.commit()

    return MessageResponseSchema(message="User account activated successfully.")


@router.post(
    path="/activate/resend-link/",
    response_model=MessageResponseSchema,
    summary="Resend activation email",
    description="Resend the activation email to a user's email address.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "The activation email was successfully resent."},
        404: {"description": "User is not found."},
    },
)
async def resend_activation_link(
    request_data: UserActivationResendRequestSchema,
    db: DB,
):
    stmt = (
        select(User)
        .options(joinedload(User.activation_token))
        .where(User.email == request_data.email)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    generic_response = MessageResponseSchema(
        message="If the account exists and is not active, "
        "a new activation link has been sent."
    )

    if not user or user.is_active:
        return generic_response

    if user.activation_token:
        await db.delete(user.activation_token)
        await db.flush()

    new_token = ActivationToken(
        user_id=user.id,
        token=generate_secure_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(new_token)
    await db.commit()

    # TODO(feature/accounts-notifications): replace with celery-task
    # send_activation_email_task.delay(user.email, new_token.token)

    return generic_response


@router.post(
    path="/login/",
    response_model=UserLoginResponseSchema,
    summary="Login a user",
    description="Authenticate a user and return access and refresh tokens.",
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Invalid email or password."},
        403: {"description": "User account is not activated."},
        500: {"description": "An error occurred while processing the request."},
    },
)
async def login(
    login_data: UserLoginRequestSchema,
    db: DB,
    settings: BaseAppSettings = Depends(get_settings),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    stmt = select(User).where(User.email == login_data.email)
    result = await db.execute(stmt)
    user = result.scalar()

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

    access_token = jwt_manager.create_access_token({"user_id": user.id})
    refresh_token = jwt_manager.create_refresh_token({"user_id": user.id})

    try:
        refresh_token_record = RefreshToken.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=refresh_token,
        )
        db.add(refresh_token_record)
        await db.commit()

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request.",
        )

    return UserLoginResponseSchema(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post(
    path="/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh access token",
    description="Refresh access token using refresh token",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Access token successfully refreshed."},
        400: {"description": "The provided refresh token is invalid or expired."},
        401: {
            "description": "The provided refresh token does not exist in the database."
        },
        404: {
            "description": "The user associated with the refresh token does not exist."
        },
    },
)
async def accounts_refresh(
    token_data: TokenRefreshRequestSchema,
    db: DB,
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
):
    try:
        decoded_refresh_token = jwt_manager.decode_refresh_token(
            token_data.refresh_token
        )
    except BaseSecurityError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))

    user_id = decoded_refresh_token.get("user_id")

    stmt = select(RefreshToken).where(RefreshToken.token == token_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token = result.scalar()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found."
        )

    stmt_user = select(User).where(User.id == user_id)
    result = await db.execute(stmt_user)
    user = result.scalar()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    new_access_token = jwt_manager.create_access_token({"user_id": user.id})

    return TokenRefreshResponseSchema(access_token=new_access_token)


@router.post(
    path="/logout/",
    response_model=MessageResponseSchema,
    summary="Logout",
    description="Logout the user by invalidating the refresh token.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "User logged out successfully.",
        },
        401: {
            "description": "Invalid refresh token.",
        },
    },
)
async def logout(
    logout_data: LogoutRequestSchema,
    db: DB,
):
    stmt = select(RefreshToken).where(RefreshToken.token == logout_data.refresh_token)
    result = await db.execute(stmt)
    refresh_token = result.scalar()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token."
        )

    await db.delete(refresh_token)
    await db.commit()

    return MessageResponseSchema(message="User logged out successfully.")


@router.post(
    path="/change-password/",
    response_model=MessageResponseSchema,
    summary="Change password",
    description="Change the password for the currently authenticated user.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Password changed successfully.",
        },
        401: {
            "description": "Invalid or missing access token, or wrong old password.",
        },
        422: {
            "description": "New password does not meet strength requirements, "
            "or matches the old password."
        },
    },
)
async def change_password(
    password_data: PasswordChangeRequestSchema,
    db: DB,
    current_user: CurrentUser,
):
    if not current_user.verify_password(raw_password=password_data.old_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong old password."
        )

    if current_user.verify_password(raw_password=password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="New password must be different from the old password.",
        )

    try:
        current_user.password = password_data.new_password
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    await db.commit()

    return MessageResponseSchema(message="Password changed successfully.")


@router.post(
    path="/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description=(
        "Allows a user to request a password reset token. "
        "If the user exists and is active, a new token will be generated "
        "and any existing tokens will be invalidated."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "The request was successful. This response is always "
            "returned regardless of the user's existence or status."
        },
    },
)
async def request_password_reset_token(
    data: PasswordResetRequestSchema,
    db: DB,
):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar()

    success_message = MessageResponseSchema(
        message="If you are registered, you will receive an email with instructions."
    )

    if not user or not user.is_active:
        return success_message

    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )

    reset_token = PasswordResetToken(user_id=user.id)
    db.add(reset_token)
    await db.commit()

    # TODO(feature/accounts-notifications): replace with celery-task
    # reset_link = (
    #     f"http://127.0.0.1/accounts/password-reset/complete/"
    #     f"?email={user.email}&token={reset_token.token}"
    # )
    #
    # background_tasks.add_task(
    #     email_sender.send_password_reset_email, str(data.email), reset_link
    # )

    return success_message


@router.post(
    path="/reset-password/complete/",
    response_model=MessageResponseSchema,
    summary="Complete Password Reset",
    description="Reset a user's password if a valid token is provided.",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Password reset successfully."},
        400: {
            "description": "The provided email, token, or password is invalid, "
            "or the token has expired."
        },
        500: {
            "description": "An unexpected error occurred while resetting the password."
        },
    },
)
async def reset_password(
    data: PasswordResetCompleteRequestSchema,
    db: DB,
):
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or token."
        )

    stmt_token = select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    result = await db.execute(stmt_token)
    reset_token = result.scalar()

    if reset_token is None or reset_token.token != data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    expires_at = reset_token.expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or token.",
        )

    try:
        user.password = data.password
        await db.delete(reset_token)
        await db.commit()

    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
        )

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting the password.",
        )

    # TODO(feature/accounts-notifications): replace with celery-task
    # login_link = "http://127.0.0.1/accounts/login/"
    #
    # background_tasks.add_task(
    #     email_sender.send_password_reset_complete_email, str(data.email), login_link
    # )

    return MessageResponseSchema(message="Password reset successfully.")
