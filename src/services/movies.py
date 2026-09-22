import uuid as uuid_lib
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from config.dependencies import (
    CartItemRepo,
    CertificationRepo,
    DirectorRepo,
    GenreRepo,
    MovieRepo,
    StarRepo,
    UserRepo,
)
from database.models.accounts import UserGroupEnum
from database.models.movies import Movie
from notifications.tasks import send_movie_removed_from_carts_notification_task
from repositories.movies import MovieSortField
from schemas.movies import (
    MovieCreateUpdateSchema,
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
        cart_item_repo: CartItemRepo,
        user_repo: UserRepo,
    ):
        self.movie_repo = movie_repo
        self.genre_repo = genre_repo
        self.star_repo = star_repo
        self.director_repo = director_repo
        self.certification_repo = certification_repo
        self.cart_item_repo = cart_item_repo
        self.user_repo = user_repo

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

    @staticmethod
    async def _resolve_ids(repo, ids: list[int], label: str) -> list:
        if not ids:
            return []
        resolved = []
        for entity_id in ids:
            entity = await repo.get_by_id(entity_id)
            if entity is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{label} with id {entity_id} not found.",
                )
            resolved.append(entity)
        return resolved

    async def create_movie(self, data: MovieCreateUpdateSchema) -> Movie:
        if await self.movie_repo.exists_by_name_year_time(
            data.name, data.year, data.time
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A movie with this name, year and duration already exists.",
            )

        certification = await self.certification_repo.get_by_id(data.certification_id)
        if certification is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certification not found.",
            )

        genres = await self._resolve_ids(self.genre_repo, data.genre_ids, "Genre")
        directors = await self._resolve_ids(
            self.director_repo, data.director_ids, "Director"
        )
        stars = await self._resolve_ids(self.star_repo, data.star_ids, "Star")

        movie = Movie(
            name=data.name,
            year=data.year,
            time=data.time,
            imdb=data.imdb,
            votes=data.votes,
            meta_score=data.meta_score,
            gross=data.gross,
            description=data.description,
            price=data.price,
            certification_id=data.certification_id,
        )
        movie.genres = genres
        movie.directors = directors
        movie.stars = stars

        self.movie_repo.add(movie)
        await self.movie_repo.db.commit()
        await self.movie_repo.db.refresh(movie)

        # Refresh alone doesn't eager-load the many-to-many relationships —
        # re-fetch through get_by_uuid, which already has the correct
        # joinedload/selectinload options for full serialization.
        return await self.movie_repo.get_by_uuid(movie.uuid)

    async def update_movie(self, movie_id: int, data: MovieCreateUpdateSchema) -> Movie:
        movie = await self.movie_repo.get_by_id_with_relations(movie_id)
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
            )

        certification = await self.certification_repo.get_by_id(data.certification_id)
        if certification is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certification not found.",
            )

        movie.name = data.name
        movie.year = data.year
        movie.time = data.time
        movie.imdb = data.imdb
        movie.votes = data.votes
        movie.meta_score = data.meta_score
        movie.gross = data.gross
        movie.description = data.description
        movie.price = data.price
        movie.certification_id = data.certification_id
        movie.genres = await self._resolve_ids(self.genre_repo, data.genre_ids, "Genre")
        movie.directors = await self._resolve_ids(
            self.director_repo, data.director_ids, "Director"
        )
        movie.stars = await self._resolve_ids(self.star_repo, data.star_ids, "Star")

        await self.movie_repo.db.commit()
        await self.movie_repo.db.refresh(movie)
        return await self.movie_repo.get_by_uuid(movie.uuid)

    async def delete_movie(self, movie_id: int) -> None:
        movie = await self.movie_repo.get_by_id(movie_id)
        if movie is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
            )

        cart_count = await self.cart_item_repo.count_by_movie_id(movie_id)
        movie_name = movie.name

        try:
            await self.movie_repo.delete(movie)
            await self.movie_repo.db.commit()
        except IntegrityError:
            await self.movie_repo.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a movie that has been purchased.",
            )

        if cart_count > 0:
            moderator_emails = await self.user_repo.get_emails_by_group(
                UserGroupEnum.MODERATOR
            )
            for email in moderator_emails:
                send_movie_removed_from_carts_notification_task.delay(
                    email=email, movie_name=movie_name, cart_count=cart_count
                )

        if cart_count > 0:
            moderator_emails = await self.user_repo.get_emails_by_group(
                UserGroupEnum.MODERATOR
            )
            for email in moderator_emails:
                send_movie_removed_from_carts_notification_task.delay(
                    email=email, movie_name=movie_name, cart_count=cart_count
                )


MovieServiceDep = Annotated[MovieService, Depends()]
