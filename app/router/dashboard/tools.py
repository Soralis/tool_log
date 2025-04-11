from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, and_, exists, desc, asc
from sqlalchemy.orm import selectinload
from typing import Dict
from datetime import datetime
from math import ceil

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import (Tool, RecipeTool, Recipe, ToolType, 
                        ToolConsumption, Workpiece, Machine, ChangeOver,
                        ToolPosition, Line, OrderDelivery, ToolLife,
                        OrderCompletion)
from . import tool_lifes_cards as tc
from .utils import get_condensed_data


router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
)

def aggregate_tool_metrics(aggregated: dict, line, product, machine, tool_position, tool, start_date: datetime, end_date: datetime, db: Session) -> dict:
    """
    Helper function to compute and aggregate tool metrics.
    
    Parameters:
        aggregated (dict): The aggregated results dictionary to update.
        line: Production line instance (or None for standalone tools).
        product: Product instance (or None for standalone tools).
        machine: Machine instance (or None for standalone tools).
        tool_position: ToolPosition instance if available; if None, aggregation falls back to tool-level lifespans.
        tool: The Tool instance.
        start_date (datetime): Start date for filtering.
        end_date (datetime): End date for filtering.
        db (Session): The database session.
    
    Returns:
        dict: Updated aggregated dictionary.
    """
    # Fetch consumption records for the tool in the given date range.
    consumptions = db.exec(
        select(ToolConsumption)
        .where(ToolConsumption.tool_id == tool.id)
        .where(ToolConsumption.datetime >= start_date)
        .where(ToolConsumption.datetime <= end_date)
    ).all()
    
    if consumptions:
        first_date = min(c.datetime.date() for c in consumptions)
        last_date = max(c.datetime.date() for c in consumptions)
        total_quantity = sum(c.quantity for c in consumptions)
        weeks = ((last_date - first_date).days // 7) + 1
        weekly = total_quantity / weeks if weeks > 0 else total_quantity
    else:
        total_quantity = 0
        weekly = 0

    # Calculate order delivery metrics.
    tool_orders = tool.tool_orders
    order_deliveries = db.exec(
        select(OrderDelivery)
        .where(OrderDelivery.order_id.in_([o.id for o in tool_orders]))
        .order_by(desc(OrderDelivery.delivery_date))
        .limit(10)
    ).all()
    if order_deliveries and len(order_deliveries) > 5:
        delivery_durations = [(ceil((od.delivery_date - od.order.order_date).days / 7), od.quantity) for od in order_deliveries]
        longest_delivery_duration = max(delivery_durations, key=lambda x: x[0])
    else:
        longest_delivery_duration = (14, 0)
    
    # Determine the applicable tool lifes.
    if tool_position is not None:
        lifes = [tl for tl in tool_position.tool_lifes if tl.timestamp.date() >= start_date and tl.timestamp.date() <= end_date]
    else:
        lifes = [tl for tl in tool.tool_lifes if tl.timestamp.date() >= start_date and tl.timestamp.date() <= end_date]
    
    percent_consumptions_recorded = round(100 * (len(lifes) / tool.max_uses) / total_quantity) if total_quantity else 100
    
    if lifes:
        avg_tool_life = sum(t.reached_life for t in lifes) / len(lifes) if len(lifes) > 0 else 0
        if tool_position is not None and hasattr(tool_position, 'tool_count'):
            cost_per_piece = (tool_position.tool_count * float(tool.price) / tool.max_uses) / avg_tool_life if avg_tool_life > 0 else 0
        else:
            # For standalone tools or missing tool_position, assume a tool_count of 1.
            cost_per_piece = (float(tool.price) / tool.max_uses) / avg_tool_life if avg_tool_life > 0 else 0
    else:
        cost_per_piece = 0
    
    tool_entry = {
        'tool_id': tool.id,
        'tool_name': tool.name,
        'selected': getattr(tool_position, 'selected', False),
        'active': tool.active,
        'stop_order': tool.stop_order,
        'number': tool.number,
        'type': tool.tool_type.name,
        'manufacturer': tool.manufacturer.name,
        'weekly_consumption': round(weekly, 1),
        'inventory': tool.inventory if tool.inventory else 0,
        'order_lead_time': longest_delivery_duration[0],
        'longest_order_size': longest_delivery_duration[1],
        'cost_per_piece': round(cost_per_piece, 2),
        'percent_consumptions_recorded': percent_consumptions_recorded,
    }
    
    if line is not None and product is not None and machine is not None:
        # Update aggregated dictionary for recipe-based tools.
        if line.name not in aggregated:
            aggregated[line.name] = {'id': line.id, 'products': {}}
        if product.name not in aggregated[line.name]['products']:
            aggregated[line.name]['products'][product.name] = {'id': product.id, 'operations': {}}
        if machine.name not in aggregated[line.name]['products'][product.name]['operations']:
            aggregated[line.name]['products'][product.name]['operations'][machine.name] = {'id': machine.id, 'tool_positions': {}}
        # Use tool_position name if available; otherwise, group under "Unassigned"
        position_key = tool_position.name if tool_position is not None else "Unassigned"
        if position_key not in aggregated[line.name]['products'][product.name]['operations'][machine.name]['tool_positions']:
            aggregated[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][position_key] = {'id': tool_position.id if tool_position else None, 'tools': []}
        aggregated[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][position_key]['tools'].append(tool_entry)
    else:
        # For standalone tools, update the aggregated under "Standalone Tools".
        if "Unassigned" not in aggregated:
            aggregated["Unassigned"] = {'id': None, 'products': {
                "Unassigned": {'id': None, 'operations': {
                    "Unassigned": {'id': None, 'tool_positions': {
                        "Unassigned": {'tools': []}
                    }}
                }}
            }}
            
        aggregated["Unassigned"]['products']["Unassigned"]['operations']["Unassigned"]['tool_positions']['Unassigned']['tools'].append(tool_entry)
    
    return aggregated

# Endpoint: Render tool dashboard template
@router.get("/", response_model=None)
async def get_tool_template(request: Request):
    """
    Render the dashboard tool template.

    This endpoint returns an HTML page built using a Jinja2 template that provides the
    user interface for managing and viewing tool data on the dashboard.
    
    Parameters:
        request (Request): The incoming HTTP request.

    Returns:
        TemplateResponse: Rendered HTML template with the provided request context.
    """
    return templates.TemplateResponse(
        "dashboard/tools.html.j2",
        {
            "request": request,
        }
    )

# Endpoint: Retrieve unique tool data and consumption metrics
@router.get("/api/unique_tools")
async def get_unique_tool_data(
    selected_operations: str = Query(''),
    selected_products: str = Query(''),
    start_date: datetime = Query(''),
    end_date: datetime = Query(''),
    db: Session = Depends(get_session),
) -> Dict:
    """
    Get unique tool data and consumption metrics within a given time frame.

    This endpoint aggregates tool information, calculates weekly consumption and inventory
    data for tools filtered by selected operations, products, and a date range.

    Parameters:
        selected_operations (str): A string representing a list of operation IDs.
        selected_products (str): A string representing a list of product IDs.
        start_date (datetime): Start date for filtering consumption data.
        end_date (datetime): End date for filtering consumption data.
        db (Session): Database session dependency.

    Returns:
        Dict: Dictionary of tool data keyed by tool ID, including details such as name, number, type,
              manufacturer, line, weekly consumption, inventory status, order lead time, stop order status,
              and price.
    """
    # Convert query string lists to Python objects
    selected_operations = eval(selected_operations)
    selected_products = eval(selected_products)

    start_date = start_date.date()
    end_date = end_date.date()

    # Base statement to select active tools
    statement = select(Tool).where(Tool.active == True)

    # Convert product and operation IDs to integers and filter tools based on related recipes
    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]
    statement = statement.where(
        Tool.id.in_(
            select(RecipeTool.tool_id).where(
                RecipeTool.recipe_id.in_(
                    select(Recipe.id).where(and_(
                        Recipe.workpiece_id.in_(selected_products),
                        Recipe.machine_id.in_(selected_operations)
                    ))
                )
            )
        )
    )
    # Join with ToolType and order the result for clarity
    statement = statement.join(ToolType, ToolType.id == Tool.tool_type_id).order_by(ToolType.name, Tool.name)

    db_tools = db.exec(statement).all()

    # Retrieve tool consumption records within the date range for selected tools
    statement = select(ToolConsumption).where(ToolConsumption.tool_id.in_([tool.id for tool in db_tools]))
    statement = statement.where(ToolConsumption.datetime >= start_date)
    statement = statement.where(ToolConsumption.datetime <= end_date)

    tools = {}
    # For unique tools endpoint, we simply build a dictionary keyed by tool.id
    for tool in db_tools:
        # Calculate consumption metrics similar to unique_tools endpoint logic
        first_consumption_date = end_date
        last_consumption_date = start_date
        total_consumption = 0
        tool_consumptions = db.exec(
            select(ToolConsumption)
            .where(ToolConsumption.tool_id == tool.id)
            .where(ToolConsumption.datetime >= start_date)
            .where(ToolConsumption.datetime <= end_date)
        ).all()
        for consumption in tool_consumptions:
            if consumption.datetime.date() <= first_consumption_date:
                first_consumption_date = consumption.datetime.date()
            if consumption.datetime.date() >= last_consumption_date:
                last_consumption_date = consumption.datetime.date()
            total_consumption += consumption.quantity
        weeks = (last_consumption_date - first_consumption_date).days // 7 + 1 if first_consumption_date != end_date else 1
        weekly_consumption = total_consumption / weeks if weeks > 0 else total_consumption

        tool_dict = {
            'id': tool.id,
            'name': tool.name,
            'number': tool.number,
            'type': tool.tool_type.name,
            'manufacturer': tool.manufacturer.name,
            'line': tool.recipes[0].workpiece.line.name if tool.recipes else "Unknown",
            'weekly_consumption': round(weekly_consumption, 1),
            'inventory': f"{tool.inventory} ({round(tool.inventory/weekly_consumption, 1) if weekly_consumption and weekly_consumption > 0 else '∞'} Weeks)" if tool.inventory else "N/A",
            'order_lead_time': 15,
            'stop_order': tool.stop_order,
            'price': round(tool.price, 2)
        }
        tools[tool.id] = tool_dict
    
    return tools

