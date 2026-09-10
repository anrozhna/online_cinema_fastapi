from datetime import datetime, timedelta, timezone
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config.dependencies import get_db
from database.models.accounts import ActivationToken, User, UserGroup, UserGroupEnum
from schemas.accounts import (
    MessageResponseSchema,
    UserActivationRequestSchema,
    UserActivationResendRequestSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
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

        activation_token = ActivationToken(user_id=cast(int, new_user.id))
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

    expires_at = cast(datetime, activation_token.expires_at).replace(
        tzinfo=timezone.utc
    )

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
        .join(ActivationToken)
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
