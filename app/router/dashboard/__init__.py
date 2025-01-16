from fastapi import APIRouter
from . import graphs, monitoring


router = APIRouter()

# Include the dashboard routers
router.include_router(monitoring.router)
router.include_router(graphs.router)
