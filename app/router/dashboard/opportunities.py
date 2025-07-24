from fastapi import APIRouter, Request, Depends
from sqlmodel import Session, select, func
import json
from typing import Optional
from datetime import datetime
from statistics import mean, stdev
from decimal import Decimal
from app.models.recipe import ToolPosition, Recipe
from app.models.tool import ToolLife, Tool
from app.models.workpiece import OrderCompletion

from app.database_config import get_session
from app.templates.jinja_functions import templates

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
)

@router.get("/")
async def dashboard(request: Request):
    """Render the Opportunities dashboard page"""
    return templates.TemplateResponse(
        "dashboard/opportunities.html.j2",
        {"request": request}
    )

@router.get("/api/ranked")
async def get_ranked_opportunities(
    request: Request, 
    start_date: Optional[datetime],
    end_date: Optional[datetime], 
    selected_operations: str = '',
    selected_products: str = '',
    db: Session = Depends(get_session)
    ):
    """
    Return a ranked list of cost saving opportunities.
    Calculates mean tool life, target life (90% expected), and cost-saving opportunities
    based on OrderCompletion volume over the past 365 days.
    """

    selected_operations = json.loads(selected_operations) if selected_operations else []
    selected_products = json.loads(selected_products) if selected_products else []
    # Convert selected operations and products to lists of integers
    selected_operations = [int(op) for op in selected_operations]
    selected_products = [int(product) for product in selected_products]
    
    # Query tool positions with expected life
    statement = select(ToolPosition).where(
        ToolPosition.selected == True).where(
        ToolPosition.expected_life != None,
    )
    if selected_operations:
        statement = statement.where(ToolPosition.recipe.machine_id.in_(selected_operations))
    if selected_products:
        statement = (
            statement
            .join(Recipe, ToolPosition.recipe_id == Recipe.id)
            .where(Recipe.workpiece_id.in_(selected_products))
        )
    statement = statement.order_by(ToolLife.timestamp.asc())
    positions = db.exec(statement).all()

    opportunities = []
    for pos in positions:
        # Fetch tool life records for this position
        lifespans = db.exec(
            select(ToolLife.reached_life)
            .where(
                ToolLife.tool_position_id == pos.id,
                ToolLife.timestamp >= start_date,
                ToolLife.timestamp <= end_date
            )
        ).all()
        if not lifespans:
            continue
        # Compute current mean life
        current_mean = mean(lifespans)
        # Compute target life at 90% of expected
        target_life = pos.expected_life * 0.9
        # Delta life opportunity
        delta = max(target_life - current_mean, 0)
        if delta <= 0:
            continue
        # Sum production volume via OrderCompletion for workpiece
        total_volume = db.exec(
            select(func.sum(OrderCompletion.quantity))
            .where(
                OrderCompletion.workpiece_id == pos.recipe.workpiece_id,
                OrderCompletion.date >= start_date,
                OrderCompletion.date <= end_date
            )
        ).first() or 0

        # Fetch tool and price
        tool = db.get(Tool, pos.tool_id)
        price = float(tool.price) if tool and tool.price else 0.0

        # Cost saving per piece: difference in cost rate
        cost_current = price / current_mean if current_mean > 0 else Decimal(0)
        cost_target = price / pos.expected_life if pos.expected_life > 0 else Decimal(0)
        saving_per_piece = float(cost_current - cost_target)

        # Annual saving opportunity
        saving_opportunity = saving_per_piece * total_volume

        opportunities.append({
            "tool_position_id": pos.id,
            "tool_name": tool.name if tool else "",
            "recipe_name": pos.recipe.name,
            "workpiece_name": pos.recipe.workpiece.name,
            "current_mean_life": round(current_mean, 2),
            "expected_life": pos.expected_life,
            "target_life": round(target_life, 2),
            "total_volume": int(total_volume),
            "saving_per_piece": round(saving_per_piece, 4),
            "saving_opportunity": round(saving_opportunity, 2)
        })

    # Sort by saving opportunity descending
    opportunities.sort(key=lambda x: x["saving_opportunity"], reverse=True)
    return {"opportunities": opportunities}
