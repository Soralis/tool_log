from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.templates.jinja_functions import templates
from sqlmodel import Session, select
from app.database_config import get_session
from app.models import ToolOrder

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)

@router.get("/", response_class=templates.TemplateResponse)
async def orders_dashboard(request: Request, session: Session = Depends(get_session)):
    orders = session.exec(select(ToolOrder)).all()
    return templates.TemplateResponse("dashboard/orders.html.j2", {"request": request, "orders": orders})

@router.post("/createOrder")
async def create_order(request: Request, session: Session = Depends(get_session)):
    form_data = await request.form()
    # Process form data to create a new order
    # TODO: ... (Implementation to handle order creation) ...
    return {"message": "Order created successfully"}

@router.put("/updateOrder/{order_id}")
async def update_order(order_id: int, request: Request, session: Session = Depends(get_session)):
    form_data = await request.form()
    # Process form data to update an existing order
    # TODO: ... (Implementation to handle order update) ...
    return {"message": f"Order {order_id} updated successfully"}

@router.delete("/deleteOrder/{order_id}")
async def delete_order(order_id: int, session: Session = Depends(get_session)):
    # Delete an order from the database
    # TODO: ... (Implementation to handle order deletion) ...
    return {"message": f"Order {order_id} deleted successfully"}

@router.get("/order_details/{order_id}")
async def order_details(request: Request, order_id: int, session: Session = Depends(get_session)):
    # Fetch order details from the database
    query = select(ToolOrder).where(ToolOrder.id == order_id)
    order = session.exec(query).first()
    order.order_date = order.order_date.date()
    order.estimated_delivery_date = order.estimated_delivery_date.date() if order.estimated_delivery_date else None
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/{order_id}/createDelivery")
async def create_delivery(order_id: int, request: Request, session: Session = Depends(get_session)):
    form_data = await request.form()
    # Process form data to create a new delivery for the order
    # TODO: ... (Implementation to handle delivery creation) ...
    return {"message": f"Delivery for order {order_id} created successfully"}

@router.put("/{order_id}/updateDelivery/{delivery_id}")
async def update_delivery(order_id: int, delivery_id: int, request: Request, session: Session = Depends(get_session)):
    form_data = await request.form()
    # Process form data to update an existing delivery for the order
    # TODO: ... (Implementation to handle delivery update) ...
    return {"message": f"Delivery {delivery_id} for order {order_id} updated successfully"}

@router.delete("/{order_id}/deleteDelivery/{delivery_id}")
async def delete_delivery(order_id: int, delivery_id: int, session: Session = Depends(get_session)):
    # Delete a delivery for an order from the database
    # TODO: ... (Implementation to handle delivery deletion) ...
    return {"message": f"Delivery {delivery_id} for order {order_id} deleted successfully"}
