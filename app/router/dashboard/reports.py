from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from app.database_config import get_session
from app.templates.jinja_functions import templates
from app.models import OrderCompletion
from .tools import get_cpu

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

@router.get("/", response_model=None)
async def reports_page(request: Request):
    """
    Render the reports dashboard page.
    """
    return templates.TemplateResponse(
        "dashboard/reports.html.j2",
        {"request": request},
    )

@router.get("/api/data")
async def reports_data(
    selected_products: str = Query('[]'),
    selected_operations: str = Query('[]'),
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_session),
)-> JSONResponse:
    """
    Retrieve report data: cost per piece, finished counts current and previous windows.
    """

    # Get cost per piece metrics from existing CPU endpoint logic
    current_cpu_data = await get_cpu(
        selected_operations=selected_operations,
        selected_products=selected_products,
        start_date=start_date,
        end_date=end_date,
        db=db,
    )

    # Compute previous window
    duration = end_date - start_date
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - duration

    previous_cpu_data = await get_cpu(
        selected_operations=selected_operations,
        selected_products=selected_products,
        start_date=prev_start,
        end_date=prev_end,
        db=db,
    )

    report_rows = []
    for line_name, line_dict in current_cpu_data.items():
        for prod_name, prod_dict in line_dict.get("products", {}).items():
            product_id = prod_dict.get("id")
            # Compute finished pieces for current and previous windows
            workpieces_produced = db.exec(
                select(func.sum(OrderCompletion.quantity))
                .where(OrderCompletion.workpiece_id == product_id)
                .where(OrderCompletion.date >= start_date.date())
                .where(OrderCompletion.date <= end_date.date())
             ).first() or 0

            for op_name, op_dict in prod_dict.get("operations", {}).items():
                current_cpp = op_dict.get("cost_per_piece", 0)

                previous_op_dict = previous_cpu_data.get(line_name, {}).get("products", {}).get(prod_name, {}).get("operations", {}).get(op_name, {})
                previous_cpp = previous_op_dict.get("cost_per_piece", 0)

                total_records = sum(
                    tool.get("total_records", 0)
                    for position in op_dict.get('tool_positions', {}).values()
                    for tool in position['tools']
                )

                previous_total_records = sum(
                    tool.get("total_records", 0)
                    for position in previous_op_dict.get('tool_positions', {}).values()
                    for tool in position['tools']
                )

                reason = ''
                if total_records < 10:
                    reason += f'Unreliable: only {total_records} records found for this timeframe - '
                if previous_total_records < 10:
                    reason += f'Unreliable: only {previous_total_records} records found for previous timeframe - '

                report_rows.append({
                    "line": line_name,
                    "product": prod_name,
                    "operation": op_name,
                    "cost_per_piece": current_cpp,
                    "workpieces_produced": workpieces_produced,
                    "previous_cost_per_piece": previous_cpp,
                    "reason": reason
                })

    return JSONResponse(content={"data": report_rows})
