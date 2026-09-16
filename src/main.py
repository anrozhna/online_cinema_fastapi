from fastapi import FastAPI

from routes import accounts_router, admin_router, profiles_router

app = FastAPI()

app.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
