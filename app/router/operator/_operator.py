from fastapi import APIRouter
from app.router.operator.change_over import router as change_over_router

router = APIRouter()

router.include_router(change_over_router, prefix="/change_over", tags=["change_over"])