# Endpoint: Get CPU and tool cost metrics for recipes and standalone tools
@router.get("/api/cpu")
async def get_cpu(
    selected_operations: str = Query(''),
    selected_products: str = Query(''),
    start_date: datetime = Query(''),
    end_date: datetime = Query(''),
    db: Session = Depends(get_session),
) -> Dict:
    """
    Retrieve CPU related data for recipes and standalone tools, including tool positions and cost metrics.

    This endpoint collects recipe data for active recipes that experienced a changeover within
    the specified date range and calculates consumption and cost metrics for tools. It also includes
    tools that are not part of any recipe but have consumption records in the given time frame.

    Parameters:
        selected_operations (str): A string representing a list of operation IDs.
        selected_products (str): A string representing a list of product IDs.
        start_date (datetime): Start date for filtering recipes and consumptions.
        end_date (datetime): End date for filtering recipes and consumptions.
        db (Session): Database session dependency.

    Returns:
        Dict: A nested dictionary structure organizing tool data and cost metrics by production line,
              product, and operation for recipe-based tools, and a separate section for standalone tools.
    """
    # Convert query parameters.
    selected_operations = eval(selected_operations)
    selected_products = eval(selected_products)
    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]

    start_date = start_date.date()
    end_date = end_date.date()

    aggregated = {}

    # Process recipe-based tools.
    statement = select(Recipe).where(Recipe.active == True)
    statement = statement.where(Recipe.machine_id.in_(selected_operations))
    statement = statement.where(Recipe.workpiece_id.in_(selected_products))
    statement = statement.where(exists()
                                .where(Recipe.id == ChangeOver.recipe_id)
                                .where(ChangeOver.timestamps >= start_date)
                                .where(ChangeOver.timestamps <= end_date))
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

    for recipe in db_recipes:
        # For each recipe, process each tool_position.
        for tool_position in recipe.tool_positions:
            # Call the helper to update the aggregated dictionary.
            aggregated = aggregate_tool_metrics(aggregated, recipe.machine.line, recipe.workpiece, recipe.machine, tool_position, tool_position.tool, start_date, end_date, db)

    # Process standalone tools (tools without any associated recipes).
    standalone_statement = select(Tool).where(Tool.active == True)
    # Exclude tools that are already processed through recipes.
    standalone_tools = []
    all_recipe_tool_ids = {tool_id for tool_id in db.exec(
        select(RecipeTool.tool_id)
    ).all()}
    for tool in db.exec(standalone_statement).all():
        if tool.id not in all_recipe_tool_ids:
            # Check if the tool has consumption records in the given time frame.
            tool_consumptions = db.exec(
                select(ToolConsumption)
                .where(ToolConsumption.tool_id == tool.id)
                .where(ToolConsumption.datetime >= start_date)
                .where(ToolConsumption.datetime <= end_date)
            ).all()
            if tool_consumptions:
                standalone_tools.append(tool)
    
    # For standalone tools, add them under the "Standalone Tools" key in aggregated.
    for tool in standalone_tools:
        aggregated = aggregate_tool_metrics(aggregated, None, None, None, None, tool, start_date, end_date, db)
    
    # Additional aggregation steps for overall cost per piece.
    for line in aggregated.values():
        for product in line.get("products", {}).values():
            product_cpp = 0
            for machine in product["operations"].values():
                machine_cpp = 0
                for tool_position in machine['tool_positions'].values():
                    tool_position_cpp = 0
                    total_consumption = 0
                    for tool in tool_position['tools']:
                        total_consumption += tool['weekly_consumption']
                        tool_position_cpp += tool['cost_per_piece'] * tool['weekly_consumption']
                    tool_position['cost_per_piece'] = round(tool_position_cpp / total_consumption if total_consumption > 0 else 0, 2)
                    machine_cpp += tool_position['cost_per_piece']
                machine['cost_per_piece'] = round(machine_cpp, 2)
                product_cpp += machine_cpp
            product['cost_per_piece'] = round(product_cpp, 2)

    return aggregated


