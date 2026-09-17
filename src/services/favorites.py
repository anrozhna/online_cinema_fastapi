from typing import Annotated

from fastapi import Depends, HTTPException, status

from config.dependencies import FavoriteMoviesRepo, FavoriteRepo, MovieRepo
from database.models.movies import Favorite
from repositories.base_movie import MovieSortField
from schemas.movies import MovieListSchema, PaginatedMoviesResponseSchema
from services.movies_shared import get_movie_or_404


class FavoriteService:
    def __init__(
        self,
        favorite_repo: FavoriteRepo,
        favorite_movies_repo: FavoriteMoviesRepo,
        movie_repo: MovieRepo,
    ):
        self.favorite_repo = favorite_repo
        self.favorite_movies_repo = favorite_movies_repo
        self.movie_repo = movie_repo

    async def add_to_favorites(self, movie_id: int, user_id: int) -> None:
        await get_movie_or_404(self.movie_repo, movie_id)

        existing = await self.favorite_repo.get_by_user_and_movie(user_id, movie_id)
        if existing is not None:
            return  # already favorite — idempotent, not an error

        favorite = Favorite(user_id=user_id, movie_id=movie_id)
        self.favorite_repo.add(favorite)
        await self.favorite_repo.db.commit()

    async def remove_from_favorites(self, movie_id: int, user_id: int) -> None:
        favorite = await self.favorite_repo.get_by_user_and_movie(user_id, movie_id)
        if favorite is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movie is not in favorites.",
            )

        await self.favorite_repo.delete(favorite)
        await self.favorite_repo.db.commit()

    async def list_favorites(
        self,
        user_id: int,
        limit: int,
        offset: int,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
        sort_by: MovieSortField | None = None,
        sort_desc: bool = False,
    ) -> PaginatedMoviesResponseSchema:
        movies = await self.favorite_movies_repo.list_favorite_movies(
            user_id=user_id,
            limit=limit,
            offset=offset,
            year=year,
            min_imdb=min_imdb,
            search=search,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        total = await self.favorite_movies_repo.count_favorite_movies(
            user_id=user_id, year=year, min_imdb=min_imdb, search=search
        )

        return PaginatedMoviesResponseSchema(
            items=[MovieListSchema.model_validate(m) for m in movies],
            total=total,
            limit=limit,
            offset=offset,
        )


FavoriteServiceDep = Annotated[FavoriteService, Depends()]
