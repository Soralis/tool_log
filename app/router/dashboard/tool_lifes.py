from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException
import asyncio
import json
from statistics import median
from collections import defaultdict
from app.templates.jinja_functions import templates
from datetime import datetime
from sqlmodel import Session, select
import locale
from app.database_config import get_session
from app.models import Tool, ToolLife, Recipe, Machine, ToolPosition, ToolConsumption, Line
from typing import Dict, List, Optional
from .utils import get_condensed_data
from . import tool_lifes_cards as tc


router = APIRouter()

# Global variables to store the latest filter settings
websocket_filters = {}

def define_machine_colors(machines):
    machine_colors = {}
    lines = {}
    for machine in machines:
        if machine.line and machine.line.name not in lines:
            lines[machine.line.name] = []
        lines[machine.line.name].append(machine)
    
    for line_name, machines_in_line in lines.items():
        # Assign colors to machines in the same line
        num_machines = len(machines_in_line)
        for i, machine in enumerate(machines_in_line):
            if f"{line_name}_{machine.name}" not in machine_colors:
                # # Generate a color based on the index
                # hue = 0  # Use a single hue for all lines
                # saturation = "0%"  # Grayscale
                # lightness = (50 * i / num_machines) + 40  # valid values range from 40 to 90
                # machine_colors[f"{line_name}_{machine.name}"] = [
                #     f"hsl({hue}, {saturation}, {lightness}%)",
                #     f"hsla({hue}, {saturation}, {lightness}%, 0.5)"
                # ]
                machine_colors[f"{line_name}_{machine.name}"] = [f"hsl({int(360 * i / num_machines)}, 75%, 50%)", f"hsla({int(360 * i / num_machines)}, 75%, 50%, 0.5)"]

    return machine_colors

async def get_tool_life_graphs(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                          selected_operations: Optional[list] = None, selected_products: Optional[list] = None) -> List[Dict]:
    # Get all active tools
    statement = select(Tool).where(Tool.active == True)
    tools = db.exec(statement).all()
    
    graphs = []
    
    # Fetch ToolLife records for each tool and find the latest timestamp
    tool_life_data = []
    for tool in tools:
        statement = select(ToolLife).where(ToolLife.tool_id == tool.id)
        if start_date:
            statement = statement.where(ToolLife.timestamp >= start_date)
        if end_date:
            statement = statement.where(ToolLife.timestamp <= end_date)
        if selected_operations:
            statement = statement.where(ToolLife.machine_id.in_(selected_operations))
        if selected_products:
            statement = (
                statement
                .join(Recipe, ToolLife.recipe_id == Recipe.id)
                .where(Recipe.workpiece_id.in_(selected_products))
            )
        
        tool_lifes = db.exec(statement).all()
        if tool_lifes:
            latest_timestamp = max(tool_life.timestamp for tool_life in tool_lifes)
            tool_life_data.append((tool, latest_timestamp))
    
    # Sort tools by the latest ToolLife timestamp (newest first)
    tool_life_data.sort(key=lambda x: x[1], reverse=True)
    
    # Create graph dictionaries in the sorted order
    for tool, _ in tool_life_data:
        graphs.append({
            "id": f"tool_{tool.id}",
            "type": "line",
            "title": f"{tool.name} (#{tool.number})",
            "width": 6,
            "height": 2
        })

    return graphs