async def tool_info(tool_id:int, start_date:datetime, end_date:datetime, db):
    """
    Retrieve detailed information about a specific tool, including its consumption history,
    tool life records, and related recipes.

    Parameters:
        tool_id (int): The ID of the tool to retrieve information for.
        start_date (datetime): Start date for filtering consumption data.
        end_date (datetime): End date for filtering consumption data.
        db (Session): Database session dependency.

    Returns:
        dict: A dictionary containing detailed information about the specified tool.
    """
    # Fetch the tool by its ID
    tool = db.exec(select(Tool).where(Tool.id == tool_id)).first()
    if not tool:
        return {"error": "Tool not found."}

    # Fetch consumption records for the specified date range
    consumptions = db.exec(
        select(ToolConsumption)
        .where(ToolConsumption.tool_id == tool.id)
        .where(ToolConsumption.datetime >= start_date)
        .where(ToolConsumption.datetime <= end_date)
        .order_by(asc(ToolConsumption.datetime))
    ).all()

    # Fetch tool life records
    lifes = db.exec(
        select(ToolLife)
        .where(ToolLife.tool_id == tool.id)
        .where(ToolLife.timestamp >= start_date)
        .where(ToolLife.timestamp <= end_date)
        .order_by(asc(ToolLife.timestamp))
    ).all()

    # Fetch related recipes
    recipes = db.exec(
        select(Recipe)
        .join(RecipeTool, RecipeTool.recipe_id == Recipe.id)
        .where(RecipeTool.tool_id == tool.id)
    ).all()

    return {
            "id": tool.id,
            "name": tool.name,
            "number": tool.number,
            "type": tool.tool_type.name,
            "manufacturer": tool.manufacturer.name,
            "price": round(tool.price, 2),
            "inventory": tool.inventory,
            "stop_order": tool.stop_order,
            "active": tool.active,
            "consumptions": [{"datetime": c.datetime, "quantity": c.quantity} for c in consumptions],
            "prices": [{"datetime": c.datetime, "price": c.price} for c in consumptions],
            "lifes": [{"timestamp": life.timestamp, "reached_life": life.reached_life} for life in lifes],
            "workpieces": {r.workpiece.name for r in recipes},
    }


