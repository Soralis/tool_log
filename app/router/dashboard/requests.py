from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List, Callable, Dict
import asyncio
from decimal import Decimal
from sqlalchemy import func
import socket
import json

from app.database_config import engine, get_session
from app.models import RequestLog, ServiceMetrics, Heartbeat, LogDevice


router = APIRouter()

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# Middleware to log requests
async def log_request(request: Request, call_next: Callable, db: Session):
    start_time = datetime.now()
    response = await call_next(request)
    end_time = datetime.now()
    
    # Calculate response time in seconds
    response_time = Decimal(str((end_time - start_time).total_seconds()))
    
    # Create request log
    log = RequestLog(
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        response_time=response_time
    )
    db.add(log)
    
    # Update metrics
    metrics = db.exec(select(ServiceMetrics)).first()
    if not metrics:
        metrics = ServiceMetrics()
        db.add(metrics)
    
    metrics.total_requests += 1
    if response.status_code >= 400:
        metrics.total_errors += 1
    
    # Update average response time
    metrics.avg_response_time = (
        (metrics.avg_response_time * (metrics.total_requests - 1) + response_time)
        / metrics.total_requests
    )
    metrics.last_updated = datetime.now()
    
    db.commit()
    
    # Notify WebSocket clients
    log_data = {
        "type": "request",
        "data": {
            "method": log.method,
            "endpoint": log.endpoint,
            "status_code": log.status_code,
            "response_time": float(log.response_time),
            "timestamp": log.timestamp.isoformat()
        }
    }
    for connection in active_connections:
        try:
            await connection.send_json(log_data)
        except:
            pass  # Ignore failed sends
    
    return response

@router.websocket("/ws/requests")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Create a new database session for this WebSocket connection
        db = Session(engine)
        
        try:
            while True:
                # Force a new database query each time
                db.expire_all()
                metrics = db.exec(select(ServiceMetrics)).first()
                
                if metrics:
                    # Explicitly load the metrics attributes to ensure fresh data
                    db.refresh(metrics)
                    
                    await websocket.send_json({
                        "type": "metrics",
                        "data": {
                            "uptime": (datetime.now() - metrics.start_time).total_seconds(),
                            "total_requests": metrics.total_requests,
                            "total_errors": metrics.total_errors,
                            "avg_response_time": float(metrics.avg_response_time)
                        }
                    })
                
                # Send recent requests on first connect
                if not hasattr(websocket, 'initial_data_sent'):
                    recent_logs = db.exec(
                        select(RequestLog)
                        .order_by(RequestLog.timestamp.desc())
                        .limit(100)
                    ).all()
                    
                    for log in reversed(recent_logs):
                        await websocket.send_json({
                            "type": "request",
                            "data": {
                                "method": log.method,
                                "endpoint": log.endpoint,
                                "status_code": log.status_code,
                                "response_time": float(log.response_time),
                                "timestamp": log.timestamp.isoformat()
                            }
                        })
                    websocket.initial_data_sent = True
                
                await asyncio.sleep(1)
        
        finally:
            db.close()
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        raise e

@router.get("/requests")
async def requests(request: Request):
    from app.templates.jinja_functions import templates
    return templates.TemplateResponse(
        "dashboard/requests.html.j2",  # Updated template path
        {"request": request,
         "server_address": get_ip_address()}
    )


### Hardware Stati
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
            "Stability 24h": round(min(stability_24h, 100.0), 2),
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
