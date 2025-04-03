from fastapi import APIRouter, Request, Depends, Body
# from collections import defaultdict
# from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import locale

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Tool, OrderCompletion, ToolPosition, Recipe

locale.setlocale( locale.LC_ALL, '' )

router = APIRouter(
    prefix="/monetary",
    tags=["monetary"],
)

@router.get("/")
async def dashboard(request: Request):
    """Render the main dashboard page"""
    return templates.TemplateResponse(
        "dashboard/monetary.html.j2",
        {
            "request": request,
        }
    )


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

    total_spend = sum(float(item[3]) for item in db_data)
    option['title'] = {
        'text': f"Total Spend: {locale.currency( round(total_spend, 2), grouping=True )}",
        'textStyle': {
            'color': 'white'
        }
    }

    return option


@router.post("/api/spend_summary_sankey")
async def get_spend_summary_from_ordercompletions(request: Request,
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

    ### FETCH Tool Consumption
    # query = select(Workpiece.name, Machine.name, Tool.name, ToolConsumption.value, ToolConsumption.quantity).select_from(ToolConsumption)
    # query = query.join(Machine, Machine.id == ToolConsumption.machine_id)
    # query = query.join(Workpiece, Workpiece.id == ToolConsumption.workpiece_id)
    # query = query.join(Tool, Tool.id == ToolConsumption.tool_id)
    query = select(Tool.name, ToolConsumption.value, ToolConsumption.quantity)
    query = query.where(ToolConsumption.value != 0)
    query = query.join(Tool, Tool.id == ToolConsumption.tool_id)
    # query = query.where(ToolConsumption.workpiece_id.in_(selected_products))
    # query = query.where(ToolConsumption.machine_id.in_(selected_operations))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)

    db_tool_consumption = db.exec(query).all()

    db_machines = db.exec(select(Machine.name).where(Machine.id.in_(selected_operations))).all()
    db_workpieces = db.exec(select(Workpiece.name).where(Workpiece.id.in_(selected_products))).all()

    tools = set([item[0] for item in db_tool_consumption])
    edges = []
    for workpiece in db_workpieces:
        edges.append({'name': workpiece})
    for machine in db_machines:
        edges.append({'name': machine})
    for tool in tools:
        edges.append({'name': tool})
    tools.add('total')

    spend_summary = {}
    for tool in db_tool_consumption:
        if tool[0] not in spend_summary:
            spend_summary[tool[0]] = {'quantity': 0,
                                      'value': 0,
                                      'hits': {}
                                      }
        spend_summary[tool[0]]['quantity'] += tool[2]
        spend_summary[tool[0]]['value'] += tool[1]
    

    ### FETCH ORDER COMPLETIONS
    query = select(Workpiece.name, OrderCompletion.quantity)
    query = query.join(Workpiece, Workpiece.id == OrderCompletion.workpiece_id)
    query = query.where(OrderCompletion.workpiece_id.in_(selected_products))
    if start_date:
        query = query.where(OrderCompletion.date >= start_date)
    if end_date:
        query = query.where(OrderCompletion.date <= end_date)

    order_completions = db.exec(query).all()
    workpiece_summary = {}
    for completion in order_completions:
        if completion[0] not in workpiece_summary:
            workpiece_summary[completion[0]] = 0
        workpiece_summary[completion[0]] += completion[1]

    ### FETCH TOOL POSITIONS
    query = select(Tool.name, ToolPosition.tool_count, Machine.name, Workpiece.name).select_from(ToolPosition)
    query = query.join(Tool, Tool.id == ToolPosition.tool_id)
    query = query.join(Recipe, Recipe.id == ToolPosition.recipe_id)
    query = query.join(Machine, Machine.id == Recipe.machine_id)
    query = query.join(Workpiece, Workpiece.id == Recipe.workpiece_id)
    query = query.where(Recipe.machine_id.in_(selected_operations))
    query = query.where(Recipe.workpiece_id.in_(selected_products))

    tool_positions = db.exec(query).all()

    for position in tool_positions:
        if position[0] not in spend_summary:
            print(f"{position[0]} is missing")
            continue
        if position[2] not in spend_summary[position[0]]['hits']:
            spend_summary[position[0]]['hits'][position[2]] = {}
        if position[3] not in spend_summary[position[0]]['hits'][position[2]]:
            spend_summary[position[0]]['hits'][position[2]][position[3]] = {'avg_tool_life': 0,
                                                                            'backflush': workpiece_summary.get(position[3], 0),
                                                                            'tool_quantity_in_position': position[1]
                                                                            }
        
    nodes = []
    for tool_name, tool in spend_summary.items():
        total_hits = sum([sum([workpiece['backflush'] * workpiece['tool_quantity_in_position'] for workpiece in op.values()]) for op in tool['hits'].values()])
        for operation_name, operation in tool['hits'].items():
            for workpiece_name, workpiece in operation.items():
                value = round((workpiece['backflush'] * workpiece['tool_quantity_in_position'] / total_hits) * float(tool['value']), 2) if total_hits != 0 else 0
                nodes.append({'source': workpiece_name, 'target': operation_name, 'value': value})
            op_value = round((sum([workpiece['backflush'] * workpiece['tool_quantity_in_position'] for workpiece in operation.values()])/ total_hits) * float(tool['value']), 2) if total_hits != 0 else 0
            nodes.append({'source': operation_name, 'target': tool_name, 'value': op_value})

    #combine duplicate nodes
    combined_nodes = []
    combinations = {}
    for node in nodes:
        if (node['source'], node['target']) in combinations:
            combined_nodes[combinations[node['source'], node['target']]]['value'] = round(combined_nodes[combinations[node['source'], node['target']]]['value'] + node['value'], 2)
        else:
            combined_nodes.append(node)
            combinations[node['source'], node['target']] = len(combined_nodes) - 1

    option['series']['data'] = edges
    option['series']['links'] = combined_nodes

    total_spend = sum(float(item[1]) for item in db_tool_consumption)
    option['title'] = {
        'text': f"Total Spend: {locale.currency( round(total_spend, 2), grouping=True )}",
        'textStyle': {
            'color': 'white'
        }
    }
    
    return option
