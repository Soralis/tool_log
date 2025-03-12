from fastapi import APIRouter
from . import requests, tools, tool_lifes, dashboard, upload, orders, monetary


router = APIRouter()

# Include the dashboard routers
router.include_router(dashboard.router)
router.include_router(requests.router)
router.include_router(tools.router)
router.include_router(tool_lifes.router)
router.include_router(upload.router)
router.include_router(orders.router)
router.include_router(monetary.router)

