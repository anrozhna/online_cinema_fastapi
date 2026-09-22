from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse

from config.dependencies import JWTManager, UserRepo
from database.models.accounts import UserGroupEnum
from exceptions.security import BaseSecurityError


class DocsService:
    def __init__(self, jwt_manager: JWTManager, user_repo: UserRepo):
        self.jwt_manager = jwt_manager
        self.user_repo = user_repo

    async def verify_admin_token(self, token: str) -> None:
        """Decode the given JWT and confirm it belongs to an active admin.

        Used to gate access to the docs endpoints — since a browser
        navigating to /docs can't attach an Authorization header, the
        admin's access token is passed as a query parameter instead. Less
        secure than a header (tokens can end up in browser history/server
        logs), but reuses the same JWT everything else in the API relies on.
        """
        try:
            payload = self.jwt_manager.decode_access_token(token)
        except BaseSecurityError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )

        user_id = payload.get("user_id")
        user = await self.user_repo.get_by_id(user_id) if user_id else None
        if user is None or not user.has_group(UserGroupEnum.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to view API docs.",
            )

    async def get_swagger_ui(self, token: str) -> HTMLResponse:
        await self.verify_admin_token(token)
        return get_swagger_ui_html(
            openapi_url=f"/openapi.json?token={token}", title="Online Cinema API — Docs"
        )

    async def get_redoc_ui(self, token: str) -> HTMLResponse:
        await self.verify_admin_token(token)
        return get_redoc_html(
            openapi_url=f"/openapi.json?token={token}",
            title="Online Cinema API — ReDoc",
        )

    async def get_openapi_schema(self, token: str, request: Request) -> JSONResponse:
        await self.verify_admin_token(token)
        app = request.app
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        return JSONResponse(schema)


DocsServiceDep = Annotated[DocsService, Depends()]
