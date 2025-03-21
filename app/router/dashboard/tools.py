from fastapi import APIRouter, Depends, Request, Query
from sqlmodel import Session, select, and_, exists, desc
from sqlalchemy.orm import selectinload
from typing import Dict
from datetime import datetime, timedelta
from math import ceil

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import (Tool, RecipeTool, Recipe, ToolType, 
                        ToolConsumption, Workpiece, Machine, ChangeOver,
                        ToolPosition, Line, OrderDelivery, ToolLife,
                        OrderCompletion)


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
            'order_lead_time': 15,
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
    operations_total = {}
    for recipe in db_recipes:
        tool_positions_total = {}
        for tool_position in recipe.tool_positions:
            if tool_position.name not in tool_positions_total:
                tool_positions_total[tool_position.name] = {}

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
                return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][tool_position.name] = {'tools': []}
            tp = return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][tool_position.name]['tools']

            consumptions = db.exec(select(ToolConsumption)
                 .where(ToolConsumption.tool_id == tool_position.tool.id)
                 .where(ToolConsumption.datetime >= start_date)
                 .where(ToolConsumption.datetime <= end_date)
                 ).all()
            if consumptions:
                first_date = min([c.datetime.date() for c in consumptions])
                last_date = max([c.datetime.date() for c in consumptions])
                total_quantity = sum([c.quantity for c in consumptions])
                weeks = ((last_date - first_date).days // 7) + 1
                weekly = total_quantity / weeks if weeks > 0 else total_quantity
            else:
                total_quantity = 0
                weekly = 0
            tool_positions_total[tool_position.name][tool_position.tool.name] = {}
            tool_positions_total[tool_position.name][tool_position.tool.name]["total_quantity"] = total_quantity

            tool_orders = tool_position.tool.tool_orders
            order_deliveries = db.exec(select(OrderDelivery)
                 .where(OrderDelivery.order_id.in_([o.id for o in tool_orders]))
                 .order_by(desc(OrderDelivery.delivery_date))
                 .limit(10)
                 ).all()
            if order_deliveries and len(order_deliveries) > 5:
                delivery_durations = [ (ceil((od.delivery_date - od.order.order_date).days / 7), od.quantity) for od in order_deliveries ]
                # find longest delivery_duration in weeks and corresponding quantity
                longest_delivery_duration = max(delivery_durations, key=lambda item: item[0])
            else:
                longest_delivery_duration = (14, 0)

            tool_lifes = [tl for tl in tool_position.tool_lifes if tl.timestamp.date() >= start_date and tl.timestamp.date() <= end_date]
            percent_consumptions_recorded = round(100 * (len(tool_lifes) / tool_position.tool.max_uses) / total_quantity) if total_quantity else 100

            if tool_lifes:
                avg_tool_life = sum([t.reached_life for t in tool_lifes]) / len(tool_lifes) if len(tool_lifes) > 0 else 0
                cost_per_piece = (tool_position.tool_count * float(tool_position.tool.price) / tool_position.tool.max_uses) / avg_tool_life if avg_tool_life > 0 else 0
            else:
                cost_per_piece = 0
            
            tool_positions_total[tool_position.name][tool_position.tool.name]["cost_per_piece"] = cost_per_piece
            
            # offset = timedelta(days=0)
            # order_completions = db.exec(select(OrderCompletion)
            #      .where(OrderCompletion.workpiece_id == recipe.workpiece_id)
            #      .where(OrderCompletion.date >= start_date + offset)
            #      .where(OrderCompletion.date <= end_date + offset)
            #      ).all()
            # if order_completions:
            #     total_value = sum([oc.value for oc in order_completions])
            # else:
            #     total_value = 0

            # cost_per_piece = total_value / total_quantity if total_quantity > 0 else 0
            
            tool_dict = {
                'tool_id': tool_position.tool_id,
                'tool_name': tool_position.tool.name,
                'selected': tool_position.selected,
                'active': tool_position.tool.active,
                'stop_order': tool_position.tool.stop_order,
                'number': tool_position.tool.number,
                'type': tool_position.tool.tool_type.name,
                'manufacturer': tool_position.tool.manufacturer.name,
                'weekly_consumption': round(weekly, 1),
                'inventory': tool_position.tool.inventory if tool_position.tool.inventory else 0,
                'order_lead_time': longest_delivery_duration[0],
                'longest_order_size': longest_delivery_duration[1],
                # 'last_price': round(tool_position.tool.price, 2),
                'cost_per_piece': round(cost_per_piece, 2),
                'percent_consumptions_recorded': percent_consumptions_recorded,
            }
            tp.append(tool_dict)
        
        for position in tool_positions_total:
            total_quantity = sum([p['total_quantity'] for p in tool_positions_total[position].values()])
            cumulated_cost_per_piece = sum([p['total_quantity'] * p['cost_per_piece'] for p in tool_positions_total[position].values()])
            return_data[line.name]['products'][product.name]['operations'][machine.name]['tool_positions'][position]['cost_per_piece'] = round(cumulated_cost_per_piece / total_quantity, 2) if total_quantity > 0 else 0

    for line in return_data.values():
        for product in line["products"].values():
            product_cpp = 0
            for machine in product["operations"].values():
                machine_cpp = 0
                for tool_position in machine['tool_positions'].values():
                    machine_cpp += tool_position['cost_per_piece']
                machine['cost_per_piece'] = round(machine_cpp, 2)
                product_cpp += machine_cpp
            product['cost_per_piece'] = round(product_cpp, 2)
    
    return return_data
