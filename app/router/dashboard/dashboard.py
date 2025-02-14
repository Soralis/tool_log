from fastapi import APIRouter, Request, Depends, Query, Body
# from collections import defaultdict
# from fastapi.responses import JSONResponse
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

@router.post("/api/spend_summary")
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

@router.post("/api/spend_summary_sankey")
async def get_spend_summary_sankey(request: Request,
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
    selected_products.append(None)
    selected_operations = [int(x) for x in selected_operations]
    selected_operations.append(None)

    query = select(Workpiece.name, Machine.name, Tool.name, ToolConsumption.value)
    query = query.join(Machine, Machine.id == ToolConsumption.machine_id)
    query = query.join(Workpiece, Workpiece.id == ToolConsumption.workpiece_id)
    query = query.join(Tool, Tool.id == ToolConsumption.tool_id)
    query = query.where(ToolConsumption.workpiece_id.in_(selected_products))
    query = query.where(ToolConsumption.machine_id.in_(selected_operations))
    query = query.where(ToolConsumption.value != 0)
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)

    db_data = db.exec(query).all()

    # Group data
    workpieces = set([item[0] for item in db_data])
    machines = set([item[1] for item in db_data])
    tools = set([item[2] for item in db_data])
    edges = []
    for workpiece in workpieces:
        edges.append({'name': workpiece})
    for machine in machines:
        edges.append({'name': machine})
    for tool in tools:
        edges.append({'name': tool})
    tools.add('total')

    spend_summary = {workpiece: {machine: {tool: 0 for tool in tools} for machine in machines} for workpiece in workpieces}
    for item in db_data:
        spend_summary[item[0]][item[1]][item[2]] += float(item[3])

    nodes = []
    for workpiece in spend_summary:
        for operation in spend_summary[workpiece]:
            value_sum = 0
            for tool in spend_summary[workpiece][operation]:
                if spend_summary[workpiece][operation][tool] != 0:
                    nodes.append({'source': operation, 'target': tool, 'value': int(spend_summary[workpiece][operation][tool])})
                    value_sum += spend_summary[workpiece][operation][tool]
            if value_sum != 0:
                nodes.append({'source': workpiece, 'target': operation, 'value': int(value_sum)})
    # sort edges by name
    edges.sort(key=lambda x: x['name'])
    option['series']['data'] = edges
    option['series']['links'] = nodes
    
    return option


# @router.get("/api/cleanup_data")
# async def cleanup_data(db: Session = Depends(get_session)):
#     tool_consumptions = db.exec(select(ToolConsumption)).all()
#     tool_usage = {}
#     allowed_pairs = {
#         '3700 INNER': {'OP30-IR', 'OP35-IR', 'OP60-IR', 'OP75-IR', 'OP45-Broach'},
#         '4700 INNER': {'OP30-IR', 'OP35-IR', 'OP60-IR', 'OP75-IR', 'OP45-Broach'},
#         '3700 DISK': {'OP70', 'OP60-OR', 'OP75-Chamfering', 'OP50', 'OP35-OR', 'OP75-OR', 'OP30-OR', 'OP40-OR'},
#         '3700 MONO': {'OP70', 'OP60-OR', 'OP75-Chamfering', 'OP50', 'OP35-OR', 'OP75-OR', 'OP30-OR', 'OP40-OR'},
#         '4700 DISK': {'OP70', 'OP60-OR', 'OP75-Chamfering', 'OP50', 'OP35-OR', 'OP75-OR', 'OP30-OR', 'OP40-OR'}
#     }
#     tool_name_id_pairing = {}

#     for tc in tool_consumptions:
#         if (tc.value == 0
#             or (tc.workpiece and tc.machine 
#                 and (tc.machine.name not in allowed_pairs[tc.workpiece.name]))
#             ):
#             tc.machine_id = None
#             tc.workpiece_id = None

#         tool_name_id_pairing[tc.tool_id] = tc.tool.name
            
#         if tc.tool_id not in tool_usage:
#             tool_usage[tc.tool_id] = {'machines': {}, 'workpieces': {}}
#         if tc.machine_id not in tool_usage[tc.tool_id]['machines']:
#             tool_usage[tc.tool_id]['machines'][tc.machine_id] = 0
#         if tc.workpiece_id not in tool_usage[tc.tool_id]['workpieces']:
#             tool_usage[tc.tool_id]['workpieces'][tc.workpiece_id] = 0
#         tool_usage[tc.tool_id]['machines'][tc.machine_id] += tc.quantity
#         tool_usage[tc.tool_id]['workpieces'][tc.workpiece_id] += tc.quantity

#     no_compares = defaultdict(int)
#     for consumption in tool_consumptions:
#         try:
#             changed = False
#             if not consumption.machine_id:
#                 max_machine_id = 0
#                 max_machine = 0
#                 for machine in tool_usage[consumption.tool_id]['machines']:
#                     if tool_usage[consumption.tool_id]['machines'][machine] > max_machine:
#                         max_machine = tool_usage[consumption.tool_id]['machines'][machine]
#                         max_machine_id = machine
#                 if max_machine_id != 0:
#                     consumption.machine_id = max_machine_id
#                     changed = True

#             if not consumption.workpiece_id:
#                 # find workpiece with max amount
#                 max_workpiece_id = 0
#                 max_workpiece = 0
#                 for workpiece in tool_usage[consumption.tool_id]['workpieces']:
#                     if tool_usage[consumption.tool_id]['workpieces'][workpiece] > max_workpiece:
#                         max_workpiece = tool_usage[consumption.tool_id]['workpieces'][workpiece]
#                         max_workpiece_id = workpiece
#                 if max_workpiece_id != 0:
#                     consumption.workpiece_id = max_workpiece_id
#                     changed = True
#             if changed:
#                 print(consumption.machine_id, consumption.workpiece_id)
#                 db.add(consumption)
#         except:
#             no_compares[consumption.tool_id] += consumption.quantity
#             db.add(consumption)
#             continue

#     db.commit()
#     return




