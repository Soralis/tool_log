from fastapi import APIRouter, WebSocket, Request, Depends, WebSocketDisconnect
from sqlmodel import Session, select
from typing import List
import json
import asyncio
import socket

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Tool, ToolLife, RequestLog, ServiceMetrics, Workpiece, Machine

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
    

def get_products(db: Session):
    workpieces = db.exec(select(Workpiece)).all()
    return {workpiece.name: workpiece.id for workpiece in workpieces}

def get_operations(db: Session):
    operations = db.exec(select(Machine)).all()
    return {operation.name: operation.id for operation in operations}

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
async def get_dashboard_summary(db: Session = Depends(get_session), 
                                selected_products: List[int] = None, 
                                selected_operations: List[int] = None):
    """Get summary statistics for the dashboard"""
    products = get_products(db)
    operations = get_operations(db)
    
    return {
        "products": products,
        "operations": operations,
    }

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, db: Session = Depends(get_session)):
    await websocket.accept()
    active_connections.append(websocket)
    user_filters = {"selected_products": [], "selected_operations": []}
    
    try:
        while True:
            try:
                # # Receive filter updates from client
                # message = await websocket.receive_text()
                # data = json.loads(message)
                # user_filters["selected_products"] = data.get("selectedProducts", [])
                # user_filters["selected_operations"] = data.get("selectedOperations", [])
                
                # Get filtered dashboard data
                summary = await get_dashboard_summary(db, user_filters["selected_products"], user_filters["selected_operations"])
                await websocket.send_text(json.dumps(summary))
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.TimeoutError:
                # If no message received, send current summary
                summary = await get_dashboard_summary(db, user_filters["selected_products"], user_filters["selected_operations"])
                await websocket.send_text(json.dumps(summary))
                await asyncio.sleep(5)
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
