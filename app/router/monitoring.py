from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Callable
import asyncio
from decimal import Decimal

from ..database_config import engine
from ..models import RequestLog, ServiceMetrics

router = APIRouter()  # Remove prefix to avoid potential routing issues

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# Middleware to log requests
async def log_request(request: Request, call_next: Callable, db: Session):
    start_time = datetime.utcnow()
    response = await call_next(request)
    end_time = datetime.utcnow()
    
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
    metrics.last_updated = datetime.utcnow()
    
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

@router.websocket("/monitoring/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Create a new database session for this WebSocket connection
        db = Session(engine)
        
        try:
            # Send initial metrics
            metrics = db.exec(select(ServiceMetrics)).first()
            if metrics:
                await websocket.send_json({
                    "type": "metrics",
                    "data": {
                        "uptime": (datetime.utcnow() - metrics.start_time).total_seconds(),
                        "total_requests": metrics.total_requests,
                        "total_errors": metrics.total_errors,
                        "avg_response_time": float(metrics.avg_response_time)
                    }
                })
            
            # Send recent requests
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
            
            # Keep connection alive and update metrics periodically
            while True:
                await asyncio.sleep(1)
                metrics = db.exec(select(ServiceMetrics)).first()
                if metrics:
                    await websocket.send_json({
                        "type": "metrics",
                        "data": {
                            "uptime": (datetime.utcnow() - metrics.start_time).total_seconds(),
                            "total_requests": metrics.total_requests,
                            "total_errors": metrics.total_errors,
                            "avg_response_time": float(metrics.avg_response_time)
                        }
                    })
        
        finally:
            db.close()
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
        raise e

@router.get("/monitoring/metrics")
async def get_metrics():
    db = Session(engine)
    try:
        metrics = db.exec(select(ServiceMetrics)).first()
        if not metrics:
            metrics = ServiceMetrics()
            db.add(metrics)
            db.commit()
        
        return {
            "uptime": (datetime.utcnow() - metrics.start_time).total_seconds(),
            "total_requests": metrics.total_requests,
            "total_errors": metrics.total_errors,
            "error_rate": metrics.total_errors / max(metrics.total_requests, 1),
            "avg_response_time": float(metrics.avg_response_time)
        }
    finally:
        db.close()

@router.get("/monitoring/recent-requests")
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
