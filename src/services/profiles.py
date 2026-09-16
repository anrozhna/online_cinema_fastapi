from typing import Annotated

from fastapi import Depends, HTTPException, status
from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from config.dependencies import DataBase, S3Storage
from database.models.accounts import User, UserProfile
from exceptions.storage import BaseS3Error
from schemas.profiles import UserProfileRequestSchema, UserProfileResponseSchema


class ProfileService:
    def __init__(self, db: DataBase, storage: S3Storage):
        self.db = db
        self.storage = storage

    async def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
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

    @staticmethod
    def raise_404_if_profile_is_none(profile: UserProfile | None) -> None:
        """Guarantee the given profile exists or raise 404."""
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found.",
            )

    @staticmethod
    def update_profile_fields(
        profile: UserProfile, profile_data: UserProfileRequestSchema
    ) -> None:
        """Map text fields from Pydantic schema to the SQLAlchemy model instance."""
        update_data = profile_data.model_dump(exclude_unset=True, exclude={"avatar"})
        for field, value in update_data.items():
            setattr(profile, field, value)

    async def handle_avatar_upload(
        self, user_id: int, profile: UserProfile, avatar_file
    ) -> None:
        """Process file extension, trigger async offloaded S3 upload,
        and map string URL."""
        file_extension = (
            (avatar_file.filename or "avatar.png").rsplit(".", 1)[-1].lower()
        )
        object_key = f"avatars/{user_id}.{file_extension}"
        file_data = await avatar_file.read()

        try:
            profile.avatar = await self.storage.upload_file(file_data, object_key)
        except BaseS3Error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar. Please try again later.",
            )

    async def save_to_database(self, profile: UserProfile) -> None:
        """Safely commit changes or rollback and raise 500 on database failure."""
        try:
            await self.db.commit()
            await self.db.refresh(profile)
        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while saving profile changes.",
            )

    @staticmethod
    def build_profile_response(profile: UserProfile) -> UserProfileResponseSchema:
        avatar_url = HttpUrl(profile.avatar) if profile.avatar else None
        return UserProfileResponseSchema(
            id=profile.id,
            user_id=profile.user_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            gender=profile.gender,
            date_of_birth=profile.date_of_birth,
            info=profile.info,
            avatar=avatar_url,
        )

    async def get_profile(self, user_id: int) -> UserProfileResponseSchema:
        user = await self.get_user_by_id(user_id=user_id)
        self.raise_404_if_user_is_none_or_not_active(user=user)

        profile = await self.get_profile_by_user_id(user_id=user_id)
        self.raise_404_if_profile_is_none(profile=profile)
        assert profile is not None

        return self.build_profile_response(profile)

    async def update_profile(
        self,
        user_id: int,
        profile_data: UserProfileRequestSchema,
    ) -> UserProfileResponseSchema:
        """Fetch, validate, update the user profile, and upload an avatar if present."""

        user = await self.get_user_by_id(user_id=user_id)
        self.raise_404_if_user_is_none_or_not_active(user=user)

        profile = await self.get_profile_by_user_id(user_id=user_id)
        self.raise_404_if_profile_is_none(profile=profile)
        assert profile is not None

        self.update_profile_fields(profile, profile_data)

        if profile_data.avatar is not None:
            await self.handle_avatar_upload(user_id, profile, profile_data.avatar)

        await self.save_to_database(profile)
        return self.build_profile_response(profile)


ProfileServiceDep = Annotated[ProfileService, Depends()]
