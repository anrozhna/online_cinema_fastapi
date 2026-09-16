from fastapi import FastAPI

from routes import accounts_router, admin_router, profiles_router

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
app.include_router(admin_router, prefix="/admin", tags=["admin"])
