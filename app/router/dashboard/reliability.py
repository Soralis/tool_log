from fastapi import APIRouter, Request, Depends, Body
from app.templates.jinja_functions import templates
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database_config import get_session
from app.models import ToolLife, Machine, ToolConsumption
from typing import Dict, List, Optional
from . import tool_lifes_cards as tc


router = APIRouter(
    prefix="/reliability",
    tags=["Reliability"],
)

async def machine_reliability(db: Session, machine_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
    # Fetch machine reliability data from the database
    machine = db.get(Machine, machine_id)
    query = (select(ToolConsumption)
             .where(ToolConsumption.machine_id == machine_id))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    tool_consumptions = db.exec(query).all()

    query = (select(ToolLife)
             .where(ToolLife.machine_id == machine_id))
    if start_date:
        query = query.where(ToolLife.timestamp >= start_date)
    if end_date:
        query = query.where(ToolLife.timestamp <= end_date)
    tool_lifes = db.exec(query).all()

    match_by_weeks = {}
    shifts = set()
    shifts.add('total_reports')
    for tool_life in tool_lifes:
        # week_number = tool_life.timestamp.isocalendar()[1]
        weeks_sunday = tool_life.timestamp - timedelta(days=tool_life.timestamp.weekday() + 1)
        weeks_sunday = weeks_sunday.date()
        if weeks_sunday not in match_by_weeks:
            match_by_weeks[weeks_sunday] = {
                'total_reports': 0,
                'tool_consumption': 0
            }
        shift_name = tool_life.user.shift.name if tool_life.user and tool_life.user.shift else 'Unknown Shift'
        if shift_name not in match_by_weeks[weeks_sunday]:
            match_by_weeks[weeks_sunday][shift_name] = 0
            shifts.add(shift_name)
        match_by_weeks[weeks_sunday][shift_name] += tool_life.tool_count / tool_life.tool.max_uses
        match_by_weeks[weeks_sunday]['total_reports'] += tool_life.tool_count / tool_life.tool.max_uses
    
    for tool_consumption in tool_consumptions:
        weeks_sunday = tool_consumption.datetime - timedelta(days=tool_consumption.datetime.weekday() + 1)
        weeks_sunday = weeks_sunday.date()
        if weeks_sunday not in match_by_weeks:
            match_by_weeks[weeks_sunday] = {
                'total_reports': 0,
                'tool_consumption': 0
            }
        match_by_weeks[weeks_sunday]['tool_consumption'] += tool_consumption.quantity   

    series_dict = {shift: {
            'type': 'line',
            'smooth': True,
            'name': shift,
            'data': []
        } for shift in shifts}
    
    if start_date and machine.name == 'OP45-Broach':
        pass

    weeks = sorted(list(match_by_weeks.keys()))
    for week in weeks:
        week_data = match_by_weeks[week]
        for shift in shifts:
            reports = week_data.get(shift, 0)
            series_dict[shift]['data'].append(int(100 * reports/week_data['tool_consumption'] if week_data['tool_consumption'] != 0 else 0))

    series = [data for data in series_dict.values()]
    xAxis= {'type': "category", 'data': [week.isoformat() for week in weeks]}
    graph = tc.graph_card(machine.name, series, xAxis)

    
    return graph


async def machine_reliability_stacked(db: Session, machine_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict[str, str]]:
    # Fetch machine reliability data from the database
    machine = db.get(Machine, machine_id)
    query = (select(ToolConsumption)
             .where(ToolConsumption.machine_id == machine_id))
    if start_date:
        query = query.where(ToolConsumption.datetime >= start_date)
    if end_date:
        query = query.where(ToolConsumption.datetime <= end_date)
    tool_consumptions = db.exec(query).all()

    query = (select(ToolLife)
             .where(ToolLife.machine_id == machine_id))
    if start_date:
        query = query.where(ToolLife.timestamp >= start_date)
    if end_date:
        query = query.where(ToolLife.timestamp <= end_date)
    tool_lifes = db.exec(query).all()

    match_by_weeks = {}
    shifts = set()
    # shifts.add('total_reports')
    for tool_life in tool_lifes:
        # week_number = tool_life.timestamp.isocalendar()[1]
        weeks_sunday = tool_life.timestamp - timedelta(days=tool_life.timestamp.weekday() + 1)
        weeks_sunday = weeks_sunday.date()
        if weeks_sunday not in match_by_weeks:
            match_by_weeks[weeks_sunday] = {
                # 'total_reports': 0,
                'tool_consumption': 0
            }
        shift_name = tool_life.user.shift.name if tool_life.user and tool_life.user.shift else 'Unknown Shift'
        if shift_name not in match_by_weeks[weeks_sunday]:
            match_by_weeks[weeks_sunday][shift_name] = 0
            shifts.add(shift_name)
        match_by_weeks[weeks_sunday][shift_name] += tool_life.tool_count / tool_life.tool.max_uses
        # match_by_weeks[weeks_sunday]['total_reports'] += tool_life.tool_count / tool_life.tool.max_uses
    
    for tool_consumption in tool_consumptions:
        weeks_sunday = tool_consumption.datetime - timedelta(days=tool_consumption.datetime.weekday() + 1)
        weeks_sunday = weeks_sunday.date()
        if weeks_sunday not in match_by_weeks:
            match_by_weeks[weeks_sunday] = {
                # 'total_reports': 0,
                'tool_consumption': 0
            }
        match_by_weeks[weeks_sunday]['tool_consumption'] += tool_consumption.quantity   

    series_dict = {shift: {
            'type': 'line',
            'stack': 'Total',
            'areaStyle': {},
            'emphasis': {
                'focus': 'series'
            },
            'name': shift,
            'data': []
        } for shift in shifts}
    
    if start_date and machine.name == 'OP45-Broach':
        pass

    weeks = sorted(list(match_by_weeks.keys()))
    for week in weeks:
        week_data = match_by_weeks[week]
        for shift in shifts:
            reports = week_data.get(shift, 0)
            series_dict[shift]['data'].append(reports)
        
        if 'tool_consumption' not in series_dict:
            series_dict['tool_consumption'] = {
                'type': 'line',
                'name': 'Tool Consumption',
                'data': []
            }
        series_dict['tool_consumption']['data'].append(week_data.get('tool_consumption', 0))

    series = [data for data in series_dict.values()]
    xAxis= {'type': "category", 'data': [week.isoformat() for week in weeks]}
    graph = tc.graph_card(machine.name, series, xAxis)

    
    return graph

@router.get("/")
async def tools(request: Request, 
                db: Session = Depends(get_session), 
            ):
    # Get initial graphs without date filtering
    machine_ids = db.exec(select(Machine.id).order_by(Machine.name)).all()
    graphs = [await machine_reliability(db, id) for id in machine_ids]
    return templates.TemplateResponse(
        "dashboard/log_reliability.html.j2",  # Updated template path
        {
            "request": request,
            "graphs": graphs
        }
    )

@router.post("/api/log_reliability")
async def log_reliability(db: Session = Depends(get_session), 
                start_date: str = Body(None),
                end_date: str = Body(None),
            ):
    start_date = datetime.fromisoformat(start_date) if start_date else None
    end_date = datetime.fromisoformat(end_date) if end_date and end_date != 'null' else None
    machine_ids = db.exec(select(Machine.id).order_by(Machine.name)).all()
    graphs = [await machine_reliability_stacked(db, id, start_date, end_date) for id in machine_ids]

    return graphs