async def get_tool_life_data(db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                          selected_operations: Optional[list] = None, selected_products: Optional[list] = None) -> Dict:
    # Get active tools with life records
    statement = select(Tool).where(Tool.active == True)
    tools = db.exec(statement).all()

    machines = db.exec(select(Machine).where(Machine.active == True)).all()
    machines.sort(key=lambda x: x.name)
    machine_colors = define_machine_colors(machines)
    machine_map = {f"{machine.line.name}_{machine.name}": machine for machine in machines}

    lines = db.exec(select(Line)).all()
    line_patterns = {line.id: pattern for line, pattern in zip(lines, ['rect', 'circle', 'triangle', 'diamond', 'pin', 'arrow', 'roundRect'])}


    data = {}
    for tool in tools:
        # Build query with date filters
        statement = select(ToolLife).where(ToolLife.tool_id == tool.id)
        
        if start_date:
            statement = statement.where(ToolLife.timestamp >= start_date)
        if end_date:
            statement = statement.where(ToolLife.timestamp <= end_date)

        if selected_operations:
            statement = statement.where(ToolLife.machine_id.in_(selected_operations))
        if selected_products:
            statement = (
                statement
                .join(Recipe, ToolLife.recipe_id == Recipe.id)
                .where(Recipe.workpiece_id.in_(selected_products))
            )
            
        statement = statement.order_by(ToolLife.timestamp.asc())
        records = list(db.exec(statement))
        
        # Only include tools that have records
        if records:
            ordered_records = {}
            # sort by machine
            for r in records:
                key = f"{r.machine.line.name}_{r.machine.name}"
                if key not in ordered_records:
                    ordered_records[key] = {}
                if f"Channel {r.machine_channel}" not in ordered_records[key]:
                    ordered_records[key][f"Channel {r.machine_channel}"] = []
                ordered_records[key][f"Channel {r.machine_channel}"].append(r)

            series = []
            decal_symbols = set()

            for machine_key in ordered_records:
                machine_name = machine_key
                machine_obj = machine_map.get(machine_name)
                for channel in ordered_records[machine_key]:
                    condensed_data, _ = get_condensed_data([{'timestamp': tool_life.timestamp, 'reached_life': tool_life.reached_life} 
                                                         for tool_life in ordered_records[machine_key][channel]])
                    decal_symbols.add(line_patterns.get(machine_obj.line_id, 'rect') if machine_obj else 'rect')
                    series.append({
                        "type": "line",
                        "data": condensed_data,
                        "lineStyle": { "color": machine_colors[machine_key][0] },
                        "areaStyle": { 
                            "color": machine_colors[machine_key][1],
                        },
                    })

            data[f"tool_{tool.id}"] = {
                "tooltip": { "trigger": "axis" },
                "xAxis": {"type": "time"},
                "yAxis": { "type": "value" },
                "series": series,
                "aria": {
                    "enabled": True,
                    "decal": {
                        "show": True,
                        "decals": {
                            "symbol": list(decal_symbols),
                            "dashArrayX": 20,
                            "dashArrayY": 20,
                            "color": "rgba(0, 0, 0, 0.4)",
                        }
                    }
                }
            }
    
    return data

async def send_tool_data(websocket: WebSocket, db: Session):
    global websocket_filters
    latest_start_date = websocket_filters[websocket].get("latest_start_date")
    latest_end_date = websocket_filters[websocket].get("latest_end_date")
    selected_operations = websocket_filters[websocket].get("selected_operations")
    selected_products = websocket_filters[websocket].get("selected_products")
    last_filter_update = websocket_filters[websocket].get("last_filter_update")

    await asyncio.sleep(1)  # Wait for any additional filters to be sent
    if last_filter_update != websocket_filters[websocket].get("last_filter_update"):
        # Filters have been updated, skip this update
        return
    # Filters have not been updated, proceed with sending data

    try:
        # Get filtered graphs and data
        graphs = await get_tool_life_graphs(db, latest_start_date, latest_end_date, selected_operations, selected_products)
        data = await get_tool_life_data(db, latest_start_date, latest_end_date, selected_operations, selected_products)

        # Send both graphs and data
        response = {
            "graphs": graphs,
            "data": data
        }
        await websocket.send_text(json.dumps(response))

    except RuntimeError as e:
        if "close message has been sent" in str(e):
            print("Websocket closed")
            return  # Exit if the websocket is closed
        raise
    except Exception as e:
        print(f"Error in send_tool_data: {e}")


