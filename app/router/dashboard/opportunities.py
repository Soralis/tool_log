from fastapi import APIRouter, Request, Depends
from sqlmodel import Session

from app.database_config import get_session
from app.templates.jinja_functions import templates

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
)

@router.get("/")
async def dashboard(request: Request):
    """Render the Opportunities dashboard page"""
    return templates.TemplateResponse(
        "dashboard/opportunities.html.j2",
        {"request": request}
    )

@router.get("/api/ranked")
async def get_ranked_opportunities(request: Request, db: Session = Depends(get_session)):
    """Return a ranked list of cost saving opportunities (placeholder)"""
    return {"opportunities": []}
