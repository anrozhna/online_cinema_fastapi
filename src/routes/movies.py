import uuid as uuid_lib

from fastapi import APIRouter, status

from schemas.movies import MovieDetailSchema
from services.movies import MovieServiceDep

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
