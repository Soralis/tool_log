from fastapi import APIRouter, Request, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
import socket
from datetime import datetime

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Tool

router = APIRouter()


def get_ip_address():
    try:
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip == '127.0.1.1':
            local_ip = '10.0.36.192'
            
        # Fallback to just local IP if public IP fetch fails
        return f"{hostname} (IP: {local_ip})"
    except:
        return "Unable to get IP address"


@router.get("/api/filter-options")
async def get_filter_options(request: Request, db: Session = Depends(get_session)):
    """Get available filter options (products and operations)"""
    products = db.exec(select(Workpiece)).all()
    products = {workpiece.name: workpiece.id for workpiece in products}
    operations = db.exec(select(Machine)).all()
    operations = {operation.name: operation.id for operation in operations}
    
    return {
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
            "server_address": get_ip_address()
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

    print('hier kommt ne anfrage')
    print(selected_products)
    print(selected_operations)
    print(start_date)
    print(end_date)
    
    
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

@router.post("/api/mocky")
async def get_spend_summary(request: Request,
                            db: Session = Depends(get_session),
                            selected_products: List[str] = Body(),
                            selected_operations: List[str] = Body(),
                            start_date: str = Body(None),
                            end_date: str = Body(None),
                            option: dict = Body()):
    """Get spend summary data based on filters"""
    start_date = datetime.fromisoformat(start_date) if start_date else None
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None

    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]

    query = select(Workpiece.name, Machine.name, Tool.name, ToolConsumption.value)
    query = query.join(Machine, Machine.id == ToolConsumption.machine_id)
    query = query.join(Workpiece, Workpiece.id == ToolConsumption.workpiece_id)
    query = query.join(Tool, Tool.id == ToolConsumption.tool_id)
    query = query.where(ToolConsumption.workpiece_id.in_(selected_products))
    query = query.where(ToolConsumption.machine_id.in_(selected_operations))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)

    db_data = db.exec(query).all()

    # Group data
    workpieces = set([item[0] for item in db_data])
    machines = set([item[1] for item in db_data])
    tools = set([item[2] for item in db_data])
    tools.add('total')
    spend_summary = {workpiece: {machine: {tool: 0 for tool in tools} for machine in machines} for workpiece in workpieces}
    total = 0
    for item in db_data:
        spend_summary[item[0]][item[1]][item[2]] += float(item[3])
        spend_summary[item[0]][item[1]]['total'] += float(item[3])
        total += float(item[3])
    
    tools.discard('total')
    
    # Drop all values where the sum is 0
    for workpiece in workpieces:
        for machine in machines:
            for tool in tools:    
                if spend_summary[workpiece][machine][tool] == 0:
                    del spend_summary[workpiece][machine][tool]

    data = [{'name':workpiece, 'data':[{'x':name,'y':int(spends['total'])} for name, spends in operations.items()]} for workpiece, operations in spend_summary.items()]
    # sort alphabetically, first by workpiece, secondary by operation
    data = sorted(data, key=lambda x: x['name'])
    for item in data:
        item['data'] = sorted(item['data'], key=lambda x: x['x'])

    option['xAxis']['data'] = list(machines)
    option['xAxis']['data'].sort()
    option['yAxis']['data'] = list(workpieces)
    option['yAxis']['data'].sort()
    machines = {machine: index for index, machine in enumerate(option['xAxis']['data'])}
    workpieces = {workpiece: index for index, workpiece in enumerate(option['yAxis']['data'])}
    option['series'][0]['data'] = []
    for data_dict in data:
        for value in data_dict['data']:
            option['series'][0]['data'].append([machines[value['x']], workpieces[data_dict['name']], value['y'] if value['y'] != 0 else '-'])
    max = 0
    for coords in option['series'][0]['data']:
        if isinstance(coords[2], int) and coords[2] > max:
            max = coords[2]
    option['visualMap']['max'] = max
    return option