from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from database.models.orders import OrderStatusEnum


class OrderItemResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the order item.")
    movie_id: int = Field(..., description="ID of the ordered movie.")
    movie_name: str = Field(
        ..., description="Title of the movie.", examples=["Inception"]
    )
    price_at_order: Decimal = Field(
        ...,
        description="Price of the movie at the time of ordering.",
        examples=["9.99"],
    )


class OrderResponseSchema(BaseModel):
    id: int = Field(..., description="Unique identifier of the order.")
    status: OrderStatusEnum = Field(
        ..., description="Current status of the order.", examples=["pending"]
    )
    total_amount: Decimal = Field(
        ..., description="Total amount of the order.", examples=["22.98"]
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the order was placed."
    )
    items: list[OrderItemResponseSchema] = Field(
        default_factory=list, description="Movies included in this order."
    )


class PlaceOrderResponseSchema(BaseModel):
    order: OrderResponseSchema | None = Field(
        default=None,
        description="The created order, or null if every cart item was excluded.",
    )
    excluded_movie_names: list[str] = Field(
        default_factory=list,
        description="Titles excluded from the order because they were already "
        "purchased or already in another pending order.",
    )
