import uuid as uuid_lib

from fastapi import APIRouter, Query, status

from config.dependencies import CurrentUser
from repositories.movies import MovieSortField
from schemas.movies import (
    MovieDetailSchema,
    MovieReactionRequestSchema,
    MovieReactionResponseSchema,
    PaginatedMoviesResponseSchema,
)
from services.movies import MovieServiceDep
from services.reactions import MovieReactionServiceDep

router = APIRouter()


@router.get(
    path="/{movie_uuid}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Get movie details",
    description="Retrieve full details for a single movie by its UUID.",
    responses={
        200: {"description": "Movie found successfully."},
        404: {"description": "Movie not found."},
    },
)
async def get_movie(movie_uuid: uuid_lib.UUID, movie_service: MovieServiceDep):
    return await movie_service.get_movie_by_uuid(movie_uuid)


@router.get(
    path="/",
    response_model=PaginatedMoviesResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="List movies",
    description=(
        "Retrieve a paginated, filterable, sortable list of movies. "
        "Supports search across title, description, director and star names."
    ),
    responses={
        200: {"description": "Movies found successfully."},
    },
)
async def list_movies(
    movie_service: MovieServiceDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    year: int | None = Query(default=None),
    min_imdb: float | None = Query(default=None, ge=0, le=10),
    search: str | None = Query(default=None, min_length=1),
    sort_by: MovieSortField | None = Query(default=None),
    sort_desc: bool = Query(default=False),
):
    return await movie_service.list_movies(
        limit=limit,
        offset=offset,
        year=year,
        min_imdb=min_imdb,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.post(
    path="/{movie_id}/reaction/",
    response_model=MovieReactionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Like or dislike a movie",
    description=(
        "Set the current user's reaction to a movie. Calling this again "
        "updates the existing reaction rather than creating a duplicate. "
        "Requires a valid Bearer access token."
    ),
    responses={
        200: {"description": "Reaction recorded or updated successfully."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Movie not found."},
    },
)
async def react_to_movie(
    movie_id: int,
    data: MovieReactionRequestSchema,
    current_user: CurrentUser,
    reaction_service: MovieReactionServiceDep,
):
    return await reaction_service.react_to_movie(
        movie_id=movie_id, user_id=current_user.id, data=data
    )
