from fastapi import APIRouter
from . import requests, tools, dashboard, upload


router = APIRouter()

# Include the dashboard routers
router.include_router(dashboard.router)
router.include_router(requests.router)
router.include_router(tools.router)
router.include_router(upload.router)