# Endpoint: Retrieve detailed information about a specific tool
@router.get("/api/target_info")
async def get_target_info(
    request: Request,
    target_type: str = Query(''),
    target_id: int = Query(''),
    start_date: datetime = Query(''),
    end_date: str = Query(''),
    db: Session = Depends(get_session),
) -> dict:
    """
    Retrieve detailed information about a specific tool.

    This endpoint fetches consumption history, tool life records, and related recipes
    for the specified tool within the given date range.

    Parameters:
        request (Request): The incoming HTTP request.
        tool_id (int): The ID of the tool to retrieve information for.
        start_date (datetime): Start date for filtering consumption data.
        end_date (datetime): End date for filtering consumption data.
        db (Session): Database session dependency.

    Returns:
        dict: A dictionary containing detailed information about the specified tool.
    """
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else datetime.now()

    production = db.exec(
        select(OrderCompletion)
        .where(OrderCompletion.date >= start_date)
        .where(OrderCompletion.date <= end_date)
        .order_by(asc(OrderCompletion.date))
    ).all()

    details = {
        "title": "",
        "cards": []
    }

    match target_type:
        case "tool":
            tool = await tool_info(target_id, start_date, end_date, db)
            tool['consumptions'] = get_condensed_data(tool['consumptions'], 50, 'datetime', 'quantity')
            tool['prices'] = get_condensed_data(tool['prices'], 50, 'datetime', 'price')
            tool['lifes'] = get_condensed_data(tool['lifes'], 50, 'timestamp', 'reached_life')
            details["title"] = f"{tool['name']} (#{tool['number']})"
            series = [
                {
                    "name": "Consumption",
                    "type": "line",
                    "smooth": True,
                    "data": [[consumption[0], consumption[1]] for consumption in tool['consumptions']],
                },
                {
                    "name": "Price",
                    "type": "line",
                    "smooth": True,
                    "yAxisIndex": 1,
                    "data": [[price[0], price[1]] for price in tool['prices']],
                },
            ]
            y_axises = [
                {
                    "name": "Consumption",
                    "type": "value",
                    "position": "left",
                    "alignTicks": True,
                    "axisLine": {
                        "show": True,
                    },
                    "axisLabel": {
                        "formatter": '{value} pcs'
                    }
                },
                {
                    "name": "Price",
                    "type": "value",
                    "position": "right",
                    # "offset": 80,
                    "alignTicks": True,
                    "axisLine": {
                        "show": True,
                    },
                    "axisLabel": {
                        "formatter": '${value}'
                    }
                },
            ]
            details['cards'].append(tc.graph_card(details["title"], series, yAxis=y_axises))

            
        
        case "position":
            tool_position_id = target_id

        case "operation":
            operation_id = target_id

        case "product":
            product_id = target_id





    return details
