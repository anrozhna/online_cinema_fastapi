from database.models.movies import Certification, Director, Genre, Movie, Star
from repositories import BaseRepository


class MovieRepository(BaseRepository[Movie]):
    model = Movie


class GenreRepository(BaseRepository[Genre]):
    model = Genre


class StarRepository(BaseRepository[Star]):
    model = Star


class DirectorRepository(BaseRepository[Director]):
    model = Director


class CertificationRepository(BaseRepository[Certification]):
    model = Certification
