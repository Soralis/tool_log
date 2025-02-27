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

def calculate_uptime_percentage(heartbeats: List[datetime], time_horizon: timedelta) -> float:
    """Calculates the uptime percentage over a given time horizon."""
    if not heartbeats:
        return 0.0

    # sort heartbeats by time
    heartbeats.sort()

    start_time = datetime.now(timezone.utc) - time_horizon

    # Filter heartbeats within the time horizon and deduplicate within 5-minute intervals
    valid_heartbeats = []
    last_heartbeat_time = None
    for hb in heartbeats:
        if start_time <= hb <= datetime.now(timezone.utc):
            time_since_last_valid = hb - last_heartbeat_time if last_heartbeat_time else timedelta(seconds=0)
            if last_heartbeat_time is None or time_since_last_valid >= timedelta(seconds=298):
                valid_heartbeats.append(hb)
                last_heartbeat_time = hb

    # Calculate expected vs actual heartbeats
    expected_heartbeats = int(time_horizon.total_seconds() / (5 * 60))  # 5 minutes in seconds
    actual_heartbeats = len(valid_heartbeats)

    # Avoid division by zero
    if expected_heartbeats == 0:
        return 0.0

    # Calculate uptime percentage
    uptime_percentage = (actual_heartbeats / expected_heartbeats) * 100
    return round(min(uptime_percentage, 100.0), 2)  # Cap at 100%


def calculate_uptime_percentage_optimized(heartbeats: List[datetime], time_horizon: timedelta) -> float:
    """Calculates the uptime percentage over a given time horizon without deduplication."""
    if not heartbeats:
        return 0.0

    start_time = datetime.now(timezone.utc) - time_horizon

    # Filter heartbeats within the time horizon
    valid_heartbeats = [hb for hb in heartbeats if start_time <= hb <= datetime.now(timezone.utc)]

    # Calculate expected vs actual heartbeats
    expected_heartbeats = int(time_horizon.total_seconds() / (5 * 60))  # 5 minutes in seconds
    actual_heartbeats = len(valid_heartbeats)

    # Avoid division by zero
    if expected_heartbeats == 0:
        return 0.0

    # Calculate uptime percentage
    uptime_percentage = (actual_heartbeats / expected_heartbeats) * 100
    return round(min(uptime_percentage, 100.0), 2)  # Cap at 100%


async def get_device_status(db: Session) -> List[Dict]:
    """Fetches the status of all log devices."""
    now = datetime.now(timezone.utc)
    devices = db.exec(select(LogDevice)).all()
    device_statuses = []

    for device in devices:
        if device.name != 'Server' and not device.machines:
            continue

        # Calculate time horizons
        one_month_ago = now - timedelta(days=30)

        # Fetch the last heartbeat for the device in the last month
        heartbeats = db.exec(
            select(Heartbeat.timestamp)
            .where(Heartbeat.log_device_id == device.id)
            .where(Heartbeat.timestamp >= one_month_ago)
            .order_by(Heartbeat.timestamp.desc())

        ).all()

        last_heartbeat = heartbeats[0] if heartbeats else None
        # Determine device health
        is_healthy = last_heartbeat and (now - last_heartbeat) <= timedelta(minutes=5)

        # Calculate last seen time
        last_seen = "Never"
        if last_heartbeat:
            time_diff = now - last_heartbeat
            minutes = time_diff.total_seconds() / 60
            if minutes < 1:
                last_seen = "Just now"
            if minutes < 60:
                last_seen = f"{int(minutes)} minutes ago"
            else:
                hours = minutes / 60
                last_seen = f"{int(hours)} hours ago"

        stability_24h = calculate_uptime_percentage_optimized(heartbeats, timedelta(hours=24))
        stability_7d = calculate_uptime_percentage_optimized(heartbeats, timedelta(days=7))
        stability_month = calculate_uptime_percentage_optimized(heartbeats, timedelta(days=30))

        device_statuses.append({
            "Device": ', '.join([machine.name for machine in device.machines]) if device.machines else device.name,
            "Healthy": is_healthy if is_healthy else False,
            "Stability 24h": stability_24h,
            "Stability 7d": stability_7d,
            "Stability month": stability_month,
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
            await asyncio.sleep(5)  # Send data every 5 seconds
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