@router.get("/toolLifes")
async def tools(request: Request, db: Session = Depends(get_session)):
    # Get initial graphs without date filtering
    graphs = await get_tool_life_graphs(db)
    return templates.TemplateResponse(
        "dashboard/tool_lifes.html.j2",  # Updated template path
        {
            "request": request,
            "graphs": graphs
        }
    )

@router.get("/api/toolLifes/{tool_id}/details")
async def get_tool_details(
    tool_id: int,
    start_date: Optional[datetime],
    end_date: str = None, 
    selected_operations: str = '',
    selected_products: str = '',
    db: Session = Depends(get_session)
):
    """Get detailed information about a specific tool"""
    # Get tool information
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Convert date strings to datetime objects and make them timezone-naive
    end_date = datetime.fromisoformat(end_date).replace(tzinfo=None) if end_date and end_date != 'null' else datetime.now().replace(tzinfo=None)

    selected_operations = json.loads(selected_operations) if selected_operations else []
    selected_products = json.loads(selected_products) if selected_products else []
    # Convert selected operations and products to lists of integers
    selected_operations = [int(op) for op in selected_operations]
    selected_products = [int(product) for product in selected_products]
    
    # Get tool life records with date filtering
    statement = select(ToolLife).where(ToolLife.tool_id == tool_id)
    if start_date:
        start_date = start_date.replace(tzinfo=None)
        statement = statement.where(ToolLife.timestamp >= start_date)
    if end_date:
        statement = statement.where(ToolLife.timestamp <= end_date)
    if selected_operations:
        statement = statement.where(ToolLife.machine_id.in_(selected_operations))
    if selected_products:
        statement = (
            statement
            .join(Recipe, ToolLife.recipe_id == Recipe.id)
            .where(Recipe.workpiece_id.in_(selected_products))
        )
    statement = statement.order_by(ToolLife.timestamp.asc())
    tool_life_records = db.exec(statement).all()

    # sum up the consumption values for the tool in the database
    consumption_records = db.exec(
        select(ToolConsumption)
        .where(ToolConsumption.tool_id == tool_id)
        .where(ToolConsumption.datetime >= start_date if start_date else datetime.min)
        .where(ToolConsumption.datetime <= end_date if end_date else datetime.max)
    ).all()

    consumption_value = sum([consumption.value for consumption in consumption_records])
    consumption_quantity = sum([consumption.quantity for consumption in consumption_records])

    timeframe_in_days = (end_date - start_date).days if start_date and end_date else 0

    # Define cards for the modal
    details = {
        "title": f"{tool.name} (#{tool.number})",
        "cards": []
    }

    if not tool_life_records:
        details['cards'].append({
            "id": "no_data",
            "title": f"No Data Available for the timeframe from {start_date} to {end_date}.",
            "width": 12,
            "height": 2,
        })
        return details  

    ordered_tool_life_records = {}
    tool_lifes = []
    # sort by machine
    for r in tool_life_records:
        tool_lifes.append(r.reached_life)
        if r.machine.name not in ordered_tool_life_records:
            ordered_tool_life_records[r.machine.name] = {}
        if r.recipe.workpiece.name not in ordered_tool_life_records[r.machine.name]:
            ordered_tool_life_records[r.machine.name][r.recipe.workpiece.name] = {}

        if f"Channel {r.machine_channel}" not in ordered_tool_life_records[r.machine.name][r.recipe.workpiece.name]:
            ordered_tool_life_records[r.machine.name][r.recipe.workpiece.name][f"Channel {r.machine_channel}"] = []
        ordered_tool_life_records[r.machine.name][r.recipe.workpiece.name][f"Channel {r.machine_channel}"].append(r)

    ### General Graph
    machines = db.exec(select(Machine).where(Machine.active == True)).all()
    machines.sort(key=lambda x: x.name)
    # machine_colors = define_machine_colors(machines)

    general_series = []
    machine_spec_series = []

    for machine_name, machine in ordered_tool_life_records.items():
        
        workpieces = [workpiece for workpiece in machine]
        
        for workpiece in workpieces:
            machine_series = []
            stats = {}
            operators_life = defaultdict(list)
            lifes = []
            change_reasons = {}

            channels = [channel for channel in machine[workpiece]]

            for channel in channels:
                channel_data = machine[workpiece][channel]
            
                series = {
                    "type": "line",
                    "data": [{"value": [life.timestamp, life.reached_life], 
                            "tooltip": f"""{life.timestamp.strftime('%Y-%m-%d %H:%M')}
                                    <br>{life.reached_life} pcs
                                    <br>{life.change_reason.name if life.change_reason else 'N/A'}
                                    <br>{life.user.name if life.user else 'N/A'} {life.user.shift.number if life.user and life.user.shift else ''}
                                    """} for life in channel_data],
                }

                for record in channel_data:
                    change_reason = record.change_reason.name if record.change_reason else "N/A"
                    if change_reason not in change_reasons:
                        change_reasons[change_reason] = {"Sentiment": record.change_reason.sentiment if record.change_reason else 3}
                        for ch in channels:
                            change_reasons[change_reason][ch] = 0
                    change_reasons[change_reason][channel] += 1
                
                for reason in change_reasons:
                    change_reasons[reason][channel] = round(100 * change_reasons[reason][channel] / len(channel_data), 1)

                tool_position: ToolPosition = next((record.tool_position for record in channel_data if record.tool_position), [] )
                
                tools_per_life = []
                used_settings = {}
                changed_settings_indicators = []

                for t_life in tool_position.tool_lifes:
                    t_life: ToolLife
                    if (t_life.recipe.workpiece_id not in selected_products
                        or end_date.date() < t_life.timestamp.date() 
                        or t_life.timestamp.date() < start_date.date()
                        or t_life.recipe.workpiece.name != workpiece):
                        continue
                    lifes.append(t_life.reached_life)
                    tools_per_life.append(t_life.tool_count)
                    if t_life.user and str(t_life.machine_channel) in channel:
                        operators_life[t_life.user.name].append(t_life.reached_life)
                    for s_name, s_value in t_life.tool_settings.items():
                        if s_name not in used_settings:
                            used_settings[s_name] = s_value
                        elif used_settings[s_name] != s_value:
                            changed_settings_indicators.append({
                                'name': s_name,
                                'value': s_value,
                                'previous_value': used_settings[s_name],
                                'timestamp': t_life.timestamp,
                                })
                            used_settings[s_name] = s_value
                
                tool_settings_units = {setting.name: setting.unit for setting in tool_position.tool.tool_type.tool_settings}
                stats['current_settings'] = {name: f"{value} {tool_settings_units.get(name, "(N/A)")}" for name, value in tool_position.tool_settings.items()}
                stats['expected_life'] = t_life.tool_position.expected_life
                stats['tools_per_life'] = sum(tools_per_life)/len(tools_per_life) if len(tools_per_life) > 0 else 1

                general_series.append(series.copy())

                series['markLine'] = {
                    "symbol": "none",
                    "data": [
                        {
                            "yAxis": t_life.tool_position.expected_life,
                            "name": "Target Tool Life",
                            "lineStyle": {
                                "color": "green",
                                "width": 2,
                                "type": "dashed"
                            },
                            "tooltip": {
                                "formatter": f"Target Tool Life: {t_life.tool_position.expected_life} pcs"
                            }
                        }
                    ]
                }
                # Group settings changes by timestamp
                grouped_settings = defaultdict(list)
                for setting in changed_settings_indicators:
                    grouped_settings[setting['timestamp']].append(setting)

                # Create markLines for each timestamp
                for timestamp, settings in grouped_settings.items():
                    formatters = [f"{s['name']}: {s['previous_value']} → {s['value']}" for s in settings]
                    
                    label_formatter = "\n".join(formatters)
                    tooltip_formatter = "<br>".join(formatters)
                    
                    series['markLine']['data'].append({
                        "name": ", ".join([s['name'] for s in settings]) + " changed",
                        "xAxis": timestamp,
                        "symbol": "none",
                        "lineStyle": {
                            "color": "orange",
                            "type": "dashed"
                        },
                        "label": {
                            "formatter": label_formatter
                        },
                        "tooltip": {
                            "formatter": tooltip_formatter
                        }
                    })

                if t_life.tool_position.min_life and t_life.tool_position.min_life > 0:
                    # add horizontal line at minimum tool life
                    series['markLine']['data'].append({
                        "yAxis": t_life.tool_position.min_life,
                        "name": "Minimum Tool Life",
                        "lineStyle": {
                            "color": "red",
                            "width": 2,
                            "type": "dashed"
                        },
                        "tooltip": {
                            "formatter": f"Minimum Tool Life: {t_life.tool_position.min_life} pcs"
                        }
                    })

                series['name'] = channel
                series['type'] = "scatter"
                machine_series.append(series)
            
            ranking = []
            for operator in operators_life:
                log_count = len(operators_life[operator])
                avg_life = round(sum(operators_life[operator]) / log_count) if log_count > 0 else 0
                ranking.append({'operator': operator,
                            'avg_life': avg_life,
                            'log_count': log_count})
            ranking.sort(key=lambda x: (x['avg_life'], x['log_count']), reverse=True)
            stats['ranking'] = ranking
            stats['avg_life'] = round(sum(lifes) / len(lifes)) if len(lifes) > 0 else 0
            stats['median_life'] = round(median(lifes)) if len(lifes) > 0 else 0


            change_reason_series = []
            for reason in change_reasons:
                series = {
                    "name": reason,
                    "type": "bar",
                    "barWidth": "60%",
                    "label": { "show": True, "formatter": "{c}%" },
                    "stack": "total",
                    "data": [change_reasons[reason][channel] for channel in change_reasons[reason] if channel != 'Sentiment']
                }
                change_reason_series.append(series)

            machine_health = 0
            for reason in change_reasons:
                machine_health += change_reasons[reason]['Sentiment'] * sum([change_reasons[reason][cr_channel] for cr_channel in change_reasons[reason] if cr_channel != 'Sentiment']) / (len(change_reasons[reason]) - 1)

            machine_spec_series.append({
                'title': f"{machine_name} - {workpiece}", 
                'health': round((stats['avg_life']/stats['expected_life']) * 2 * machine_health / 100, 1),
                'channels': channels,
                'data': machine_series, 
                'change_reasons': change_reason_series, 
                'stats': stats})

    details['cards'].append(tc.graph_card("", general_series))

    ### Tool statistics overall
    avg_life = round(sum(tool_lifes) / len(tool_lifes)) if len(tool_lifes) > 0 else 0

    # Calculate average weekly demand
    timeframe_in_weeks = timeframe_in_days / 7 if timeframe_in_days > 0 else 1
    avg_weekly_demand = round(consumption_quantity / timeframe_in_weeks, 1)

    details['cards'].append(tc.stat_card("Tool Statistics", [
        ["Average Life", avg_life],
        ["Median Life", round(median(tool_lifes)) if len(tool_lifes) > 0 else 0],
        ["CPU", f"${round(tool.price / tool.max_uses / avg_life, 2)}"],
        ["Used Tools", f"{consumption_quantity}"],
        ["Avg. weekly demand", f"{avg_weekly_demand} pc"],
        ["Reported Changes", f"{len(tool_life_records)} ({(len(tool_life_records) / tool.max_uses) / (consumption_quantity if consumption_quantity else 1) * 100:.1f}%)"],
        ["Spent", f"{locale.currency(round(consumption_value, 2), grouping=True )}"],
        ["Yearly Spend", f"{locale.currency(round(consumption_value / timeframe_in_days * 365, 2), grouping=True )}"],
    ]))  

    ### Basic Tool Details
    details['cards'].append(tc.stat_card("Tool Information", [
        ["Type", f"{tool.tool_type.name} ({'perishable' if tool.tool_type.perishable else 'durable'})"],
        ["Description", tool.description],
        ["Manufacturer", tool.manufacturer.name],
        ["CPN", tool.cpn_number],
        ["ERP", tool.erp_number],
        ["Price", f"{locale.currency(tool.price, grouping=True)}"]
    ]))  

    ### Machine specific stats and graphs
    for machine_spec in machine_spec_series:
        details['cards'].append(tc.graph_card(machine_spec['title'], machine_spec['data']))
        details['cards'].append(tc.graph_card(machine_spec['title'], machine_spec['change_reasons'], xAxis= {'type': "category",'data': machine_spec['channels']}, width=3))
        stats = machine_spec['stats']
        best_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][:3]])
        worst_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][-3:]])
        current_settings = "<br>".join([f"{name}: {value}" for name, value in stats['current_settings'].items()])

        details['cards'].append(tc.stat_card("Tool Statistics", [
            ["Machine Health", f"{machine_spec['health']} / 10"],
            ["Average Life", stats['avg_life']],
            ["Median Life", stats['median_life']],
            ["Target Life", stats['expected_life']],
            ["Tools per Record", stats['tools_per_life'] / tool.max_uses],
            ["CPU", f"${round(stats['tools_per_life'] * float(tool.price) / tool.max_uses / stats['avg_life'], 2)}"],
            ["Target CPU", f"${round(stats['tools_per_life'] * float(tool.price) / tool.max_uses / stats['expected_life'], 2)}"],
            ["Current Settings", current_settings],
            ["Highest Toollife", best_operators_text],
            ["Lowest Toollife", worst_operators_text]
        ])) 

    return details


