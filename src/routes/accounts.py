from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_db
from database.models.accounts import ActivationToken, User, UserGroup, UserGroupEnum
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)

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
