import uuid as uuid_lib
from typing import Annotated

from fastapi import Depends, HTTPException, status

from config.dependencies import (
    CertificationRepo,
    DirectorRepo,
    GenreRepo,
    MovieRepo,
    StarRepo,
)
from repositories.movies import MovieSortField
from schemas.movies import (
    MovieDetailSchema,
    MovieListSchema,
    PaginatedMoviesResponseSchema,
)


class MovieService:
    def __init__(
        self,
        movie_repo: MovieRepo,
        genre_repo: GenreRepo,
        star_repo: StarRepo,
        director_repo: DirectorRepo,
        certification_repo: CertificationRepo,
    ):
        self.movie_repo = movie_repo
        self.genre_repo = genre_repo
        self.star_repo = star_repo
        self.director_repo = director_repo
        self.certification_repo = certification_repo

    async def get_movie_by_uuid(self, movie_uuid: uuid_lib.UUID) -> MovieDetailSchema:
        movie = await self.movie_repo.get_by_uuid(movie_uuid)
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
            )
        return MovieDetailSchema.model_validate(movie)

    async def list_movies(
        self,
        limit: int,
        offset: int,
        year: int | None = None,
        min_imdb: float | None = None,
        search: str | None = None,
        sort_by: MovieSortField | None = None,
        sort_desc: bool = False,
    ) -> PaginatedMoviesResponseSchema:
        movies = await self.movie_repo.list_movies(
            limit=limit,
            offset=offset,
            year=year,
            min_imdb=min_imdb,
            search=search,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
        total = await self.movie_repo.count_movies(
            year=year, min_imdb=min_imdb, search=search
        )

        return PaginatedMoviesResponseSchema(
            items=[MovieListSchema.model_validate(movie) for movie in movies],
            total=total,
            limit=limit,
            offset=offset,
        )


MovieServiceDep = Annotated[MovieService, Depends()]
