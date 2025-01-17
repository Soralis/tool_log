from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Callable
import asyncio
from decimal import Decimal

from app.database_config import engine
from app.models import RequestLog, ServiceMetrics


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
        {"request": request}
    )

@router.get("/requests/metrics")
async def get_metrics():
    db = Session(engine)
    try:
        metrics = db.exec(select(ServiceMetrics)).first()
        if not metrics:
            metrics = ServiceMetrics()
            db.add(metrics)
            db.commit()
        
        return {
            "uptime": (datetime.now() - metrics.start_time).total_seconds(),
            "total_requests": metrics.total_requests,
            "total_errors": metrics.total_errors,
            "error_rate": metrics.total_errors / max(metrics.total_requests, 1),
            "avg_response_time": float(metrics.avg_response_time)
        }
    finally:
        db.close()

@router.get("/requests/recent-requests")
async def get_recent_requests():
    db = Session(engine)
    try:
        logs = db.exec(
            select(RequestLog)
            .order_by(RequestLog.timestamp.desc())
            .limit(100)
        ).all()
        
        return [
            {
                "method": log.method,
                "endpoint": log.endpoint,
                "status_code": log.status_code,
                "response_time": float(log.response_time),
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    finally:
        db.close()
