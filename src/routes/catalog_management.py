from fastapi import APIRouter, Depends, status

from config.dependencies import (
    CertificationCrud,
    DirectorCrud,
    GenreCrud,
    StarCrud,
    require_admin_or_moderator,
)
from schemas.movies import (
    CertificationBaseSchema,
    CertificationResponseSchema,
    DirectorBaseSchema,
    DirectorResponseSchema,
    GenreBaseSchema,
    GenreResponseSchema,
    MovieCreateUpdateSchema,
    MovieDetailSchema,
    StarBaseSchema,
    StarResponseSchema,
)
from services.movies import MovieServiceDep

router = APIRouter(dependencies=[Depends(require_admin_or_moderator)])


# --- Movies --------------------------------------------------------------


@router.post(
    path="/movies/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a movie",
    description="Create a new movie. Requires administrator or moderator privileges.",
    responses={
        201: {"description": "Movie created successfully."},
        400: {"description": "Certification, genre, director or star not found."},
        403: {"description": "Admin or moderator privileges required."},
        409: {
            "description": "A movie with this name, year and duration already exists."
        },
    },
)
async def create_movie(data: MovieCreateUpdateSchema, movie_service: MovieServiceDep):
    return await movie_service.create_movie(data)


@router.put(
    path="/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a movie",
    description="Replace a movie's data. "
    "Requires administrator or moderator privileges.",
    responses={
        200: {"description": "Movie updated successfully."},
        400: {"description": "Certification, genre, director or star not found."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Movie not found."},
    },
)
async def update_movie(
    movie_id: int, data: MovieCreateUpdateSchema, movie_service: MovieServiceDep
):
    return await movie_service.update_movie(movie_id, data)


@router.delete(
    path="/movies/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a movie",
    description="Delete a movie. Requires administrator or moderator privileges.",
    responses={
        204: {"description": "Movie deleted successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Movie not found."},
        409: {"description": "Cannot delete a movie that has been purchased."},
    },
)
async def delete_movie(movie_id: int, movie_service: MovieServiceDep):
    await movie_service.delete_movie(movie_id)


# --- Genres ----------------------------------------------------------------


@router.post(
    path="/genres/",
    response_model=GenreResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a genre",
    description="Create a new genre. Requires administrator or moderator privileges.",
    responses={
        201: {"description": "Genre created successfully."},
        403: {"description": "Admin or moderator privileges required."},
        409: {"description": "A genre with this name already exists."},
    },
)
async def create_genre(data: GenreBaseSchema, genre_crud: GenreCrud):
    return await genre_crud.create(data)


@router.put(
    path="/genres/{genre_id}/",
    response_model=GenreResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a genre",
    description="Update a genre's name. "
    "Requires administrator or moderator privileges.",
    responses={
        200: {"description": "Genre updated successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Genre not found."},
    },
)
async def update_genre(genre_id: int, data: GenreBaseSchema, genre_crud: GenreCrud):
    return await genre_crud.update(genre_id, data)


@router.delete(
    path="/genres/{genre_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a genre",
    description="Delete a genre. Requires administrator or moderator privileges.",
    responses={
        204: {"description": "Genre deleted successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Genre not found."},
    },
)
async def delete_genre(genre_id: int, genre_crud: GenreCrud):
    await genre_crud.delete(genre_id)


# --- Stars -----------------------------------------------------------------


@router.post(
    path="/stars/",
    response_model=StarResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a star",
    description="Create a new star. Requires administrator or moderator privileges.",
    responses={
        201: {"description": "Star created successfully."},
        403: {"description": "Admin or moderator privileges required."},
        409: {"description": "A star with this name already exists."},
    },
)
async def create_star(data: StarBaseSchema, star_crud: StarCrud):
    return await star_crud.create(data)


@router.put(
    path="/stars/{star_id}/",
    response_model=StarResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a star",
    description="Update a star's name. Requires administrator or moderator privileges.",
    responses={
        200: {"description": "Star updated successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Star not found."},
    },
)
async def update_star(star_id: int, data: StarBaseSchema, star_crud: StarCrud):
    return await star_crud.update(star_id, data)


@router.delete(
    path="/stars/{star_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a star",
    description="Delete a star. Requires administrator or moderator privileges.",
    responses={
        204: {"description": "Star deleted successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Star not found."},
    },
)
async def delete_star(star_id: int, star_crud: StarCrud):
    await star_crud.delete(star_id)


# --- Directors ---------------------------------------------------------


@router.post(
    path="/directors/",
    response_model=DirectorResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a director",
    description="Create a new director. "
    "Requires administrator or moderator privileges.",
    responses={
        201: {"description": "Director created successfully."},
        403: {"description": "Admin or moderator privileges required."},
        409: {"description": "A director with this name already exists."},
    },
)
async def create_director(data: DirectorBaseSchema, director_crud: DirectorCrud):
    return await director_crud.create(data)


@router.put(
    path="/directors/{director_id}/",
    response_model=DirectorResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a director",
    description="Update a director's name. "
    "Requires administrator or moderator privileges.",
    responses={
        200: {"description": "Director updated successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Director not found."},
    },
)
async def update_director(
    director_id: int, data: DirectorBaseSchema, director_crud: DirectorCrud
):
    return await director_crud.update(director_id, data)


@router.delete(
    path="/directors/{director_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a director",
    description="Delete a director. Requires administrator or moderator privileges.",
    responses={
        204: {"description": "Director deleted successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Director not found."},
    },
)
async def delete_director(director_id: int, director_crud: DirectorCrud):
    await director_crud.delete(director_id)


# --- Certifications ---------------------------------------------------------


@router.post(
    path="/certifications/",
    response_model=CertificationResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a certification",
    description="Create a new certification. "
    "Requires administrator or moderator privileges.",
    responses={
        201: {"description": "Certification created successfully."},
        403: {"description": "Admin or moderator privileges required."},
        409: {"description": "A certification with this name already exists."},
    },
)
async def create_certification(
    data: CertificationBaseSchema, certification_crud: CertificationCrud
):
    return await certification_crud.create(data)


@router.put(
    path="/certifications/{certification_id}/",
    response_model=CertificationResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a certification",
    description="Update a certification's name. "
    "Requires administrator or moderator privileges.",
    responses={
        200: {"description": "Certification updated successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Certification not found."},
    },
)
async def update_certification(
    certification_id: int,
    data: CertificationBaseSchema,
    certification_crud: CertificationCrud,
):
    return await certification_crud.update(certification_id, data)


@router.delete(
    path="/certifications/{certification_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a certification",
    description="Delete a certification. "
    "Requires administrator or moderator privileges.",
    responses={
        204: {"description": "Certification deleted successfully."},
        403: {"description": "Admin or moderator privileges required."},
        404: {"description": "Certification not found."},
    },
)
async def delete_certification(
    certification_id: int, certification_crud: CertificationCrud
):
    await certification_crud.delete(certification_id)
