import uuid as uuid_lib
from datetime import datetime

from pydantic import BaseModel, Field


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


class CommentCreateRequestSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    parent_comment_id: int | None = Field(
        default=None,
        description="ID of the comment being replied to. Omit for a top-level comment.",
    )


class CommentResponseSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    text: str
    parent_comment_id: int | None
    created_at: datetime
    replies: list["CommentResponseSchema"] = []

    model_config = {"from_attributes": True}


CommentResponseSchema.model_rebuild()


class RatingRequestSchema(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Rating from 1 to 10.")


class RatingResponseSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class MovieReactionRequestSchema(BaseModel):
    is_like: bool = Field(..., description="True for a like, false for a dislike.")


class MovieReactionResponseSchema(BaseModel):
    id: int
    user_id: int
    movie_id: int
    is_like: bool
    created_at: datetime

    model_config = {"from_attributes": True}
