from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException
import asyncio
import json
from app.templates.jinja_functions import templates
from datetime import datetime
from collections import defaultdict
import socket
from sqlmodel import Session, select
from app.database_config import get_session
from app.models.tool import Tool, ToolLife
from typing import Dict, List
import numpy as np
from scipy.stats import linregress
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

async def get_tool_graphs(db: Session) -> List[Dict]:
    # Get all active tools that have tool life records
    statement = select(Tool).where(Tool.active == True)
    tools = db.exec(statement).all()
    
    graphs = []
    for tool in tools:
        # Check if tool has any life records
        statement = select(ToolLife).where(ToolLife.tool_id == tool.id).limit(1)
        if db.exec(statement).first():
            graphs.append({
                "id": f"tool_{tool.id}",
                "type": "line",
                "title": f"{tool.name} (#{tool.number})"
            })
    
    return graphs

async def get_tool_life_data(db: Session, limit: int = 50) -> Dict:
    # Get active tools with life records
    statement = select(Tool).where(Tool.active == True)
    tools = db.exec(statement).all()
    
    data = {}
    for tool in tools:
        # Get only the last 10 records for this tool, ordered by timestamp
        statement = (
            select(ToolLife)
            .where(ToolLife.tool_id == tool.id)
            .order_by(ToolLife.timestamp.desc())
            .limit(limit)
        )
        records = list(db.exec(statement))
        
        # Only include tools that have records
        if records:
            # Reverse to get chronological order
            records.reverse()
            values = [record.reached_life for record in records]
            
            # Calculate statistics
            if len (values) > 1:
                mean = np.mean(values)
                std = np.std(values)
                
                # Calculate trendline
                x = np.arange(len(values))
                slope, intercept, _, _, _ = linregress(x, values)
                trendline = [slope * i + intercept for i in x]

            else:
                mean = values[0]
                std = 0
                trendline = [mean]
            
            data[f"tool_{tool.id}"] = {
                "labels": [record.timestamp.isoformat() for record in records],
                "values": values,
                "mean": mean,
                "std": std,
                "trendline": trendline,
                "scales": {
                    "x": {
                        "type": "time",
                        "time": {
                            "unit": "day",
                            "displayFormats": {
                                "day": "MMM D"
                            }
                        }
                    }
                }
            }
    
    return data

@router.get("/graphs")
async def graphs(request: Request, db: Session = Depends(get_session)):
    graphs = await get_tool_graphs(db)
    return templates.TemplateResponse(
        "graphs.html.j2",
        {
            "request": request,
            "server_address": get_ip_address(),
            "graphs": graphs
        }
    )

