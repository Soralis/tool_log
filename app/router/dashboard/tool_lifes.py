from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException
import asyncio
import json
from collections import defaultdict
from app.templates.jinja_functions import templates
from datetime import datetime
from sqlmodel import Session, select
from app.database_config import get_session
from app.models import Tool, ToolLife, Recipe, Machine
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
                    condensed_data = get_condensed_data(ordered_records[machine][channel])

                    series.append({
                        "type": "line",
                        "data": condensed_data,
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
    print(last_filter_update==websocket_filters[websocket].get("last_filter_update"), last_filter_update, websocket_filters[websocket].get("last_filter_update"))
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
    machine_colors = define_machine_colors(machines)

    general_series = []
    machine_spec_series = []

    for machine in ordered_tool_life_records:
        machine_series = []
        stats = {}
        operators_life = defaultdict(list)
        lifes = []

        for channel in ordered_tool_life_records[machine]:
            condensed_data = get_condensed_data(ordered_tool_life_records[machine][channel])

            series = {
                "type": "line",
                "data": condensed_data,
                "lineStyle": { "color": machine_colors[machine][0] },
                "areaStyle": { "color": machine_colors[machine][1] },
            }

            stats['expected_life'] = ordered_tool_life_records[machine][channel][0].tool_position.expected_life if ordered_tool_life_records[machine][channel] else 1

            for t_life in ordered_tool_life_records[machine][channel]:
                t_life: ToolLife
                lifes.append(t_life.reached_life)
                operators_life[t_life.creator.name].append(t_life.reached_life)

            general_series.append(series)

            series['name'] = machine
            machine_series.append(series)
        
        ranking = []
        for operator in operators_life:
            log_count = len(operators_life[operator])
            avg_life = round(sum(operators_life[operator]) / log_count) if log_count > 0 else 0
            ranking.append({'operator': operator,
                        'avg_life': avg_life,
                        'log_count': log_count})
        ranking.sort(key=lambda x: x['avg_life'], reverse=True)
        print(ranking)
        stats['ranking'] = ranking
        stats['avg_life'] = round(sum(lifes) / len(lifes)) if len(lifes) > 0 else 0

        machine_spec_series.append({'title': machine, 'data':machine_series, 'stats': stats})

    details['cards'].append(tc.graph_card("", general_series))

    ### Tool statistics overall
    avg_life = round(sum(tool_lifes) / len(tool_lifes))
    target_life = 1000

    details['cards'].append(tc.stat_card("Tool Statistics", [
        ["Average Life", avg_life],
        ["Target Life", target_life],
        ["CPU", f"${round(tool.price / avg_life, 2)}"],
        ["Target CPU", f"${round(tool.price / target_life, 2)}"]
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
        stats = machine_spec['stats']
        best_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][:3]])
        worst_operators_text = "<br>".join([f"{o['operator']}: {o['avg_life']} ({o['log_count']})" for o in stats['ranking'][-3:]])
        details['cards'].append(tc.stat_card("Tool Statistics", [
            ["Average Life", stats['avg_life']],
            ["Target Life", stats['expected_life']],
            ["CPU", f"${round(tool.price / stats['avg_life'], 2)}"],
            ["Target CPU", f"${round(tool.price / stats['expected_life'], 2)}"],
            ["Best 3 Operators", best_operators_text],
            ["Worst 3 Operators", worst_operators_text]
        ])) 

    # # Add a card for each machine with all its channels
    # for machine_name, channels in machines.items():
    #     # Get all unique timestamps across all channels
    #     all_timestamps = set()
    #     for channel_records in channels.values():
    #         all_timestamps.update(record['timestamp'] for record in channel_records)

    #     # Sort timestamps chronologically
    #     sorted_timestamps = sorted(all_timestamps)
    #     timestamp_labels = [ts.isoformat() for ts in sorted_timestamps]

    #     # Create datasets for each channel
    #     datasets = []
    #     colors = [
    #         ["rgb(255, 205, 86)", "rgba(255, 205, 86, 0.5)"],  # Yellow
    #         ["rgb(153, 102, 255)", "rgba(153, 102, 255, 0.5)"],  # Purple
    #         ["rgb(75, 192, 192)", "rgba(75, 192, 192, 0.5)"],  # Teal
    #         ["rgb(255, 99, 132)", "rgba(255, 99, 132, 0.5)"],  # Pink
    #         ["rgb(54, 162, 235)", "rgba(54, 162, 235, 0.5)"],  # Blue
    #     ]

    #     for i, (channel, records) in enumerate(channels.items()):
    #         color_idx = i % len(colors)
    #         sorted_records = sorted(records, key=lambda x: x['timestamp'])

    #         datasets.append({
    #             "label": f"Channel {channel}",
    #             "data": sorted_records,
    #             "parsing": {
    #                 "xAxisKey": "timestamp",
    #                 "yAxisKey": "tool_life"
    #             },
    #             "borderColor": colors[color_idx][0],
    #             "tension": 0.1,
    #             "fill": False,
    #             "pointRadius": 5,
    #             "pointHoverRadius": 8,
    #             "pointBorderWidth": 2,
    #             "pointBackgroundColor": "white",
    #             "pointBorderColor": colors[color_idx][0]
    #         })

    #     details['cards'].append({
    #         "id": f"machine_{machine_name}",
    #         "title": f"{machine_name} Tool Life by Channel",
    #         "width": 6,  # Full width
    #         "height": 2,  # 2 units tall
    #         "type": "graph",
    #         "data": {
    #             "type": "line",
    #             "labels": timestamp_labels,
    #             "scales": scales,
    #             "datasets": datasets
    #         }
    #     })

    #     # Calculate change reason statistics
    #     all_reasons = set()
    #     channel_reasons = {}
    #     machine_reasons = defaultdict(int)
    #     total_machine_records = 0

    #     # Collect all unique reasons and count occurrences
    #     for channel, records in channels.items():
    #         channel_reasons[channel] = defaultdict(int)
    #         for record in records:
    #             reason = record['change_reason']['name']
    #             all_reasons.add(reason)
    #             channel_reasons[channel][reason] += 1
    #             machine_reasons[reason] += 1
    #             total_machine_records += 1

    #     # Convert counts to percentages
    #     reason_datasets = []

    #     # Add machine total dataset
    #     machine_percentages = []
    #     for reason in sorted(all_reasons):
    #         percentage = (machine_reasons[reason] / total_machine_records) * 100
    #         machine_percentages.append(percentage)

    #     reason_datasets.append({
    #         "label": f"{machine_name} Total",
    #         "data": machine_percentages,
    #         "backgroundColor": "rgb(128, 128, 128)",  # Gray for total
    #         "borderWidth": 1
    #     })

    #     # Add channel datasets
    #     for i, (channel, reasons) in enumerate(sorted(channel_reasons.items())):
    #         channel_total = sum(reasons.values())
    #         percentages = []
    #         for reason in sorted(all_reasons):
    #             percentage = (reasons[reason] / channel_total) * 100
    #             percentages.append(percentage)

    #         color_idx = i % len(colors)
    #         reason_datasets.append({
    #             "label": f"Channel {channel}",
    #             "data": percentages,
    #             "backgroundColor": colors[color_idx][0],
    #             "borderWidth": 1
    #         })

    #     # Add change reasons chart
    #     details['cards'].append({
    #         "id": f"machine_{machine_name}_reasons",
    #         "title": f"{machine_name} Change Reasons",
    #         "width": 6,  # Full width
    #         "height": 2,  # 2 units tall
    #         "type": "graph",
    #         "data": {
    #             "type": "bar",
    #             "labels": sorted(all_reasons),
    #             "datasets": reason_datasets,
    #             "options": {
    #                 "scales": {
    #                     "y": {
    #                         "beginAtZero": True,
    #                         "title": {
    #                             "display": True,
    #                             "text": "Percentage"
    #                         }
    #                     }
    #                 },
    #                 "plugins": {
    #                     "tooltip": {
    #                         "callbacks": {
    #                             "label": "function(context) { return context.dataset.label + ': ' + context.raw.toFixed(1) + '%'; }"
    #                         }
    #                     }
    #                 }
    #             }
    #         }
    #     })



    # # Get condensed data points
    # condensed_data = get_condensed_data(records)
    # timestamps, values = zip(*condensed_data) if condensed_data else ([], [])

    # # Calculate statistics
    # mean = np.mean(values)
    # std = np.std(values)

    # # Calculate trendline
    # x = np.arange(len(values))
    # slope, intercept, _, _, _ = linregress(x, values)

    # # Calculate daily averages (last 7 days)
    # daily_data = {}
    # for record in records:
    #     date_key = record.timestamp.strftime("%Y-%m-%d")
    #     if date_key not in daily_data:
    #         daily_data[date_key] = []
    #     daily_data[date_key].append(record.reached_life)

    # daily_averages = []
    # daily_dates = []
    # for date in sorted(daily_data.keys())[-7:]:
    #     daily_averages.append(np.mean(daily_data[date]))
    #     daily_dates.append(datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d"))

    # # Calculate wear rate
    # wear_rates = []
    # wear_dates = []
    # for i in range(1, min(8, len(values))):
    #     wear_rate = abs(values[i] - values[i - 1])
    #     wear_rates.append(wear_rate)
    #     wear_dates.append(timestamps[i].strftime("%m/%d"))

    # # Define scales
    # scales = {
    #     "x": {
    #         "type": "time",
    #         "time": {
    #             "unit": "day",
    #             "displayFormats": {
    #                 "day": "MMM D"
    #             }
    #         }
    #     }
    # }

    # ROW 1
    # details['cards'].append({
    #     "id": "main_graph",
    #     "title": "Tool Life Trend",
    #     "width": 6,  # Full width
    #     "height": 2,  # 2 units tall
    #     "type": "graph",
    #     "data": {
    #         "type": "line",
    #         "labels": [timestamp.isoformat() for timestamp in timestamps],
    #         "scales": scales,
    #         "datasets": [
    #             {
    #                 "label": "Tool Life",
    #                 "data": values,
    #                 "borderColor": "rgb(75, 192, 192)",
    #                 "backgroundColor": "rgba(75, 192, 192, 0.5)",
    #                 "tension": 0.1,
    #                 "fill": True
    #             },
    #             {
    #                 "label": "Trendline",
    #                 "data": [slope * i + intercept for i in x],
    #                 "borderColor": "rgba(255, 99, 132, 1)",
    #                 "borderWidth": 2,
    #                 "borderDash": [5, 5],
    #                 "fill": False,
    #                 "pointRadius": 0
    #             }
    #         ]
    #     }
    # })
    #
    # # ROW 3+
    # machines = defaultdict(lambda: defaultdict(list))
    # for record in records:
    #     machines[record.machine.name][record.machine_channel].append({
    #         'tool_life': record.reached_life,
    #         'timestamp': record.timestamp,
    #         'settings': record.tool_settings,
    #         'additional_measurements': record.additional_measurements,
    #         'change_reason': {
    #             'name': record.change_reason.name if record.change_reason else "N/A",
    #             'sentiment': record.change_reason.sentiment if record.change_reason else "N/A"
    #         },
    #     })

    return details

async def periodic_data_sender(websocket: WebSocket, db: Session):
    while True:
        await asyncio.sleep(30)
        await send_tool_data(websocket, db)

@router.websocket("/ws/toolLifes")
async def websocket_tools(websocket: WebSocket, db: Session = Depends(get_session)):
    global websocket_filters
    print('got socket request')
    await websocket.accept()
    print('accepted it')

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
