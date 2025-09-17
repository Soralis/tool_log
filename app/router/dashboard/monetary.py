from fastapi import APIRouter, Request, Depends, Body
# from collections import defaultdict
# from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import locale
from collections import defaultdict

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Tool, OrderCompletion, ToolPosition, Recipe, ToolLife

locale.setlocale(locale.LC_ALL, '')

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

    data = [{'name': workpiece, 'data': [{'x': name, 'y': int(spends['total'])} for name, spends in operations.items()]} for workpiece, operations in spend_summary.items()]
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
        'text': f"Total Spend: {locale.currency(round(total_spend, 2), grouping=True)}",
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
    query = select(Tool.name, ToolConsumption.value, ToolConsumption.quantity)
    query = query.where(ToolConsumption.value != 0)
    query = query.join(Tool, Tool.id == ToolConsumption.tool_id)
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

    # combine duplicate nodes
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
        'text': f"Total Spend: {locale.currency(round(total_spend, 2), grouping=True)}",
        'textStyle': {
            'color': 'white'
        }
    }
    
    return option


@router.post("/api/spend_by_month")
async def get_spend_by_month(request: Request,
                                  db: Session = Depends(get_session),
                                  selected_products: List[str] = Body(),
                                  selected_operations: List[str] = Body(),
                                  start_date: str = Body(None),
                                  end_date: str = Body(None)):
    """Get spend data grouped by part number (row) and month (column)"""
    start_date = datetime.fromisoformat(start_date) if start_date else None
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None

    selected_products = [int(x) for x in selected_products]
    selected_operations = [int(x) for x in selected_operations]

    # Query to get spend data TODO: Get used tools by workpiece and machine, then get their consumption data
    query = select(Recipe.id, Workpiece.id, Workpiece.name, Machine.id, Machine.name).where(Recipe.machine_id.in_(selected_operations)).where(Recipe.workpiece_id.in_(selected_products))
    query = query.join(Workpiece, Workpiece.id == Recipe.workpiece_id)
    query = query.join(Machine, Machine.id == Recipe.machine_id)
    recipes = db.exec(query).all()
    recipes = {
        recipe[0]: {
            'workpiece_id': recipe[1],
            'workpiece_name': recipe[2],
            'machine_id': recipe[3],
            'machine_name': recipe[4]
        } for recipe in recipes
    }

    query = select(ToolPosition.tool_id, ToolPosition.recipe_id, ToolPosition.name).where(ToolPosition.recipe_id.in_(recipes.keys()))
    toolpositions = db.exec(query).all()
    tool_ids = [tp[0] for tp in toolpositions]

    query = select(ToolConsumption.tool_id, ToolConsumption.value, ToolConsumption.datetime).where(ToolConsumption.tool_id.in_(tool_ids))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    tool_consumptions = db.exec(query).all()

    finished_products = select(OrderCompletion.workpiece_id, OrderCompletion.date, OrderCompletion.quantity).where(OrderCompletion.workpiece_id.in_(selected_products))
    if start_date:
        finished_products = finished_products.where(OrderCompletion.date >= start_date)
    if end_date:
        finished_products = finished_products.where(OrderCompletion.date <= end_date)
    finished_products = db.exec(finished_products).all()

    tool_lifes = select(ToolLife.tool_id, ToolLife.reached_life, ToolLife.machine_id, Workpiece.id, ToolLife.timestamp).where(ToolLife.tool_id.in_(tool_ids))
    tool_lifes = tool_lifes.join(Recipe, Recipe.id == ToolLife.recipe_id).join(Workpiece, Workpiece.id == Recipe.workpiece_id)
    if start_date:
        tool_lifes = tool_lifes.where(ToolLife.timestamp >= start_date)
    if end_date:
        tool_lifes = tool_lifes.where(ToolLife.timestamp <= end_date)
    tool_lifes = db.exec(tool_lifes).all()
    mapped_tool_lifes = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    # map tool lifes to tool -> date (grouped by month) -> machine -> workpiece -> [lifes]
    for tl in tool_lifes:
        mapped_tool_lifes[tl[0]][tl[4].strftime("%Y-%m")][tl[2]][tl[3]].append(tl[1])
    avg_tool_lifes = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    for tool_id, months in mapped_tool_lifes.items():
        for month, machines in months.items():
            for machine_id, workpieces in machines.items():
                for workpiece, lifes in workpieces.items():
                    if len(lifes) == 0:
                        continue
                    avg_tool_lifes[tool_id][month][machine_id][workpiece] = sum(lifes) / len(lifes)

    monthly_tc_values = defaultdict(lambda: defaultdict(float))
    for tc in tool_consumptions:
        monthly_tc_values[tc[0]][tc[2].strftime("%Y-%m")] += float(tc[1])

    monthly_fp_values = defaultdict(lambda: defaultdict(int))
    for fp in finished_products:
        monthly_fp_values[fp[0]][fp[1].strftime("%Y-%m")] += fp[2]

    # tool_to_products = defaultdict(lambda: defaultdict(set))
    tool_to_products = defaultdict(set)
    tool_to_ops = defaultdict(set)
    for tp in toolpositions:
        tool_to_products[tp[0]].add(recipes[tp[1]]["workpiece_id"])
        tool_to_ops[tp[0]].add(recipes[tp[1]]["machine_id"])
        
    monthly_spend_per_workpiece = defaultdict(lambda: defaultdict(float))
    monthly_spend_per_operation = defaultdict(lambda: defaultdict(float))
    for tool_id, months in monthly_tc_values.items():
        associated_products = tool_to_products[tool_id]
        associated_ops = tool_to_ops[tool_id]
        for month, tc_value in months.items():
            total_finished = sum([monthly_fp_values[wp_id][month] for wp_id in associated_products])
            if total_finished == 0:
                continue
            for wp_id in associated_products:
                wp_finished = monthly_fp_values[wp_id][month]
                if wp_finished == 0:
                    continue
                # Allocate spend based on finished products
                allocated_value = (wp_finished / total_finished) * tc_value
                monthly_spend_per_workpiece[wp_id][month] += allocated_value
            for op_id in associated_ops:
                # Allocate spend based on finished products
                if avg_tool_lifes[tool_id].get(month) is None or avg_tool_lifes[tool_id][month].get(op_id) is None:
                    continue
                sum_x = 0
                sum_all = 0
                for wp_id in avg_tool_lifes[tool_id][month][op_id]:
                    sum_x += monthly_fp_values[wp_id][month] / avg_tool_lifes[tool_id][month][op_id][wp_id]
                for op_id in avg_tool_lifes[tool_id][month]:
                    for wp_id in avg_tool_lifes[tool_id][month][op_id]:
                        sum_all += monthly_fp_values[wp_id][month] / avg_tool_lifes[tool_id][month][op_id][wp_id]
                if sum_x == 0 or sum_all == 0:
                    continue

                allocated_value = sum_x / sum_all * tc_value
                monthly_spend_per_operation[op_id][month] += allocated_value
    # Total monthly spend per workpiece and operation
    total = defaultdict(float)
    for op_id, months in monthly_spend_per_operation.items():
        for month, value in months.items():
            total[month] += float(value)
    monthly_spend_per_operation["Total"] = total
        
    for wp_id, months in monthly_spend_per_workpiece.items():
        for month, value in months.items():
            total[month] += float(value)
    monthly_spend_per_workpiece["Total"]

    # Get all months in range
    if not monthly_spend_per_workpiece:
        return {
            "workpiece": {"headers": ["Part"], "rows": [], "summary": []},
            "operation": {"headers": ["Machine"], "rows": [], "summary": []}
        }

    # Get all months in range
    all_months = set()
    for wp_id, months in monthly_spend_per_workpiece.items():
        for month in months.keys():
            all_months.add(month)
    for op_id, months in monthly_spend_per_operation.items():
        for month in months.keys():
            all_months.add(month)
    all_months = sorted(list(all_months))

    # Build workpiece table
    workpiece_headers = ["Part"] + all_months + ["Total"]
    workpiece_rows = []
    workpiece_total = [0] * (len(all_months) + 1)  # +1 for the total column
    
    # Sort workpieces by name
    workpiece_ids = sorted(monthly_spend_per_workpiece.keys(), 
                          key=lambda x: recipes[list(recipes.keys())[0]]["workpiece_name"] if x == "Total" else 
                              next((r["workpiece_name"] for r in recipes.values() if r["workpiece_id"] == x), ""))
    
    for wp_id in workpiece_ids:
        if wp_id == "Total":
            continue
        row = [next((r["workpiece_name"] for r in recipes.values() if r["workpiece_id"] == wp_id), f"Workpiece {wp_id}")]
        row_total = 0
        for month in all_months:
            value = monthly_spend_per_workpiece[wp_id].get(month, 0)
            row.append(locale.currency(value, grouping=True))
            row_total += value
        row.append(locale.currency(row_total, grouping=True))
        workpiece_rows.append(row)
        
        # Update totals
        for i, month in enumerate(all_months):
            workpiece_total[i] += monthly_spend_per_workpiece[wp_id].get(month, 0)
        workpiece_total[-1] += row_total

    # Add total row
    total_row = ["Total"]
    for i, month in enumerate(all_months):
        total_row.append(locale.currency(workpiece_total[i], grouping=True))
    total_row.append(locale.currency(workpiece_total[-1], grouping=True))
    workpiece_rows.append(total_row)
    
    # Build operation table
    operation_headers = ["Machine"] + all_months + ["Total"]
    operation_rows = []
    operation_total = [0] * (len(all_months) + 1)  # +1 for the total column
    
    # Sort operations by name
    operation_ids = sorted(monthly_spend_per_operation.keys(), 
                          key=lambda x: recipes[list(recipes.keys())[0]]["machine_name"] if x == "Total" else 
                              next((r["machine_name"] for r in recipes.values() if r["machine_id"] == x), ""))
    
    for op_id in operation_ids:
        if op_id == "Total":
            continue
        row = [next((r["machine_name"] for r in recipes.values() if r["machine_id"] == op_id), f"Machine {op_id}")]
        row_total = 0
        for month in all_months:
            value = monthly_spend_per_operation[op_id].get(month, 0)
            row.append(locale.currency(value, grouping=True))
            row_total += value
        row.append(locale.currency(row_total, grouping=True))
        operation_rows.append(row)
        
        # Update totals
        for i, month in enumerate(all_months):
            operation_total[i] += monthly_spend_per_operation[op_id].get(month, 0)
        operation_total[-1] += row_total

    # Add total row
    total_row_op = ["Total"]
    for i, month in enumerate(all_months):
        total_row_op.append(locale.currency(operation_total[i], grouping=True))
    total_row_op.append(locale.currency(operation_total[-1], grouping=True))
    operation_rows.append(total_row_op)

    return {
        "workpiece": {
            "headers": workpiece_headers,
            "rows": workpiece_rows,
            "summary": total_row
        },
        "operation": {
            "headers": operation_headers,
            "rows": operation_rows,
            "summary": total_row_op
        }
    }
