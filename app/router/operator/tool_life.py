from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from auth import get_current_operator

from app.database_config import get_db
from app.models.all_models import ToolLife, Machine, Recipe, Tool, ToolPosition, ChangeReason, ToolLifeCreate, LogDevice, User

router = APIRouter()

@router.get("/")
async def get_tool_life_data(machine_id: int, 
                             db: Session = Depends(get_db)):
    
    machine: Machine = db.exec(select(Machine)
                      .where(Machine.id == machine_id)
                    #   .options(joinedload(Machine.measureables))
                      ).unique().one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found or ambiguous")

    current_recipe = machine.current_recipe
    if not current_recipe:
        raise HTTPException(status_code=404, detail="No current recipe for this machine")

    tool_positions = [position for position in current_recipe.tool_positions if position.active]
    measureables = [measureable for measureable in machine.measureables if measureable.active]

    print('machine', machine)
    print('current_recipe', current_recipe)
    print('tool_positions', tool_positions)
    print('measureables', measureables)

    return {
        "machine": machine,
        "current_recipe": current_recipe,
        "tool_positions": tool_positions,
        "measureables": measureables
    }


@router.get("/change-reasons")
async def get_change_reasons(
    tool_position_id: int,
    db: Session = Depends(get_db)
):
    tool_position = db.exec(select(ToolPosition).where(ToolPosition.id == tool_position_id)).first()
    if not tool_position:
        raise HTTPException(status_code=404, detail="Tool position not found")

    tool = tool_position.tool
    if not tool:
        raise HTTPException(status_code=404, detail="No tool associated with this position")

    change_reasons = db.exec(select(ChangeReason).where(ChangeReason.tool_type_id == tool.tool_type_id)).all()

    return {
        "change_reasons": change_reasons
    }


@router.post("/")
async def create_tool_life(
    request: Request,
    db: Session = Depends(get_db),
    current_operator: User = Depends(get_current_operator)
):
    form_data: dict = await request.json()

    toolposition: ToolPosition = db.exec(select(ToolPosition)
                           .where(ToolPosition.id == int(form_data.pop('tool_position_id')))
                           ).one_or_none()

    machine: Machine = db.exec(select(Machine)
                           .where(Machine.id == int(form_data.pop('machine_id')))
                           ).one_or_none()

    try:
        db_tool_life = ToolLife(
            created_by = current_operator.id,
            reached_life = int(form_data.pop('reached_life')),
            tool_settings = toolposition.tool_settings,
            machine_id = machine.id,
            machine_channel = int(form_data.pop('machine_channel')),
            recipe_id = machine.current_recipe_id,
            tool_position_id = toolposition.id,
            tool_id = toolposition.tool_id,
            change_reason_id = int(form_data.pop('change_reason_id')),
            )
        
        additional_measurements = {}
        for key, value in form_data.items():
            if key.endswith('_ms'):
                additional_measurements[key.rstrip('_ms')] = value

        db_tool_life.additional_measurements = additional_measurements

        db.add(db_tool_life)
        db.commit()
        db.refresh(db_tool_life)
        return db_tool_life
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))