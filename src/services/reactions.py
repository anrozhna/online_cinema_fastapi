from typing import Annotated

from fastapi import Depends

from config.dependencies import MovieReactionRepo, MovieRepo
from database.models.movies import MovieReaction
from schemas.movies import MovieReactionRequestSchema, MovieReactionResponseSchema
from services.movies_shared import get_movie_or_404


class MovieReactionService:
    def __init__(self, reaction_repo: MovieReactionRepo, movie_repo: MovieRepo):
        self.reaction_repo = reaction_repo
        self.movie_repo = movie_repo

    async def react_to_movie(
        self, movie_id: int, user_id: int, data: MovieReactionRequestSchema
    ) -> MovieReactionResponseSchema:
        await get_movie_or_404(self.movie_repo, movie_id)

        existing = await self.reaction_repo.get_by_user_and_movie(user_id, movie_id)
        if existing is not None:
            existing.is_like = data.is_like
            reaction = existing
        else:
            reaction = MovieReaction(
                user_id=user_id, movie_id=movie_id, is_like=data.is_like
            )
            self.reaction_repo.add(reaction)

        await self.reaction_repo.db.commit()
        await self.reaction_repo.db.refresh(reaction)

        return MovieReactionResponseSchema.model_validate(reaction)


MovieReactionServiceDep = Annotated[MovieReactionService, Depends()]
