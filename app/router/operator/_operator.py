from fastapi import APIRouter
from app.router.operator.change_over import router as change_over_router
from app.router.operator.tool_life import router as tool_life_router

router = APIRouter()

router.include_router(change_over_router, prefix="/change_over", tags=["change_over"])
router.include_router(tool_life_router, prefix="/tool_life", tags=["tool_life"])
