from fastapi import APIRouter, Request, Depends, Query, WebSocket
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from sqlmodel import Session, select
from sqlalchemy import func, case
import socket
import asyncio
import json

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Heartbeat, LogDevice

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


@router.get("/api/filter-options")
async def get_filter_options(request: Request, db: Session = Depends(get_session)):
    """Get available filter options (products and operations)"""
    products = db.exec(select(Workpiece)).all()
    products = {workpiece.name: workpiece.id for workpiece in products}
    operations = db.exec(select(Machine)).all()
    operations = {operation.name: operation.id for operation in operations}
    
    return {
        "products": products,
        "operations": operations
    }

@router.get("/")
async def dashboard(request: Request):
    """Render the main dashboard page"""
    return templates.TemplateResponse(
        "dashboard/index.html.j2",
        {
            "request": request,
            "server_address": get_ip_address()
        }
    )

@router.get("/api/filter")
async def get_dashboard_filter(request: Request, 
                              db: Session = Depends(get_session),
                              selected_products: List[int] = Query(None),
                              selected_operations: List[int] = Query(None),
                              start_date: str = Query(None),
                              end_date: str = Query(None)):
    """Get filtered dashboard content"""
    # Construct query with filters
    query = select(ToolConsumption)
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    
    data = db.exec(query).all()
    
    return templates.TemplateResponse("dashboard/partials/cards.html.j2", {
        "request": request,
        "data": data,
        "selected_products": selected_products or [],
        "selected_operations": selected_operations or []
    })


async def get_device_status(db: Session) -> List[Dict]:
    """Fetches the status of all log devices."""
    now = datetime.now()
    devices = db.exec(select(LogDevice)).all()
    device_statuses = []

    # Define time horizons
    time_horizon_24h = timedelta(hours=24)
    time_horizon_7d = timedelta(days=7)
    time_horizon_30d = timedelta(days=30)

    # Heartbeat frequency (minutes)
    heartbeat_frequency = 1

    # Calculate expected heartbeats for each time horizon
    expected_heartbeats_24h = int(time_horizon_24h.total_seconds() / (heartbeat_frequency * 60))
    expected_heartbeats_7d = int(time_horizon_7d.total_seconds() / (heartbeat_frequency * 60))
    expected_heartbeats_30d = int(time_horizon_30d.total_seconds() / (heartbeat_frequency * 60))

    for device in devices:
        if device.name != 'Server' and not device.machines:
            continue

        # Construct the query to count heartbeats for different time horizons using aggregate filters
        stmt = select(
            func.count(Heartbeat.timestamp).filter(Heartbeat.timestamp >= now - time_horizon_24h).label("count_24h"),
            func.count(Heartbeat.timestamp).filter(Heartbeat.timestamp >= now - time_horizon_7d).label("count_7d"),
            func.count(Heartbeat.timestamp).filter(Heartbeat.timestamp >= now - time_horizon_30d).label("count_30d"),
        ).where(Heartbeat.log_device_id == device.id)

        result = db.exec(stmt).first()

        # Extract heartbeat counts from the result
        heartbeats_24h = result.count_24h if result else 0
        heartbeats_7d = result.count_7d if result else 0
        heartbeats_30d = result.count_30d if result else 0

        # Calculate device health
        is_healthy = device.last_seen and (now - device.last_seen) <= timedelta(minutes=5) if device.last_seen else False

        # Calculate last seen time
        last_seen = "Never"
        if device.last_seen:
            time_diff = now - device.last_seen
            minutes = time_diff.total_seconds() / 60
            if minutes < 1:
                last_seen = "Just now"
            elif minutes < 60:
                last_seen = f"{int(minutes)} minutes ago"
            else:
                hours = minutes / 60
                last_seen = f"{int(hours)} hours ago"

        # Calculate stability percentages
        stability_24h = (heartbeats_24h / expected_heartbeats_24h) * 100 if expected_heartbeats_24h else 0
        stability_7d = (heartbeats_7d / expected_heartbeats_7d) * 100 if expected_heartbeats_7d else 0
        stability_month = (heartbeats_30d / expected_heartbeats_30d) * 100 if expected_heartbeats_30d else 0

        device_statuses.append({
            "Device": ', '.join([machine.name for machine in device.machines]) if device.machines else device.name,
            "IP": device.ip_address,
            "Healthy": is_healthy,
            "Stability 24h": round(min(stability_24h, 190.0), 2),
            "Stability 7d": round(min(stability_7d, 100.0), 2),
            "Stability month": round(min(stability_month, 100.0), 2),
            "Last Seen": last_seen,
        })

    # Sort the device statuses
    device_statuses.sort(key=lambda x: (
        x["Healthy"],  # Sort by Healthy (False first)
        x["Stability 24h"],  # Then by Stability 24h (ascending)
        x["Stability 7d"],  # Then by Stability 7d (ascending)
        x["Stability month"]  # Then by Stability month (ascending)
    ))

    return device_statuses


async def send_heartbeat_data(websocket: WebSocket, db: Session):
    """Sends device status data to the WebSocket client."""
    device_statuses = await get_device_status(db)
    await websocket.send_text(json.dumps(device_statuses))


async def periodic_data_sender(websocket: WebSocket, db: Session):
    """Periodically sends heartbeat data to the WebSocket client."""
    while True:
        try:
            await send_heartbeat_data(websocket, db)
            await asyncio.sleep(30)  # Send data every 30 seconds
        except Exception as e:
            print(f"Error in periodic_data_sender: {e}")
            break


@router.websocket("/ws/heartbeat")
async def websocket_heartbeat(websocket: WebSocket, db: Session = Depends(get_session)):
    """WebSocket endpoint for streaming heartbeat data."""
    await websocket.accept()
    data_sender_task = asyncio.create_task(periodic_data_sender(websocket, db))
    try:
        while True:
            await websocket.receive_text()  # Keep the connection alive
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        data_sender_task.cancel()
        try:
            await websocket.close()
        except:
            pass  # Ignore errors during close
