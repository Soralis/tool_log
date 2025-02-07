from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
import socket
from datetime import datetime

from app.templates.jinja_functions import templates
from app.database_config import get_session
from app.models import Workpiece, Machine, ToolConsumption, Machine

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

@router.get("/api/example-card")
async def get_example_card(request: Request,
                          db: Session = Depends(get_session),
                          selected_products: List[int] = Query([]),
                          selected_operations: List[int] = Query([]),
                          start_date: str = Query(None),
                          end_date: str = Query(None)):
    """Get example card data based on filters"""
    start_date = datetime.fromisoformat(start_date) if start_date else None
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None
    # Example query using filters
    query = select(ToolConsumption)
    query = query.where(ToolConsumption.workpiece_id.in_(selected_products))
    query = query.where(ToolConsumption.machine_id.in_(selected_operations))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    
    data = db.exec(query).all()
    
    # Calculate some example metrics
    total_consumptions = len(data)
    avg_tool_life = 798.4321
    
    return templates.TemplateResponse("dashboard/partials/dashboard-cards/example_card.html.j2", {
        "request": request,
        "total_consumptions": total_consumptions,
        "avg_tool_life": round(avg_tool_life, 2)
    })

@router.get("/api/filter")
async def get_dashboard_filter(request: Request, 
                              db: Session = Depends(get_session),
                              selected_products: List[int] = Query(None),
                              selected_operations: List[int] = Query(None),
                              start_date: str = Query(None),
                              end_date: str = Query(None)):
    """Get filtered dashboard content"""

    print('hier kommt ne anfrage')
    print(selected_products)
    print(selected_operations)
    print(start_date)
    print(end_date)
    
    
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


@router.get("/api/spend-summary")
async def get_spend_summary(request: Request,
                            db: Session = Depends(get_session),
                            selected_products: str = Query(),
                            selected_operations: str = Query(),
                            start_date: str = Query(None),
                            end_date: str = Query(None)):
    """Get spend summary data based on filters"""
    start_date = datetime.fromisoformat(start_date) if start_date else None
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None

    selected_products = [int(x) for x in selected_products.split(",") if x] if selected_products else []
    selected_operations = [int(x) for x in selected_operations.split(",") if x] if selected_operations else []

    query = select(Machine.name, ToolConsumption.value)
    query = query.join(Machine, Machine.id == ToolConsumption.machine_id)
    query = query.where(ToolConsumption.workpiece_id.in_(selected_products))
    query = query.where(ToolConsumption.machine_id.in_(selected_operations))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)

    data = db.exec(query).all()

    # Group data by date and calculate total spend
    spend_summary = {}
    for item in data:
        name = item.name
        if name not in spend_summary:
            spend_summary[name] = 0
        spend_summary[name] += float(item.value)

    # Prepare data for chart
    labels = list(spend_summary.keys())
    values = list(spend_summary.values())

    chart_data = {
        'name': 'Spend Summary',
        "labels": labels,
        "series": values
    }

    print(chart_data)

    return JSONResponse(chart_data)
