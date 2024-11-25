# app/main.py
from fastapi import APIRouter, Request, Depends, Response, status
from fastapi.responses import HTMLResponse
from fastapi.exceptions import HTTPException
from app.templates.jinja_functions import templates
from sqlmodel import Session, select
from sqlalchemy.orm import aliased
from app.models import Recipe, RecipeRead, ToolType, ToolPosition, ToolAttribute
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
                'name': f'{tool.name} ({manufacturer.name})',
                'type': tool_type.name,  # Add tool type separately
                'attributes': []
            }
        
        tools_dict[tool.id]['attributes'].append({
            'name': attribute.name,
            'unit': attribute.unit
        })

    return tools_dict

@router.get("/{recipe_id}")
async def get_recipe(recipe_id: int, session: Session = Depends(get_session)):
    # Query for the recipe
    recipe_query = select(Recipe).where(Recipe.id == recipe_id)
    recipe = session.exec(recipe_query).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Query for all tool positions
    tool_positions_query = select(ToolPosition).where(
        ToolPosition.recipe_id == recipe_id,
        ToolPosition.active
    )
    tool_positions = session.exec(tool_positions_query).all()

    # Convert to dict for JSON response
    recipe_dict = {
        "id": recipe.id,
        "name": recipe.name,
        "description": recipe.description,
        "workpiece_id": recipe.workpiece_id,
        "machine_id": recipe.machine_id,
        "tool_positions": []
    }

    # Add tool positions with their settings
    for tp in tool_positions:
        tp_dict = {
            "id": tp.id,  # Include the ID
            "name": tp.name,
            "tool_id": tp.tool_id,
            "expected_life": tp.expected_life,
            "tool_settings": tp.tool_settings,
            "selected": tp.selected
        }
        recipe_dict["tool_positions"].append(tp_dict)

    return recipe_dict

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

    # Create tool positions with active state
    tool_positions = body['tool_positions']
    for tp in tool_positions:
        tp['tool_id'] = int(tp['tool_id'])
        tp['recipe_id'] = db_recipe.id
        db_tp = ToolPosition.model_validate(tp)
        session.add(db_tp)
    session.commit()

    return {"message": "Recipe created successfully", "recipe_id": db_recipe.id}

@router.put("/{recipe_id}")
async def update_recipe(
    recipe_id: int,
    request: Request,
    session: Session = Depends(get_session)
):
    # Get the recipe
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Get the update data
    body = await request.json()
    recipe_data = body['recipe']
    
    # Update recipe fields
    for key, value in recipe_data.items():
        if key != 'id':  # Don't update the ID
            setattr(recipe, key, value)
    
    # Get existing tool positions
    tool_positions_query = select(ToolPosition).where(
        ToolPosition.recipe_id == recipe_id
    )
    existing_positions = session.exec(tool_positions_query).all()
    
    # Create a set of submitted position IDs
    submitted_position_ids = {int(tp.get('id')) for tp in body['tool_positions'] if tp.get('id')}
    
    # Delete positions that aren't in the submitted data
    for existing_pos in existing_positions:
        if existing_pos.id not in submitted_position_ids:
            try:
                session.delete(existing_pos)
                session.commit()
            except:
                session.rollback()
                existing_pos.active = False
                session.commit()
        else:
            existing_pos.active = True
            existing_pos.selected = False
            session.commit()
    
    # Update or create tool positions
    for tp in body['tool_positions']:
        tp['tool_id'] = int(tp['tool_id'])
        tp['recipe_id'] = recipe_id
        
        if tp.get('id'):  # Update existing position
            position = session.get(ToolPosition, tp['id'])
            if position:
                for key, value in tp.items():
                    if key != 'id':
                        setattr(position, key, value)
        else:  # Create new position
            db_tp = ToolPosition.model_validate(tp)
            session.add(db_tp)
    
    session.commit()
    return {"message": "Recipe updated successfully"}

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
