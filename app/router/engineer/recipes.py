# app/main.py
from fastapi import APIRouter, Request, Depends
from app.templates.jinja_functions import templates
from sqlmodel import Session, select
from typing import List
from app.models import Recipe, RecipeCreate, ToolPosition, ToolPositionCreate, ToolSettings, ToolSettingsCreate
from app.models import Workpiece
from app.models import Machine
from app.models import Tool
from app.database_config import get_session

router = APIRouter()

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
            request=request,
            name="engineer/recipes.html.j2",
        )

@router.get("/workpieces")
async def get_workpieces(q: str = "", session: Session = Depends(get_session)):
    query = select(Workpiece)
    if q:
        query = query.where(Workpiece.name.contains(q))
    workpieces = session.exec(query).all()
    return workpieces

@router.get("/machines")
async def get_machines(q: str = "", session: Session = Depends(get_session)):
    query = select(Machine)
    if q:
        query = query.where(Machine.name.contains(q))
    machines = session.exec(query).all()
    return machines

@router.get("/tools")
async def get_tools(q: str = "", session: Session = Depends(get_session)):
    query = select(Tool)
    if q:
        query = query.where(Tool.name.contains(q))
    tools = session.exec(query).all()
    return tools

@router.post("/recipes")
async def create_recipe(
    recipe: RecipeCreate,
    tool_positions: List[ToolPositionCreate],
    tool_settings: List[List[ToolSettingsCreate]],
    session: Session = Depends(get_session)
):
    db_recipe = Recipe.model_validate(recipe)
    session.add(db_recipe)
    session.commit()
    session.refresh(db_recipe)

    for i, tp in enumerate(tool_positions):
        db_tp = ToolPosition.model_validate(tp)
        db_tp.recipe_id = db_recipe.id
        session.add(db_tp)
        session.commit()
        session.refresh(db_tp)

        for ts in tool_settings[i]:
            db_ts = ToolSettings.model_validate(ts)
            db_ts.tool_position_id = db_tp.id
            session.add(db_ts)
            session.commit()
            session.refresh(db_ts)

    return {"message": "Recipe created successfully", "recipe_id": db_recipe.id}

