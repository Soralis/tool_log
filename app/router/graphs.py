from fastapi import APIRouter, WebSocket, Request, Depends
import asyncio
import json
from app.templates.jinja_functions import templates
import socket
import httpx
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
        
        # Try to get public IP
        try:
            response = httpx.get('https://api.ipify.org', timeout=2.0)
            if response.status_code == 200:
                public_ip = response.text
                return f"{hostname} (Local: {local_ip}, Public: {public_ip})"
        except:
            pass
            
        # Fallback to just local IP if public IP fetch fails
        return f"{hostname} (Local: {local_ip})"
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

async def get_tool_life_data(db: Session, limit:int = 50) -> Dict:
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
            mean = np.mean(values)
            std = np.std(values)
            
            # Calculate trendline
            x = np.arange(len(values))
            slope, intercept, _, _, _ = linregress(x, values)
            trendline = [slope * i + intercept for i in x]
            
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
