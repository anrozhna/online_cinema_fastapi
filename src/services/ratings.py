from typing import Annotated

from fastapi import Depends

from config.dependencies import MovieRepo, RatingRepo
from database.models.movies import Rating
from schemas.movies import RatingRequestSchema, RatingResponseSchema
from services.movies_shared import get_movie_or_404


class RatingService:
    def __init__(self, rating_repo: RatingRepo, movie_repo: MovieRepo):
        self.rating_repo = rating_repo
        self.movie_repo = movie_repo

    async def rate_movie(
        self, movie_id: int, user_id: int, data: RatingRequestSchema
    ) -> RatingResponseSchema:
        await get_movie_or_404(self.movie_repo, movie_id)

        existing = await self.rating_repo.get_by_user_and_movie(user_id, movie_id)
        if existing is not None:
            existing.score = data.score
            rating = existing
        else:
            rating = Rating(user_id=user_id, movie_id=movie_id, score=data.score)
            self.rating_repo.add(rating)

        await self.rating_repo.db.commit()
        await self.rating_repo.db.refresh(rating)

        return RatingResponseSchema.model_validate(rating)


RatingServiceDep = Annotated[RatingService, Depends()]
