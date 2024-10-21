from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from templates.jinja_functions import templates
from typing import List
from app.database_config import get_db
from app.models.models import ToolLife, Machine

router = APIRouter()

@router.get("/ToolLifes", response_model=List[ToolLife])
def get_ToolLifes(db: Session = Depends(get_db)):
    statement = select(ToolLife)
    results = db.execute(statement)
    ToolLifes = results.scalars().all()
    return ToolLifes

@router.get("/ToolLifes/", include_in_schema=False)
async def ToolLifes_page(request: Request):
    return templates.TemplateResponse("operator/ToolLifes.html", {"request": request})

@router.post("/ToolLifes", response_model=ToolLife)
def create_ToolLife(ToolLife: ToolLife, db: Session = Depends(get_db)):
    # Check if the machine exists
    machine = db.get(Machine, ToolLife.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    db.add(ToolLife)
    db.commit()
    db.refresh(ToolLife)
    return ToolLife

@router.get("/ToolLifes/{ToolLife_id}", response_model=ToolLife)
def get_ToolLife(ToolLife_id: int, db: Session = Depends(get_db)):
    statement = select(ToolLife).where(ToolLife.id == ToolLife_id)
    results = db.execute(statement)
    ToolLife = results.scalar_one_or_none()
    if not ToolLife:
        raise HTTPException(status_code=404, detail="ToolLife not found")
    return ToolLife

@router.get("/ToolLifes/machine/{machine_id}", response_model=List[ToolLife])
def get_ToolLifes_by_machine(machine_id: int, db: Session = Depends(get_db)):
    statement = select(ToolLife).where(ToolLife.machine_id == machine_id)
    results = db.execute(statement)
    ToolLifes = results.scalars().all()
    return ToolLifes

@router.delete("/ToolLifes/{ToolLife_id}")
def delete_ToolLife(ToolLife_id: int, db: Session = Depends(get_db)):
    statement = select(ToolLife).where(ToolLife.id == ToolLife_id)
    results = db.execute(statement)
    ToolLife = results.scalar_one_or_none()
    if not ToolLife:
        raise HTTPException(status_code=404, detail="ToolLife not found")
    db.delete(ToolLife)
    db.commit()
    return {"message": "ToolLife deleted successfully"}