async def periodic_data_sender(websocket: WebSocket, db: Session):
    while True:
        await asyncio.sleep(30)
        await send_tool_data(websocket, db)

@router.websocket("/ws/toolLifes")
async def websocket_tools(websocket: WebSocket, db: Session = Depends(get_session)):
    global websocket_filters
    await websocket.accept()

    websocket_filters[websocket] = {
        'latest_start_date': datetime.strptime("2020-01-01", "%Y-%m-%d"),
        'latest_end_date': datetime.today(),
        'selected_operations': [],
        'selected_products': [],
        'last_filter_update': datetime.fromisoformat("2020-01-01")
    }

    # Start the periodic data sending task
    data_sender_task = asyncio.create_task(periodic_data_sender(websocket, db))

    try:
        while True:
            try:
                # Receive date range from client with a timeout of 0.5 seconds
                message = await websocket.receive_text()
                filters = json.loads(message)

                websocket_filters[websocket]['latest_start_date'] = datetime.fromisoformat(filters['startDate']) if filters.get('startDate') and filters['startDate'] != 'null' else None
                websocket_filters[websocket]['latest_end_date'] = datetime.fromisoformat(filters['endDate']) if filters.get('endDate') and filters['endDate'] != 'null' else None
                websocket_filters[websocket]['selected_operations'] = [int(op) for op in filters.get('selectedOperations', [])]
                websocket_filters[websocket]['selected_products'] = [int(product) for product in filters.get('selectedProducts', [])]
                websocket_filters[websocket]['last_filter_update'] = datetime.now()

                asyncio.create_task(send_tool_data(websocket, db))

            except asyncio.TimeoutError:
                # No message received within the timeout period
                pass
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    break
                raise

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Signal the filter processing task to exit
        # await filter_queue.put(None)
        # filter_task.cancel()
        data_sender_task.cancel()
        del websocket_filters[websocket]
        try:
            await websocket.close()
        except:
            pass  # Ignore errors during close
