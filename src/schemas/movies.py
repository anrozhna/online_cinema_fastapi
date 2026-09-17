import uuid as uuid_lib

from pydantic import BaseModel


class GenreBaseSchema(BaseModel):
    name: str


class GenreResponseSchema(GenreBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class StarBaseSchema(BaseModel):
    name: str


class StarResponseSchema(StarBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class DirectorBaseSchema(BaseModel):
    name: str


class DirectorResponseSchema(DirectorBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class CertificationBaseSchema(BaseModel):
    name: str


class CertificationResponseSchema(CertificationBaseSchema):
    id: int

    model_config = {"from_attributes": True}


class MovieBaseSchema(BaseModel):
    uuid: uuid_lib.UUID
    name: str
    year: int
    time: int
    imdb: float


class MovieDetailSchema(MovieBaseSchema):
    votes: int
    meta_score: float | None = None
    gross: float | None = None
    description: str
    price: float
    certification: CertificationResponseSchema
    genres: list[GenreResponseSchema]
    directors: list[DirectorResponseSchema]
    stars: list[StarResponseSchema]

    model_config = {"from_attributes": True}


class MovieListSchema(MovieBaseSchema):
    genres: list[GenreBaseSchema]

    model_config = {"from_attributes": True}


class PaginatedMoviesResponseSchema(BaseModel):
    items: list[MovieListSchema]
    total: int
    limit: int
    offset: int
