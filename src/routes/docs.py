from fastapi import APIRouter, Request

from services.docs import DocsServiceDep

router = APIRouter(include_in_schema=False)


@router.get("/docs")
async def custom_swagger_ui(token: str, docs_service: DocsServiceDep):
    return await docs_service.get_swagger_ui(token)


@router.get("/redoc")
async def custom_redoc(token: str, docs_service: DocsServiceDep):
    return await docs_service.get_redoc_ui(token)


@router.get("/openapi.json")
async def custom_openapi(token: str, request: Request, docs_service: DocsServiceDep):
    return await docs_service.get_openapi_schema(token, request)
