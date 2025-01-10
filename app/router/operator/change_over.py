from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database_config import get_session
from app.models import LogDevice, Machine, Recipe, ChangeOver, User
from auth import get_current_device, get_current_operator

router = APIRouter()

@router.get("/machines")
async def change_over_page(device: LogDevice = Depends(get_current_device), session: Session = Depends(get_session)):
    # Get all active machines for the current device
    machines = session.exec(select(Machine).where(Machine.id.in_(device.machines), Machine.active)).all()
    
    return {"machines": machines}

@router.get("/{machine_id}")
async def get_recipes(machine_id: int, session: Session = Depends(get_session)):
    # Get all active recipes for the selected machine
    recipes = session.exec(select(Recipe).where(Recipe.machine_id == machine_id, Recipe.active)).all()
    
    return recipes

@router.post("/")
async def perform_change_over(
    request: Request,
    current_operator: User = Depends(get_current_operator),
    device: LogDevice = Depends(get_current_device),
    session: Session = Depends(get_session)
):
    form_data = await request.form()
    machine_id = int(form_data['machine_id'])
    recipe_id = int(form_data['recipe_id'])

    # Verify that the machine belongs to the current device
    valid_machine_ids = [machine.id for machine in device.machines]
    if machine_id not in valid_machine_ids:
        raise HTTPException(status_code=400, detail="Invalid machine selection")

    # Get the selected machine and recipe
    machine = session.get(Machine, machine_id)
    recipe = session.get(Recipe, recipe_id)

    if not machine or not recipe:
        raise HTTPException(status_code=404, detail="Machine or recipe not found")

    if not machine.active or not recipe.active:
        raise HTTPException(status_code=400, detail="Machine or recipe is not active")

    # Set the new recipe as the current recipe for the machine
    machine.current_recipe_id = recipe.id
    change_over = ChangeOver(
        machine_id=machine.id,
        recipe_id=recipe.id,
        performed_by=current_operator.id
    )
    session.add(change_over)
    session.commit()

    return {"message": "Change over successful", "machine": machine.name, "recipe": recipe.name}

