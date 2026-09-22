from fastapi import FastAPI

from routes import (
    accounts_router,
    cart_router,
    catalog_management_router,
    movies_router,
    orders_router,
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
        "name": "admin",
        "description": "Administrative operations restricted to admin users.",
    },
]

app = FastAPI(openapi_tags=tags_metadata)

app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(user_management_router, prefix="/admin", tags=["user_management"])
app.include_router(
    catalog_management_router, prefix="/moderation", tags=["catalog_management"]
)
app.include_router(movies_router, prefix="/movies", tags=["movies"])
app.include_router(cart_router, prefix="/cart", tags=["cart"])
app.include_router(orders_router, prefix="/orders", tags=["orders"])
