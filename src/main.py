from fastapi import FastAPI

from routes import (
    accounts_router,
    cart_router,
    catalog_management_router,
    movies_router,
    orders_router,
    payments_router,
    profiles_router,
    user_management_router,
)

tags_metadata = [
    {
        "name": "accounts",
        "description": "Registration, login, and password management.",
    },
    {"name": "profiles", "description": "User profile data and avatar management."},
    {
        "name": "user-management",
        "description": "Admin-only user role and activation management.",
    },
    {
        "name": "movies",
        "description": "Movie catalog, comments, ratings, reactions and favorites.",
    },
    {
        "name": "catalog-management",
        "description": "Admin/moderator CRUD for movies and reference entities.",
    },
    {"name": "cart", "description": "Shopping cart management."},
    {"name": "orders", "description": "Order placement and lifecycle."},
    {
        "name": "payments",
        "description": "Stripe checkout sessions, webhook, and payment history.",
    },
]

app = FastAPI(
    title="Online Cinema API",
    version="1.0.0",
    description=(
        "Backend API for an online movie rental/purchase platform: "
        "accounts, a movie catalog with comments/ratings, a shopping "
        "cart, orders, and Stripe-based payments."
    ),
    openapi_tags=tags_metadata,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(user_management_router, prefix="/admin", tags=["user_management"])
app.include_router(
    catalog_management_router, prefix="/moderation", tags=["catalog_management"]
)
app.include_router(movies_router, prefix="/movies", tags=["movies"])
app.include_router(cart_router, prefix="/cart", tags=["cart"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
app.include_router(payments_router, prefix="/payments", tags=["payments"])