@router.get("/api/tool/{tool_id}/details")
async def get_tool_details(tool_id: int, db: Session = Depends(get_session)):
    """Get detailed information about a specific tool"""
    # Get tool information
    tool = db.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    # Get tool life records
    statement = (
        select(ToolLife)
        .where(ToolLife.tool_id == tool_id)
        .order_by(ToolLife.timestamp.desc())
        .limit(50)
    )
    records = list(db.exec(statement))
    records.reverse()  # Chronological order
    
    if not records:
        raise HTTPException(status_code=404, detail="No tool life data found")
    
    # Calculate statistics
    values = [record.reached_life for record in records]
    timestamps = [record.timestamp for record in records]
    mean = np.mean(values)
    std = np.std(values)
    
    # Calculate trendline
    x = np.arange(len(values))
    slope, intercept, _, _, _ = linregress(x, values)
        
    # Calculate daily averages (last 7 days)
    daily_data = {}
    for record in records:
        date_key = record.timestamp.strftime("%Y-%m-%d")
        if date_key not in daily_data:
            daily_data[date_key] = []
        daily_data[date_key].append(record.reached_life)
    
    daily_averages = []
    daily_dates = []
    for date in sorted(daily_data.keys())[-7:]:
        daily_averages.append(np.mean(daily_data[date]))
        daily_dates.append(datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d"))
    
    # Calculate wear rate
    wear_rates = []
    wear_dates = []
    for i in range(1, min(8, len(values))):
        wear_rate = abs(values[i] - values[i-1])
        wear_rates.append(wear_rate)
        wear_dates.append(timestamps[i].strftime("%m/%d"))

    # Define cards for the modal
    details = {
        "title": f"{tool.name} (#{tool.number})",
        "cards": []
    }

    details['cards'].append({"id": "main_graph", "title": "Tool Life Trend",
                "width": 6,  # Full width
                "height": 2,  # 2 units tall
                "type": "graph",
                "data": {
                    "type": "line",
                    "labels": [timestamp.isoformat() for timestamp in timestamps],
                    "scales": {
                        "x": {
                            "type": "time",
                            "time": {
                                "unit": "day",
                                "displayFormats": {
                                    "day": "MMM D"
                                }
                            }
                        }
                    },
                    "datasets": [
                        {
                            "label": "Tool Life",
                            "data": values,
                            "borderColor": "rgb(75, 192, 192)",
                            "backgroundColor": "rgba(75, 192, 192, 0.5)",
                            "tension": 0.1,
                            "fill": True
                        },
                        {
                            "label": "Trendline",
                            "data": [slope * i + intercept for i in x],
                            "borderColor": "rgba(255, 99, 132, 1)",
                            "borderWidth": 2,
                            "borderDash": [5, 5],
                            "fill": False,
                            "pointRadius": 0
                        }
                    ]
                }
            }
        )
    details['cards'].append({"id": "current_stats", "title": "Current Statistics",
            "width": 3,  # One third width
            "height": 2,
            "type": "stats",
            "data": [
                {"label": "Current Life", "value": f"{values[-1]:.2f}"},
                {"label": "Average Life", "value": f"{mean:.2f} ± {std:.2f} ({std/mean:.0%})"},
                {"label": "Trend Slope", "value": f"{slope:.2f}"},
                {"label": "Last Replacement", "value": timestamps[-1].strftime("%Y/%m/%d %H:%M")},
            ]
        }
    )
    details['cards'].append({"id": "tool_info", "title": "Tool Information",
            "width": 3,  # One third width
            "height": 2,
            "type": "stats",
            "data": [
                {"label": "Tool Number", "value": str(tool.number)},
                {'label': 'Tool Type', 'value': tool.tool_type.name + ' (perishable)' if tool.tool_type.perishable else ' (durable)'},
                {'label': 'Description', 'value': tool.description},
                {"label": "Manufacturer", "value": tool.manufacturer.name},
                {"label": "Total Uses", "value": str(len(records))},
                {'label': 'Cost', 'value': '1000'}
            ]
        }
    )

    machines = defaultdict(lambda: defaultdict(list))
    for record in records:
        machines[record.machine.name][record.machine_channel].append({'tool_life': record.reached_life,
                                                                       'timestamp': record.timestamp,
                                                                       'settings': record.tool_settings,
                                                                       'additional_measurements': record.additional_measurements,
                                                                       'change_reason': {
                                                                           'name': record.change_reason.name,
                                                                           'sentiment': record.change_reason.sentiment},
                                                                        })
        
    # Add a card for each machine with all its channels
    for machine_name, channels in machines.items():
        # Get all unique timestamps across all channels
        all_timestamps = set()
        for channel_records in channels.values():
            all_timestamps.update(record['timestamp'] for record in channel_records)
        
        # Sort timestamps chronologically
        sorted_timestamps = sorted(all_timestamps)
        timestamp_labels = [ts.isoformat() for ts in sorted_timestamps]
        
        # Create datasets for each channel
        datasets = []
        colors = [
            ["rgb(255, 205, 86)", "rgba(255, 205, 86, 0.5)"],  # Yellow
            ["rgb(153, 102, 255)", "rgba(153, 102, 255, 0.5)"],  # Purple
            ["rgb(75, 192, 192)", "rgba(75, 192, 192, 0.5)"],  # Teal
            ["rgb(255, 99, 132)", "rgba(255, 99, 132, 0.5)"],  # Pink
            ["rgb(54, 162, 235)", "rgba(54, 162, 235, 0.5)"],  # Blue
        ]
        
        for i, (channel, records) in enumerate(channels.items()):
            color_idx = i % len(colors)
            sorted_records = sorted(records, key=lambda x: x['timestamp'])
            
            datasets.append({
                "label": f"Channel {channel}",
                "data": sorted_records,
                "parsing": {
                    "xAxisKey": "timestamp",
                    "yAxisKey": "tool_life"
                },
                "borderColor": colors[color_idx][0],
                "tension": 0.1,
                "fill": False,
                "pointRadius": 5,
                "pointHoverRadius": 8,
                "pointBorderWidth": 2,
                "pointBackgroundColor": "white",
                "pointBorderColor": colors[color_idx][0]
            })
        
        details['cards'].append({
            "id": f"machine_{machine_name}",
            "title": f"{machine_name} Tool Life by Channel",
            "width": 6,  # Full width
            "height": 2,  # 2 units tall
            "type": "graph",
            "data": {
                "type": "line",
                "labels": timestamp_labels,
                "scales": {
                    "x": {
                        "type": "time",
                        "time": {
                            "unit": "day",
                            "displayFormats": {
                                "day": "MMM D"
                            }
                        }
                    }
                },
                "datasets": datasets,
                "interaction": {
                    "intersect": True,
                    "mode": "point"
                },
                "plugins": {
                    "tooltip": {
                        "callbacks": {
                            "afterLabel": "function(context) { return 'Change Reason: ' + context.raw.change_reason.name; }"
                        }
                    }
                }
            }
        })
        
        # Calculate change reason statistics
        all_reasons = set()
        channel_reasons = {}
        machine_reasons = defaultdict(int)
        total_machine_records = 0
        
        # Collect all unique reasons and count occurrences
        for channel, records in channels.items():
            channel_reasons[channel] = defaultdict(int)
            for record in records:
                reason = record['change_reason']['name']
                all_reasons.add(reason)
                channel_reasons[channel][reason] += 1
                machine_reasons[reason] += 1
                total_machine_records += 1
        
        # Convert counts to percentages
        reason_datasets = []
        
        # Add machine total dataset
        machine_percentages = []
        for reason in sorted(all_reasons):
            percentage = (machine_reasons[reason] / total_machine_records) * 100
            machine_percentages.append(percentage)
        
        reason_datasets.append({
            "label": f"{machine_name} Total",
            "data": machine_percentages,
            "backgroundColor": "rgb(128, 128, 128)",  # Gray for total
            "borderWidth": 1
        })
        
        # Add channel datasets
        for i, (channel, reasons) in enumerate(sorted(channel_reasons.items())):
            channel_total = sum(reasons.values())
            percentages = []
            for reason in sorted(all_reasons):
                percentage = (reasons[reason] / channel_total) * 100
                percentages.append(percentage)
            
            color_idx = i % len(colors)
            reason_datasets.append({
                "label": f"Channel {channel}",
                "data": percentages,
                "backgroundColor": colors[color_idx][0],
                "borderWidth": 1
            })
        
        # Add change reasons chart
        details['cards'].append({
            "id": f"machine_{machine_name}_reasons",
            "title": f"{machine_name} Change Reasons",
            "width": 6,  # Full width
            "height": 2,  # 2 units tall
            "type": "graph",
            "data": {
                "type": "bar",
                "labels": sorted(all_reasons),
                "datasets": reason_datasets,
                "options": {
                    "scales": {
                        "y": {
                            "beginAtZero": True,
                            "title": {
                                "display": True,
                                "text": "Percentage"
                            }
                        }
                    },
                    "plugins": {
                        "tooltip": {
                            "callbacks": {
                                "label": "function(context) { return context.dataset.label + ': ' + context.raw.toFixed(1) + '%'; }"
                            }
                        }
                    }
                }
            }
        })

    return details

@router.websocket("/ws/graphs")
async def websocket_graphs(websocket: WebSocket, db: Session = Depends(get_session)):
    await websocket.accept()
    
    try:
        while True:
            try:
                # Get latest tool life data
                data = await get_tool_life_data(db)
                await websocket.send_text(json.dumps(data))
                await asyncio.sleep(5)  # Update every second
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    break
                raise
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass  # Ignore errors during close
