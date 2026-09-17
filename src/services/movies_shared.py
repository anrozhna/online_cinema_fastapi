from fastapi import HTTPException, status

from repositories.movies import MovieRepository


async def get_movie_or_404(movie_repo: MovieRepository, movie_id: int):
    movie = await movie_repo.get_by_id(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found."
        )
    return movie
