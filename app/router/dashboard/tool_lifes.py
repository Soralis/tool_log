from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException
import asyncio
import json
from statistics import median
from collections import defaultdict
from app.templates.jinja_functions import templates
from datetime import datetime
from sqlmodel import Session, select
from app.database_config import get_session
from app.models import Tool, ToolLife, Recipe, Machine, ToolPosition
from typing import Dict, List, Optional
from .utils import get_condensed_data
from . import tool_lifes_cards as tc


router = APIRouter()

# Global variables to store the latest filter settings
websocket_filters = {}

def define_machine_colors(machines):
    num_machines = len(machines)
    machine_colors = {machine.name: [f"hsl({int(360 * i / num_machines)}, 75%, 50%)", f"hsla({int(360 * i / num_machines)}, 75%, 50%, 0.5)"] for i, machine in enumerate(machines)} if num_machines > 0 else {}
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
        statement = statement.where(ToolLife.machine_id.in_(selected_operations or []))
        statement = (
            statement
            .join(Recipe, ToolLife.recipe_id == Recipe.id)
            .where(Recipe.workpiece_id.in_(selected_products or []))
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

    data = {}
    for tool in tools:
        # Build query with date filters
        statement = select(ToolLife).where(ToolLife.tool_id == tool.id)
        
        if start_date:
            statement = statement.where(ToolLife.timestamp >= start_date)
        if end_date:
            statement = statement.where(ToolLife.timestamp <= end_date)

        statement = statement.where(ToolLife.machine_id.in_(selected_operations or []))
        statement = (
            statement
            .join(Recipe, ToolLife.recipe_id == Recipe.id)
            .where(Recipe.workpiece_id.in_(selected_products or []))
        )
            
        statement = statement.order_by(ToolLife.timestamp.asc())
        records = list(db.exec(statement))
        
        # Only include tools that have records
        if records:
            ordered_records = {}
            # sort by machine
            for r in records:
                if r.machine.name not in ordered_records:
                    ordered_records[r.machine.name] = {}
                if f"Channel {r.machine_channel}" not in ordered_records[r.machine.name]:
                    ordered_records[r.machine.name][f"Channel {r.machine_channel}"] = []
                ordered_records[r.machine.name][f"Channel {r.machine_channel}"].append(r)

            series = []

            for machine in ordered_records:
                for channel in ordered_records[machine]:
                    condensed_data, window = get_condensed_data([{'timestamp': tool_life.timestamp, 'reached_life': tool_life.reached_life} 
                                                         for tool_life in ordered_records[machine][channel]])

                    series.append({
                        "type": "line",
                        "data": condensed_data,
                        "tooltip": {
                            "formatter": 'gaygaygay',
                        },
                        # "smooth": True,
                        "lineStyle": { "color": machine_colors[machine][0] },
                        "areaStyle": { "color": machine_colors[machine][1] },
                    })

            data[f"tool_{tool.id}"] = {
                "tooltip": { "trigger": "axis" },
                "xAxis": {"type": "time"},
                "yAxis": { "type": "value" },
                "series": series
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
    start_date: str = None, 
    end_date: str = None, 
    db: Session = Depends(get_session)
):
    """Get detailed information about a specific tool"""
    # Get tool information
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Convert date strings to datetime objects
    start = datetime.fromisoformat(start_date) if start_date and start_date != 'null' else None
    end = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None
    
    # Get tool life records with date filtering
    statement = select(ToolLife).where(ToolLife.tool_id == tool_id)
    if start:
        statement = statement.where(ToolLife.timestamp >= start)
    if end:
        statement = statement.where(ToolLife.timestamp <= end)
    statement = statement.order_by(ToolLife.timestamp.asc())
    tool_life_records = db.exec(statement).all()
    # tool_life_records.reverse()  # Chronological order

    # Define cards for the modal
    details = {
        "title": f"{tool.name} (#{tool.number})",
        "cards": []
    }

    if not tool_life_records:
        details['cards'].append({
            "id": "no_data",
            "title": f"No Data Available for the timeframe from {start} to {end}.",
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
        if f"Channel {r.machine_channel}" not in ordered_tool_life_records[r.machine.name]:
            ordered_tool_life_records[r.machine.name][f"Channel {r.machine_channel}"] = []
        ordered_tool_life_records[r.machine.name][f"Channel {r.machine_channel}"].append(r)

    ### General Graph
    machines = db.exec(select(Machine).where(Machine.active == True)).all()
    machines.sort(key=lambda x: x.name)
    # machine_colors = define_machine_colors(machines)

    general_series = []
    machine_spec_series = []

    for machine in ordered_tool_life_records:
        machine_series = []
        stats = {}
        operators_life = defaultdict(list)
        lifes = []
        change_reasons = {}
        channels = [channel for channel in ordered_tool_life_records[machine]]

        for channel in channels:
            channel_data = ordered_tool_life_records[machine][channel]
        
            series = {
                "type": "line",
                "data": [{"value": [life.timestamp, life.reached_life], 
                          "tooltip": f"""{life.timestamp.strftime('%Y-%m-%d %H:%M')}
                                <br>{life.reached_life} pcs
                                <br>{life.change_reason.name if life.change_reason else 'N/A'}
                                <br>{life.user.name if life.user else 'N/A'} {life.user.shift.number if life.user and life.user.shift else ''}
                                """} for life in channel_data],
                # "tooltip": {
                #     "formatter": 'homohmomom',
                # },
                # "lineStyle": { "color": machine_colors[machine][0] },
                # "areaStyle": { "color": machine_colors[machine][1] },
            }

            
            for record in channel_data:
                change_reason = record.change_reason.name if record.change_reason else "N/A"
                if change_reason not in change_reasons:
                    change_reasons[change_reason] = {"Sentiment": record.change_reason.sentiment if record.change_reason else 3}
                    for ch in channels:
                        change_reasons[change_reason][ch] = 0
                change_reasons[change_reason][channel] += 1
            
            for reason in change_reasons:
                # if channel not in change_reasons[reason]:
                #     change_reasons[reason][channel] = 0
                change_reasons[reason][channel] = round(100 * change_reasons[reason][channel] / len(channel_data), 1)

            tool_position: ToolPosition = next((record.tool_position for record in channel_data if record.tool_position), [] )

            stats['expected_life'] = tool_position.expected_life if tool_position else 1
            stats['tools_per_life'] = tool_position.tool_count if tool_position else 1

            for t_life in tool_position.tool_lifes:
                t_life: ToolLife
                lifes.append(t_life.reached_life)
                if t_life.user and str(t_life.machine_channel) in channel:
                    operators_life[t_life.user.name].append(t_life.reached_life)

            general_series.append(series)

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
        ranking.sort(key=lambda x: x['avg_life'], reverse=True)
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
            'title': machine, 
            'health': round((stats['avg_life']/stats['expected_life']) * 2 * machine_health / 100, 1),
            'channels': channels,
            'data': machine_series, 
            'change_reasons': change_reason_series, 
            'stats': stats})

    details['cards'].append(tc.graph_card("", general_series))

    ### Tool statistics overall
    avg_life = round(sum(tool_lifes) / len(tool_lifes)) if len(tool_lifes) > 0 else 0

    details['cards'].append(tc.stat_card("Tool Statistics", [
        ["Average Life", avg_life],
        ["Median Life", round(median(tool_lifes)) if len(tool_lifes) > 0 else 0],
        ["CPU", f"${round(tool.price / tool.max_uses / avg_life, 2)}"],
    ]))  

    ### Basic Tool Details
    details['cards'].append(tc.stat_card("Tool Information", [
        ["Type", f"{tool.tool_type.name} ({'perishable' if tool.tool_type.perishable else 'durable'})"],
        ["Description", tool.description],
        ["Manufacturer", tool.manufacturer.name],
        ["CPN", tool.cpn_number],
        ["ERP", tool.erp_number],
        ["Price", tool.price]
    ]))  

    ### Machine specific stats and graphs
    for machine_spec in machine_spec_series:
        details['cards'].append(tc.graph_card(machine_spec['title'], machine_spec['data']))
        details['cards'].append(tc.graph_card(machine_spec['title'], machine_spec['change_reasons'], xAxis= {'type': "category",'data': machine_spec['channels']}, width=3))
        stats = machine_spec['stats']
        best_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][:3]])
        worst_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][-3:]])
        details['cards'].append(tc.stat_card("Tool Statistics", [
            ["Machine Health", f"{machine_spec['health']} / 10"],
            ["Average Life", stats['avg_life']],
            ["Median Life", stats['median_life']],
            ["Target Life", stats['expected_life']],
            ["Tools per Record", stats['tools_per_life']],
            ["CPU", f"${round(stats['tools_per_life'] * tool.price / tool.max_uses / stats['avg_life'], 2)}"],
            ["Target CPU", f"${round(stats['tools_per_life'] * tool.price / tool.max_uses / stats['expected_life'], 2)}"],
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
