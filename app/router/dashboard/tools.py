from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, and_
from typing import Dict

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Tool, RecipeTool, Recipe, ToolType


router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
)

@router.get("/", response_model=None)
async def get_tool_data(request: Request):
    return templates.TemplateResponse(
        "dashboard/tools.html.j2",
        {
            "request": request,
        }
    )


@router.get("/api/filtered")
async def get_filtered_tool_data(
    selected_operations: str = Query(''),
    selected_products: str = Query(''),
    db: Session = Depends(get_session),
) -> Dict:
    selected_operations = eval(selected_operations)
    selected_products = eval(selected_products)

    statement = select(Tool).where(Tool.active == True)

    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]
    statement = statement.where(Tool.id.in_(select(RecipeTool.tool_id).where(RecipeTool.recipe_id.in_(select(Recipe.id).where(and_(Recipe.workpiece_id.in_(selected_products), Recipe.machine_id.in_(selected_operations)))))))
    statement = statement.join(ToolType, ToolType.id == Tool.tool_type_id).order_by(ToolType.name, Tool.name)

    tools = db.exec(statement).all()
    
    flat_tools = []
    grouped_tools = {}
    for tool in tools:
        weekly_consumption = 33
        tool_dict = {
            'name': tool.name,
            'number': tool.number,
            'type': tool.tool_type.name,
            'manufacturer': tool.manufacturer.name,
            'line': tool.recipes[0].workpiece.line.name if tool.recipes else "Unknown",
            'weekly_consumption': weekly_consumption,
            'inventory': f"{tool.inventory} ({round(tool.inventory/weekly_consumption, 1) if weekly_consumption and weekly_consumption > 0 else "∞"} Weeks)" if tool.inventory else "N/A",
            'order_lead_time': "21 Weeks",
        }
        flat_tools.append(tool_dict)

        if tool.recipes and len(tool.recipes) > 0:
            recipe = tool.recipes[0]
            product = recipe.workpiece.name if recipe.workpiece and hasattr(recipe, 'workpiece') and recipe.workpiece.name else "Unknown"
            operation = recipe.machine.name if recipe.machine and hasattr(recipe, 'machine') and recipe.machine.name else "Unknown"
        else:
            product = "Unknown"
            operation = "Unknown"
        grouped_tools.setdefault(product, {}).setdefault(operation, []).append(tool_dict)
    
    table3 = []  # Placeholder for table 3 data

    return {
        "flat_tools": flat_tools,
        "grouped_tools": grouped_tools,
        "table3": table3
    }
