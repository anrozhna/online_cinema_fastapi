import uuid as uuid_lib

from fastapi import APIRouter, Query, status

from config.dependencies import CurrentUser
from repositories.movies import MovieSortField
from schemas.movies import (
    CommentCreateRequestSchema,
    CommentResponseSchema,
    MovieDetailSchema,
    MovieReactionRequestSchema,
    MovieReactionResponseSchema,
    PaginatedMoviesResponseSchema,
    RatingRequestSchema,
    RatingResponseSchema,
)
from services.comments import CommentServiceDep
from services.movies import MovieServiceDep
from services.ratings import RatingServiceDep
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


@router.get(
    path="/{movie_id}/comments/",
    response_model=list[CommentResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List comments for a movie",
    description="Retrieve all comments for a movie as a nested reply tree.",
    responses={
        200: {"description": "Comments retrieved successfully."},
        404: {"description": "Movie not found."},
    },
)
async def list_movie_comments(movie_id: int, comment_service: CommentServiceDep):
    return await comment_service.list_comments_for_movie(movie_id)


@router.post(
    path="/{movie_id}/comments/",
    response_model=CommentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Post a comment or reply",
    description=(
        "Create a new top-level comment, or a reply by providing "
        "parent_comment_id. Requires a valid Bearer access token."
    ),
    responses={
        201: {"description": "Comment posted successfully."},
        400: {"description": "Parent comment not found for this movie."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Movie not found."},
    },
)
async def create_movie_comment(
    movie_id: int,
    data: CommentCreateRequestSchema,
    current_user: CurrentUser,
    comment_service: CommentServiceDep,
):
    return await comment_service.create_comment(
        movie_id=movie_id, user_id=current_user.id, data=data
    )


@router.post(
    path="/{movie_id}/rating/",
    response_model=RatingResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Rate a movie",
    description=(
        "Set the current user's 1-10 rating for a movie. Calling this again "
        "updates the existing rating rather than creating a duplicate. "
        "Requires a valid Bearer access token."
    ),
    responses={
        200: {"description": "Rating recorded or updated successfully."},
        401: {"description": "Invalid or missing access token."},
        404: {"description": "Movie not found."},
        422: {"description": "Score must be between 1 and 10."},
    },
)
async def rate_movie(
    movie_id: int,
    data: RatingRequestSchema,
    current_user: CurrentUser,
    rating_service: RatingServiceDep,
):
    return await rating_service.rate_movie(
        movie_id=movie_id, user_id=current_user.id, data=data
    )
