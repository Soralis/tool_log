from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from auth import get_current_operator, get_current_device

from datetime import datetime, timedelta

from app.database_config import get_session
from app.models import ToolLife, Machine, ToolPosition, ChangeReason, User, LogDevice, Recipe, Note

router = APIRouter()

@router.get("/")
async def get_tool_life_data(machine_id: int, 
                             db: Session = Depends(get_session)):
    
    machine: Machine = db.exec(select(Machine)
                      .where(Machine.id == machine_id)
                    #   .options(joinedload(Machine.measureables))
                      ).unique().one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found or ambiguous")

    current_recipe = machine.current_recipe
    if not current_recipe:
        raise HTTPException(status_code=404, detail="No current recipe for this machine")

    time_threshold = datetime.now() - timedelta(minutes=15)
    recent_tool_lives = db.exec(
        select(ToolLife)
        .where(ToolLife.machine_id == machine.id)
        .where(ToolLife.recipe_id == current_recipe.id)
        .where(ToolLife.timestamp >= time_threshold)
    ).all()

    recent_tool_lives = [{"machine_channel": tl.machine_channel, "tool_position_id": tl.tool_position_id} for tl in recent_tool_lives if tl.tool_position.selected]

    tool_positions = [position for position in current_recipe.tool_positions if position.selected]
    measureables = [measureable for measureable in machine.measureables if measureable.active]

    return {
        "machine": machine,
        "current_recipe": current_recipe,
        "tool_positions": tool_positions,
        "measureables": measureables,
        "recent_tool_lives": recent_tool_lives
    }

@router.get("/change-reasons")
async def get_change_reasons(
    tool_position_id: int,
    db: Session = Depends(get_session)
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
async def log_tool_life(
    request: Request,
    current_operator: User = Depends(get_current_operator),
    device: LogDevice = Depends(get_current_device),
    session: Session = Depends(get_session)
):
    form_data = await request.json()

    machine_id = int(form_data['machine_id'])
    tool_position_id = int(form_data['tool_position_id'])
    change_reason_id = int(form_data['change_reason_id'])
    reached_life = int(form_data['reached_life'])

    # Get machine and verify it belongs to the device
    machine = session.get(Machine, machine_id)
    if not machine or machine.id not in [m.id for m in device.machines]:
        raise HTTPException(status_code=400, detail="Invalid machine selection")

    # Get tool position with recipe loaded
    tool_position = session.exec(
        select(ToolPosition)
        .where(ToolPosition.id == tool_position_id)
        .options(
            selectinload(ToolPosition.recipe).selectinload(Recipe.workpiece),
            selectinload(ToolPosition.recipe).selectinload(Recipe.workpiece_group)
        )
    ).first()
    
    if not tool_position:
        raise HTTPException(status_code=404, detail="Tool position not found")

    # Determine workpiece_id or workpiece_group_id from the recipe
    workpiece_id = None
    workpiece_group_id = None
    if tool_position.recipe:
        workpiece_id = tool_position.recipe.workpiece_id
        workpiece_group_id = tool_position.recipe.workpiece_group_id

    # Create tool life record
    tool_life = ToolLife(
        tool_id=tool_position.tool_id,
        tool_position_id=tool_position_id,
        recipe_id=tool_position.recipe_id,
        machine_id=machine_id,
        user_id=current_operator.id,
        change_reason_id=change_reason_id,
        reached_life=reached_life,
        machine_channel=int(form_data.get('machine_channel', 0)),
        tool_settings=tool_position.tool_settings,
        tool_count=tool_position.tool_count,
        cycle_time=tool_position.recipe.cycle_time if tool_position.recipe else None,
        workpiece_id=workpiece_id,
        workpiece_group_id=workpiece_group_id
    )

    session.add(tool_life)
    session.commit()

    # Get the workpiece/group name for the response
    workpiece_name = 'N/A'
    if tool_position.recipe:
        if tool_position.recipe.workpiece:
            workpiece_name = tool_position.recipe.workpiece.name
        elif tool_position.recipe.workpiece_group:
            workpiece_name = tool_position.recipe.workpiece_group.name

    return {
        "message": "Tool life logged successfully",
        "tool_position": tool_position.name,
        "reached_life": reached_life,
        "workpiece": workpiece_name
    }
