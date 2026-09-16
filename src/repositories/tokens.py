from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from database.models.accounts import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)
from repositories.base import BaseRepository


class ActivationTokenRepository(BaseRepository[ActivationToken]):
    model = ActivationToken

    async def get_by_user_id(self, user_id: int) -> ActivationToken | None:
        stmt = select(ActivationToken).where(ActivationToken.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_and_token(
        self, email: str, token: str
    ) -> ActivationToken | None:
        """Joins User to allow lookup by the email supplied in the activation request,
        eagerly loading the related User to avoid a MissingGreenlet on `.user` access
        later in the service (the async lazy-load problem we hit earlier)."""

        stmt = (
            select(ActivationToken)
            .options(joinedload(ActivationToken.user))
            .join(User)
            .where(User.email == email, ActivationToken.token == token)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    model = PasswordResetToken

    async def get_by_user_id(self, user_id: int) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_all_for_user(self, user_id: int) -> None:
        await self.db.execute(
            delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_token(self, token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
