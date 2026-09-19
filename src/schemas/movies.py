import uuid as uuid_lib
from datetime import datetime

from pydantic import BaseModel, Field


class GenreBaseSchema(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Genre name.",
        examples=["Action"],
    )


class GenreResponseSchema(GenreBaseSchema):
    id: int = Field(..., description="Unique identifier of the genre.")

    model_config = {"from_attributes": True}


class StarBaseSchema(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Star's full name.",
        examples=["Leonardo DiCaprio"],
    )


class StarResponseSchema(StarBaseSchema):
    id: int = Field(..., description="Unique identifier of the star.")

    model_config = {"from_attributes": True}


class DirectorBaseSchema(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Director's full name.",
        examples=["Christopher Nolan"],
    )


class DirectorResponseSchema(DirectorBaseSchema):
    id: int = Field(..., description="Unique identifier of the director.")

    model_config = {"from_attributes": True}


class CertificationBaseSchema(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Certification name.",
        examples=["PG-13"],
    )


class CertificationResponseSchema(CertificationBaseSchema):
    id: int = Field(..., description="Unique identifier of the certification.")

    model_config = {"from_attributes": True}


class MovieBaseSchema(BaseModel):
    uuid: uuid_lib.UUID = Field(
        ..., description="Public, globally unique identifier of the movie."
    )
    name: str = Field(..., description="Movie title.", examples=["Inception"])
    year: int = Field(..., description="Release year.", examples=[2010])
    time: int = Field(..., description="Runtime in minutes.", examples=[148])
    imdb: float = Field(..., description="IMDb rating out of 10.", examples=[8.8])


class MovieDetailSchema(MovieBaseSchema):
    votes: int = Field(..., description="Number of votes on IMDb.", examples=[2000000])
    meta_score: float | None = Field(
        default=None, description="Metascore rating, if available."
    )
    gross: float | None = Field(
        default=None, description="Gross revenue in USD, if available."
    )
    description: str = Field(..., description="Plot synopsis of the movie.")
    price: float = Field(
        ..., description="Price to purchase the movie.", examples=[9.99]
    )
    certification: CertificationResponseSchema = Field(
        ..., description="Certification of the movie."
    )
    genres: list[GenreResponseSchema] = Field(
        default_factory=list, description="Genres the movie belongs to."
    )
    directors: list[DirectorResponseSchema] = Field(
        default_factory=list, description="Directors of the movie."
    )
    stars: list[StarResponseSchema] = Field(
        default_factory=list, description="Featured cast of the movie."
    )

    model_config = {"from_attributes": True}


class MovieListSchema(MovieBaseSchema):
    genres: list[GenreBaseSchema] = Field(
        default_factory=list, description="Genres the movie belongs to."
    )

    model_config = {"from_attributes": True}


class PaginatedMoviesResponseSchema(BaseModel):
    items: list[MovieListSchema] = Field(
        ..., description="Movies matching the current page, filters and sort order."
    )
    total: int = Field(
        ...,
        description="Total number of movies matching the filters, across all pages.",
    )
    limit: int = Field(..., description="Maximum number of items requested per page.")
    offset: int = Field(..., description="Number of items skipped before this page.")


class MovieCreateUpdateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Movie title.")
    year: int = Field(..., ge=1888, le=2100, description="Release year.")
    time: int = Field(..., gt=0, description="Runtime in minutes.")
    imdb: float = Field(..., ge=0, le=10, description="IMDb rating out of 10.")
    votes: int = Field(..., ge=0, description="Number of votes on IMDb.")
    meta_score: float | None = Field(
        default=None, ge=0, le=100, description="Metascore rating, if available."
    )
    gross: float | None = Field(
        default=None, ge=0, description="Gross revenue in USD, if available."
    )
    description: str = Field(
        ..., min_length=1, description="Plot synopsis of the movie."
    )
    price: float = Field(..., gt=0, description="Price to purchase the movie.")
    certification_id: int = Field(
        ..., description="ID of an existing certification to assign to the movie."
    )
    genre_ids: list[int] = Field(
        default_factory=list,
        description="IDs of existing genres to assign to the movie.",
    )
    director_ids: list[int] = Field(
        default_factory=list,
        description="IDs of existing directors to assign to the movie.",
    )
    star_ids: list[int] = Field(
        default_factory=list,
        description="IDs of existing stars to assign to the movie.",
    )


class CommentCreateRequestSchema(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Comment text, 1 to 2000 characters.",
        examples=["Great movie, loved the ending!"],
    )
    parent_comment_id: int | None = Field(
        default=None,
        description="ID of the comment being replied to. Omit for a top-level comment.",
    )


class CommentResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the comment.")
    user_id: int = Field(..., description="ID of the user who wrote the comment.")
    movie_id: int = Field(..., description="ID of the movie this comment belongs to.")
    text: str = Field(..., description="Comment text.")
    parent_comment_id: int | None = Field(
        default=None,
        description="ID of the parent comment, or null for a top-level comment.",
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the comment was posted."
    )
    replies: list["CommentResponseSchema"] = Field(
        default_factory=list, description="Nested replies to this comment."
    )

    model_config = {"from_attributes": True}


CommentResponseSchema.model_rebuild()


class RatingRequestSchema(BaseModel):
    score: int = Field(
        ..., ge=1, le=10, description="Rating from 1 to 10.", examples=[8]
    )


class RatingResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the rating.")
    user_id: int = Field(..., description="ID of the user who submitted the rating.")
    movie_id: int = Field(..., description="ID of the rated movie.")
    score: int = Field(..., description="Rating value, 1 to 10.")
    created_at: datetime = Field(
        ..., description="Timestamp when the rating was submitted."
    )

    model_config = {"from_attributes": True}


class MovieReactionRequestSchema(BaseModel):
    is_like: bool = Field(..., description="True for a like, false for a dislike.")


class MovieReactionResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the reaction.")
    user_id: int = Field(..., description="ID of the user who reacted.")
    movie_id: int = Field(..., description="ID of the movie reacted to.")
    is_like: bool = Field(..., description="True for a like, false for a dislike.")
    created_at: datetime = Field(
        ..., description="Timestamp when the reaction was recorded."
    )

    model_config = {"from_attributes": True}
