from datetime import datetime

from pydantic import BaseModel, Field


class CartItemResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the cart item.")
    movie_id: int = Field(..., description="ID of the movie in the cart.")
    movie_name: str = Field(
        ..., description="Title of the movie.", examples=["Inception"]
    )
    movie_price: float = Field(
        ..., description="Current price of the movie.", examples=[9.99]
    )
    movie_year: int = Field(
        ..., description="Release year of the movie.", examples=[2010]
    )
    movie_genres: list[str] = Field(
        default_factory=list,
        description="Genre names of the movie.",
        examples=[["Action", "Sci-Fi"]],
    )
    added_at: datetime = Field(
        ..., description="Timestamp when the item was added to the cart."
    )


class CartResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the cart.")
    items: list[CartItemResponseSchema] = Field(
        default_factory=list, description="Movies currently in the cart."
    )
    total_price: float = Field(
        ..., description="Sum of prices of all items in the cart.", examples=[22.98]
    )
