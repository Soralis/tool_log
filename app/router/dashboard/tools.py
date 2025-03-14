from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, and_, exists
from sqlalchemy.orm import selectinload
from typing import Dict, Optional
from datetime import datetime

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import (Tool, RecipeTool, Recipe, ToolType, 
                        ToolConsumption, Workpiece, Machine, ChangeOver,
                        ToolPosition, Line)


router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
)

@router.get("/", response_model=None)
async def get_tool_template(request: Request):
    return templates.TemplateResponse(
        "dashboard/tools.html.j2",
        {
            "request": request,
        }
    )


@router.get("/api/unique_tools")
async def get_unique_tool_data(
    selected_operations: str = Query(''),
    selected_products: str = Query(''),
    start_date: datetime = Query(''),
    end_date: datetime = Query(''),
    db: Session = Depends(get_session),
) -> Dict:
    selected_operations = eval(selected_operations)
    selected_products = eval(selected_products)

    start_date = start_date.date()
    end_date = end_date.date()

    statement = select(Tool).where(Tool.active == True)

    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]
    statement = statement.where(Tool.id.in_(select(RecipeTool.tool_id).where(RecipeTool.recipe_id.in_(select(Recipe.id).where(and_(Recipe.workpiece_id.in_(selected_products), Recipe.machine_id.in_(selected_operations)))))))
    statement = statement.join(ToolType, ToolType.id == Tool.tool_type_id).order_by(ToolType.name, Tool.name)

    db_tools = db.exec(statement).all()

    statement = select(ToolConsumption).where(ToolConsumption.tool_id.in_([tool.id for tool in db_tools]))
    statement = statement.where(ToolConsumption.datetime >= start_date)
    statement = statement.where(ToolConsumption.datetime <= end_date)

    weeks = (end_date - start_date).days // 7
        
    tool_consumptions = db.exec(statement).all()
    
    tools = {}
    for tool in db_tools:
        tool: Tool
        first_consumption_date = end_date
        last_consumption_date = start_date
        total_consumption = 0
        for consumption in tool_consumptions:
            if consumption.tool_id == tool.id:
                if consumption.datetime.date() <= first_consumption_date:
                    first_consumption_date = consumption.datetime.date()
                if consumption.datetime.date() >= last_consumption_date:
                    last_consumption_date = consumption.datetime.date()
                total_consumption += consumption.quantity
        weeks = (last_consumption_date - first_consumption_date).days // 7 + 1 if first_consumption_date != end_date else 1
        weekly_consumption = total_consumption / weeks if weeks > 0 else total_consumption

        tool_dict = {
            'name': tool.name,
            'number': tool.number,
            'type': tool.tool_type.name,
            'manufacturer': tool.manufacturer.name,
            'line': tool.recipes[0].workpiece.line.name if tool.recipes else "Unknown",
            'weekly_consumption': round(weekly_consumption,1),
            'inventory': f"{tool.inventory} ({round(tool.inventory/weekly_consumption, 1) if weekly_consumption and weekly_consumption > 0 else "∞"} Weeks)" if tool.inventory else "N/A",
            'order_lead_time': "21 Weeks",
            'stop_order': tool.stop_order,
            'price': round(tool.price, 2)
        }
        tools[tool.id] = tool_dict
    
    return tools


@router.get("/api/cpu")
async def get_cpu(
    selected_operations: str = Query(''),
    selected_products: str = Query(''),
    start_date: datetime = Query(''),
    end_date: datetime = Query(''),
    db: Session = Depends(get_session),
) -> Dict:
    selected_operations = eval(selected_operations)
    selected_products = eval(selected_products)
    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]

    start_date = start_date.date()
    end_date = end_date.date()

    # Get all recipes that had a changeover to in the given time frame
    statement = select(Recipe).where(Recipe.active == True)
    
    statement = statement.where(Recipe.machine_id.in_(selected_operations))
    statement = statement.where(Recipe.workpiece_id.in_(selected_products))
    statement = statement.where(exists()
                                .where(Recipe.id == ChangeOver.recipe_id)
                                .where(ChangeOver.timestamps >= start_date)
                                .where(ChangeOver.timestamps <= end_date))
    # Get all their ToolPositions too
    statement = statement.options(
                    selectinload(Recipe.machine),
                    selectinload(Recipe.tool_positions).options(
                        selectinload(ToolPosition.tool)))
    statement = (statement
                 .join(Machine, Machine.id == Recipe.machine_id)
                 .join(Line, Line.id == Machine.line_id)
                 .join(Workpiece, Workpiece.id == Recipe.workpiece_id)
                 .order_by(Line.name, Workpiece.name, Machine.name))

    db_recipes = db.exec(statement).all()

    return_data = {}
    for recipe in db_recipes:
        for tool_position in recipe.tool_positions:
            line = recipe.machine.line
            if line.name not in return_data:
                return_data[line.name] = {
                    'id': line.id,
                    'products': {}
                }
            product = recipe.workpiece
            if product.name not in return_data[line.name]['products']:
                return_data[line.name]['products'][product.name] = {
                    'id': product.id,
                    'operations': {}
                }
            machine = recipe.machine
            if machine.name not in return_data[line.name]['products'][product.name]['operations']:
                return_data[line.name]['products'][product.name]['operations'][machine.name] = {
                    'id': machine.id,
                    'tool_positions': {}
                }
            if tool_position.name not in return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions']:
                return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][tool_position.name] = []
            tp = return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][tool_position.name]
            
            tool_dict = {
                'tool_id': tool_position.tool_id,
                'tool_name': tool_position.tool.name,
                'selected': tool_position.selected,
                'active': tool_position.tool.active,
                'stop_order': tool_position.tool.stop_order,
                'number': tool_position.tool.number,
                'type': tool_position.tool.tool_type.name,
                'manufacturer': tool_position.tool.manufacturer.name,
                'weekly_consumption': 'NOT CALCULATED',
                'inventory': tool_position.tool.inventory,
                'order_lead_time': '21 weeks',
                'last_price': round(tool_position.tool.price, 2),
            }
            tp.append(tool_dict)
    print(return_data)
    return return_data
