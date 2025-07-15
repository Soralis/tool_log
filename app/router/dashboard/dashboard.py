from fastapi import APIRouter, Request, Depends, Query, WebSocket
from typing import List
import json
from sqlmodel import Session, select, func, and_
from datetime import datetime, timedelta
from app.broadcast import broadcast

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Recipe, ChangeOver, Tool, ToolOrder, OrderDelivery, Line
from collections import defaultdict

router = APIRouter()


@router.get("/api/filter-options")
async def get_filter_options(request: Request, db: Session = Depends(get_session)):
    """Get available filter options (lines, products, and operations)"""
    # Fetch lines
    lines_db = db.exec(select(Line)).all()
    lines = [{ "id": l.id, "name": l.name } for l in lines_db]
    
    # Fetch products with associated line
    products_db = db.exec(select(Workpiece)).all()
    products = [{ "id": wp.id, "name": wp.name, "line_id": wp.line_id } for wp in products_db]

    # Fetch operations with associated line
    operations_db = db.exec(select(Machine)).all()
    operations = [{ "id": m.id, "name": m.name, "line_id": m.line_id } for m in operations_db]
    
    return {
        "lines": lines,
        "products": products,
        "operations": operations
    }

@router.get("/")
async def dashboard(request: Request):
    """Render the main dashboard page"""
    return templates.TemplateResponse(
        "dashboard/index.html.j2",
        {
            "request": request,
        }
    )

@router.get("/api/filter")
async def get_dashboard_filter(request: Request, 
                              db: Session = Depends(get_session),
                              selected_products: List[int] = Query(None),
                              selected_operations: List[int] = Query(None),
                              start_date: str = Query(None),
                              end_date: str = Query(None)):
    """Get filtered dashboard content"""
    # Construct query with filters
    query = select(ToolConsumption)
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    
    data = db.exec(query).all()
    
    return templates.TemplateResponse("dashboard/partials/cards.html.j2", {
        "request": request,
        "data": data,
        "selected_products": selected_products or [],
        "selected_operations": selected_operations or []
    })


@router.websocket("/ws/machine_status")
async def machine_status_websocket(websocket: WebSocket):
    """WebSocket endpoint for machine status updates"""
    await websocket.accept()
    # Send initial data to the client
    session = next(get_session())
    machines = session.exec(select(Machine)).all()

    # get the most current changeover for each machine
    subq = (select(ChangeOver.machine_id,
            func.max(ChangeOver.timestamps).label("max_timestamp")
        )
            .group_by(ChangeOver.machine_id)
            .subquery()
        )
    stmt = (select(ChangeOver)
        .join(
            subq,
            and_(
                ChangeOver.machine_id == subq.c.machine_id,
                ChangeOver.timestamps == subq.c.max_timestamp
            )
        )
        .where(ChangeOver.machine_id.in_([machine.id for machine in machines]))
    )
    changeovers = session.exec(stmt).all()
    changeovers = {changeover.machine_id: changeover for changeover in changeovers}

    machines = [{"machine_id": machine.id,
                 "machine_name": machine.name,
                 "current_workpiece": machine.current_recipe.name if machine.current_recipe else None,
                 "timestamp": changeovers[machine.id].timestamps.strftime("%Y-%m-%d %H:%M") if machine.current_recipe else None
                 } for machine in machines]
    # sort machines by machine name
    machines = sorted(machines, key=lambda x: x['machine_name'])

    initial_data = {
        "op": "initial",
        "data": machines
    }
    await websocket.send_text(json.dumps(initial_data))


    async with broadcast.subscribe("machine_status") as subscriber:
        async for event in subscriber:
            message = json.loads(event.message)
            # get the current workpiece from the database
            session = next(get_session())
            recipe = session.exec(select(Recipe).where(Recipe.id == message['data']['current_recipe_id'])).one_or_none()
            if recipe is None:
                workpiece_name = "No Recipe selected"
            else:
                workpiece = session.exec(select(Workpiece).where(Workpiece.id == recipe.workpiece_id)).one_or_none()
                if workpiece is None:
                    workpiece_name = "Unknown"
                else:
                    workpiece_name = workpiece.name

            msg = {
                "op": message['op'],
                "data": {
                    "machine_id": message['data']['id'],
                    "machine_name": message['data']['name'],
                    "current_workpiece": workpiece_name,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            }
                
            await websocket.send_text(json.dumps(msg))


@router.get("/api/low_inventory")
async def low_inventory(request: Request, db: Session = Depends(get_session)):
    """Render the low inventory page"""
    # last calendar week
    now = datetime.now()
    last_sunday = now - timedelta(days=now.weekday() + 1)

    # get tools for which the inventory is below 1.5 times the average weekly consumption rate of the last 4 weeks
    records = db.exec(
        select(ToolConsumption)
        .where(ToolConsumption.datetime <= last_sunday)
        .where(ToolConsumption.datetime >= last_sunday - timedelta(weeks=8))
    ).all()
    weekly_totals = defaultdict(lambda: defaultdict(int))
    for rec in records:
        iso_year, iso_week, _ = rec.datetime.isocalendar()
        key = f"{iso_year}-{iso_week}"
        weekly_totals[rec.tool_id][key] += rec.quantity
    
    tool_ids = [tool_id for tool_id in weekly_totals]

    tools: list[Tool] = db.exec(
                            select(Tool)
                            .where(Tool.id.in_(tool_ids))
                            .where(Tool.stop_order == False)
                            .where(Tool.recipes.any())
                        ).all()

    tools = {tool.id: 
             {
                'name': tool.name,
                'number': tool.number,
                'weekly_usage': None,
                'supply': None,
                'inventory': tool.inventory,
                'order_quantity': 0,
                'delivery_date': None,
            } for tool in tools if tool.inventory < 1.5 * sum(weekly_totals[tool.id].values()) / len(weekly_totals[tool.id])}
    
    tool_ids = [tool_id for tool_id in tools]

    for tool_id, weeks in weekly_totals.items():
        if tool_id not in tools:
            continue
        avg_consumption = sum(weeks.values()) / len(weeks)
        tools[tool_id]['weekly_usage'] = round(avg_consumption, 1)
        tools[tool_id]['supply'] = round(tools[tool_id]['inventory'] / avg_consumption, 1)

    orders: list[ToolOrder] = db.exec(
        select(ToolOrder)
        .where(ToolOrder.tool_id.in_(tool_ids))
        .where(ToolOrder.delivered < ToolOrder.quantity)
    )
    for order in orders:
        tools[order.tool_id]['order_quantity'] = order.quantity - order.delivered
        tools[order.tool_id]['delivery_date'] = order.estimated_delivery_date.strftime("%Y-%m-%d")
    
    tools = [tool for tool in tools.values()]

    return {
        "tools": tools,
    }
