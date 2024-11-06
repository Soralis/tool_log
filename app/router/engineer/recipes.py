# app/main.py
from fastapi import APIRouter, Request, Depends, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from app.templates.jinja_functions import templates
from sqlmodel import Session, select
from sqlalchemy.orm import aliased
from app.models import Recipe, RecipeRead, ToolType, ToolPosition, ToolAttribute #,ToolSettings, ToolSettingsCreate, 
from app.models import Workpiece
from app.models import Machine
from app.models import Tool
from app.models import Manufacturer
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
    # Create an alias for the ToolAttribute table
    ToolAttributeAlias = aliased(ToolAttribute)

    # Create the query
    query = (
        select(Tool, ToolType, ToolAttributeAlias, Manufacturer)
        .join(ToolType, Tool.tool_type_id == ToolType.id)
        .join(ToolAttributeAlias, ToolType.id == ToolAttributeAlias.tool_type_id)
        .join(Manufacturer, Tool.manufacturer_id == Manufacturer.id)
    )

    # Execute the query
    result = session.exec(query).fetchall()

    # Process the result
    tools_dict = {}
    for tool, tool_type, attribute, manufacturer in result:
        if tool.id not in tools_dict:
            tools_dict[tool.id] = {
                'name': f'{tool.name} ({tool_type.name}, {manufacturer.name})',
                'attributes': []
            }
        
        tools_dict[tool.id]['attributes'].append({
            'name': attribute.name,
            'unit': attribute.unit
        })

    return tools_dict

@router.post("/")
async def create_recipe(
    request: Request,
    session: Session = Depends(get_session)
):
    body = await request.json()
    db_recipe = Recipe.model_validate(body['recipe'])
    session.add(db_recipe)
    session.commit()
    session.refresh(db_recipe)

    tool_positions = body['tool_positions']
    for i, tp in enumerate(tool_positions):
        tp['tool_id'] = int(tp['tool_id'])
        tp['recipe_id'] = db_recipe.id
        db_tp = ToolPosition.model_validate(tp)
        session.add(db_tp)
        session.commit()
        session.refresh(db_tp)

    return {"message": "Recipe created successfully", "recipe_id": db_recipe.id}

@router.get("/list", response_class=HTMLResponse)
async def get_item_list(request: Request,
                        session: Session = Depends(get_session)
                        ):
    filters = request.query_params
    statement = select(Recipe)

    # Apply filters to the statement
    for key, value in filters.items():
        if value and key != 'with_filter':
            statement = statement.where(getattr(Recipe, key).in_(value.split(',')))

    items = session.exec(statement).fetchall()

    # For full page load, return the complete template
    return templates.TemplateResponse(
        request=request,
        name="engineer/partials/list.html.j2",
        context={"items": items, 'item_type': 'Recipe', 'read_model': RecipeRead}
    )

@router.delete("/{item_id}")
def delete_item(item_id: int,
                session: Session = Depends(get_session)
                ):
    statement = select(Recipe).where(Recipe.id == item_id)
    item = session.exec(statement).one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Recipe not found")
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)