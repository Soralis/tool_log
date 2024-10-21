from app.templates.jinja_functions import templates
from fastapi import APIRouter, Request

from app.router.engineer import machines, manufacturer, users, tools

router = APIRouter()

router.include_router(machines.router, prefix="/machines", tags=["machines"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(manufacturer.router, prefix="/manufacturers", tags=["manufacturer"])
router.include_router(tools.router, prefix="/tools", tags=["tools"])

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="engineer/index.html")