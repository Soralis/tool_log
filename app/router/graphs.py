from fastapi import APIRouter, WebSocket, Request, Depends, Response, HTTPException
import asyncio
import json
from app.templates.jinja_functions import templates
from datetime import datetime, timedelta
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
            labels = [record.timestamp.strftime("%m/%d") for record in records]
            
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
                "labels": labels,
                "values": values,
                "mean": mean,
                "std": std,
                "trendline": trendline
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
    
    # Predict replacement date based on trend
    current_life = values[-1]
    days_to_replacement = max(1, int((100 - current_life) / abs(slope))) if slope < 0 else 30
    predicted_replacement = datetime.now() + timedelta(days=days_to_replacement)
    
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
    
    details = {
        "tool_info": {
            "id": tool.id,
            "name": tool.name,
            "number": tool.number,
            "manufacturer": tool.manufacturer,
            "total_uses": len(records),
            "installation_date": "yadaday"
        },
        "current_stats": {
            "current_life": current_life,
            "average_life": mean,
            "trend_slope": slope,
            "predicted_replacement": predicted_replacement.strftime("%Y-%m-%d")
        },
        "historical_data": {
            "daily_averages": {
                "labels": daily_dates,
                "values": daily_averages
            },
            "wear_rate": {
                "labels": wear_dates,
                "values": wear_rates
            }
        },
        "process_info": {
            "last_maintenance": 'xxx',
            "optimal_speed": "xxx RPM",
            "optimal_feed": "xxx mm/min",
            "coolant_type": "Standard",
            "material_compatibility": ["General Purpose"]
        }
    }
    
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
