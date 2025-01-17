from fastapi import APIRouter, WebSocket, Request, Depends, WebSocketDisconnect
from sqlmodel import Session, select
from typing import List
import json
import asyncio
import socket

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Tool, ToolLife, RequestLog, ServiceMetrics

router = APIRouter()

# Store active WebSocket connections
active_connections: List[WebSocket] = []


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
    

# 

@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_session)):
    """Render the main dashboard page"""
    return templates.TemplateResponse(
        "dashboard/index.html.j2",
        {
            "request": request,
            "server_address": get_ip_address()
        }
    )

@router.get("/api/dashboard/summary")
async def get_dashboard_summary(db: Session = Depends(get_session)):
    """Get summary statistics for the dashboard"""
    # Get service metrics
    metrics = db.exec(select(ServiceMetrics)).first()
    
    # Get tool statistics
    total_tools = db.exec(select(Tool)).all()
    active_tools = [tool for tool in total_tools if tool.active]
    
    # Get recent tool life entries
    recent_tool_life = db.exec(
        select(ToolLife)
        .order_by(ToolLife.timestamp.desc())
        .limit(100)
    ).all()
    
    # Get recent requests
    recent_requests = db.exec(
        select(RequestLog)
        .order_by(RequestLog.timestamp.desc())
        .limit(100)
    ).all()
    
    return {
        "service_metrics": {
            "total_requests": metrics.total_requests if metrics else 0,
            "total_errors": metrics.total_errors if metrics else 0,
            "avg_response_time": float(metrics.avg_response_time) if metrics else 0
        },
        "tool_metrics": {
            "total_tools": len(total_tools),
            "active_tools": len(active_tools),
            "recent_tool_changes": len(recent_tool_life)
        },
        "request_metrics": {
            "recent_requests": len(recent_requests),
            "recent_errors": sum(1 for req in recent_requests if req.status_code >= 400)
        }
    }

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, db: Session = Depends(get_session)):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            try:
                # Get latest dashboard data
                summary = await get_dashboard_summary(db)
                await websocket.send_text(json.dumps(summary))
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    break
                raise
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)
    finally:
        try:
            await websocket.close()
        except:
            pass  # Ignore errors during close
