from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.templates.jinja_functions import templates
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.database_config import get_session
from app.models import ToolOrder, ToolType, Tool, OrderDelivery, Note, User
from datetime import datetime
import json


router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


@router.get("/tool_types")
async def get_tool_types(session: Session = Depends(get_session)):
    tool_types = session.exec(select(ToolType)).all()
    return tool_types


@router.get("/tools/{tool_id}")
async def get_tool(tool_id: int, session: Session = Depends(get_session)):
    tool = session.get(Tool, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool_dict = {
            "id": tool.id,
            "name": tool.name,
            "number": tool.number,
            "regrind": tool.regrind,
            "tool_type": tool.tool_type.name,
            "tool_type_id": tool.tool_type_id,
            "tool_type_name": tool.tool_type.name,
            "cpn_number": tool.cpn_number,
            "erp_number": tool.erp_number,
            "manufacturer": tool.manufacturer.name,
            "description": tool.description,
            'inventory': tool.inventory,
        }
    return tool_dict


@router.get("/tools")
async def get_tools(tool_type_id: int = None, session: Session = Depends(get_session)):
    query = select(Tool)
    if tool_type_id:
        query = query.where(Tool.tool_type_id == tool_type_id)
    tools = session.exec(query).all()
    # sort tools by name
    tools.sort(key=lambda tool: tool.name)
    return tools


@router.get("/", response_class=templates.TemplateResponse)
async def orders_dashboard(request: Request, session: Session = Depends(get_session)):
    query = select(ToolOrder).options(selectinload(ToolOrder.tool).selectinload(Tool.tool_type))
    orders = session.exec(query).all()
    return templates.TemplateResponse("dashboard/orders.html.j2", {"request": request, "orders": orders})


def prepare_toolOrder(form_data:dict, tool_order:ToolOrder):
    gross_price = round(float(form_data.get("gross_price")), 2) if form_data.get("gross_price") else None
    tool_price = round(float(form_data.get("tool_price")), 2) if form_data.get("tool_price") else None
    quantity = int(form_data.get("quantity"))

    tool_id = int(form_data.get("tool_id")) if form_data.get("tool_id") else None
    if not tool_id:
        raise HTTPException(status_code=400, detail="Tool is required")

    if not gross_price and not tool_price:
        raise HTTPException(status_code=400, detail="Gross price or tool price are required")
    
    if gross_price and not tool_price:
        tool_price = round(gross_price / quantity, 3)
    elif tool_price and not gross_price:
        gross_price = round(tool_price * quantity, 2)
    if gross_price and tool_price:
        if int(gross_price / quantity) != int(tool_price):
            raise HTTPException(status_code=400, detail="If both gross price AND tool price are given, gross price must be equal to tool price * quantity")

    tool_order.tool_id= tool_id
    tool_order.order_number= form_data.get("order_number")
    tool_order.quantity= quantity
    tool_order.gross_price= gross_price
    tool_order.tool_price= tool_price
    tool_order.order_date= datetime.strptime(form_data.get("order_date"), '%Y-%m-%d').date() if form_data.get("order_date") else datetime.now()
    tool_order.estimated_delivery_date= datetime.strptime(form_data.get("estimated_delivery_date"), '%Y-%m-%d').date() if form_data.get("estimated_delivery_date") else None

    return tool_order


@router.post("/createOrder")
async def create_order(request: Request, session: Session = Depends(get_session)):
    try:
        body = await request.body()
        form_data = json.loads(body.decode('utf-8'))
        
        new_toolorder = ToolOrder()
        toolorder_db = prepare_toolOrder(form_data, new_toolorder)

        session.add(toolorder_db)
        session.commit()
        session.refresh(toolorder_db)

        return JSONResponse(content={"message": f"Order {toolorder_db.id} created successfully"})

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/updateOrder/{order_id}")
async def update_order(order_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        body = await request.body()
        form_data = json.loads(body.decode('utf-8'))

        tool_order = session.get(ToolOrder, order_id)
        if not tool_order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        toolorder_db = prepare_toolOrder(form_data, tool_order)

        session.add(toolorder_db)
        session.commit()
        return JSONResponse(content={"message": f"Order {order_id} updated successfully"})

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/deleteOrder/{order_id}")
async def delete_order(order_id: int, session: Session = Depends(get_session)):
    # Fetch the order from the database
    order = session.get(ToolOrder, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Delete the order
    session.delete(order)
    session.commit()

    return {"message": f"Order {order_id} deleted successfully"}


@router.get("/order_details/{order_id}")
async def order_details(request: Request, order_id: int, session: Session = Depends(get_session)):
    # Fetch order details from the database
    query = select(ToolOrder).where(ToolOrder.id == order_id)
    order = session.exec(query).first()
    order.estimated_delivery_date = order.estimated_delivery_date.date() if order.estimated_delivery_date else None
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_data = {
        "id": order.id,
        "order_number": order.order_number,
        "quantity": order.quantity,
        "gross_price": order.gross_price,
        "tool_price": order.tool_price,
        "order_date": order.order_date.date(),
        "estimated_delivery_date": order.estimated_delivery_date.isoformat() if order.estimated_delivery_date else None,
        'fulfilled': order.fulfilled,
        "tool": {
            "id": order.tool.id,
            "name": order.tool.name,
            "number": order.tool.number,
            "regrind": order.tool.regrind,
            "tool_type": order.tool.tool_type.name,
            "tool_type_id": order.tool.tool_type_id,
            "cpn_number": order.tool.cpn_number,
            "erp_number": order.tool.erp_number,
            "manufacturer": order.tool.manufacturer.name,
            "description": order.tool.description,
            'inventory': order.tool.inventory,
        },
        'delivery_notes': [{'delivery_date': delivery.delivery_date, 'quantity': delivery.quantity, 'notes': "\n".join([note.note for note in delivery.notes]) } 
                           for delivery in order.deliveries]
    }
    return order_data


@router.post("/{order_id}/createDelivery")
async def create_delivery(order_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        form_data = await request.form()
        delivery_date = form_data.get("delivery_date")
        quantity = form_data.get('quantity')
        delivery_notes = form_data.get("delivery_notes")

        toolorder: ToolOrder = session.exec(select(ToolOrder).where(ToolOrder.id==order_id)).first()
        if toolorder is None:
            raise HTTPException(status_code=404, detail="ToolOrder not found")

        delivery = OrderDelivery(
            delivery_date=datetime.fromisoformat(delivery_date),
            quantity=int(quantity),
            order_id=int(order_id),
        )
        rando_user = session.exec(select(User)).first()
        if delivery_notes:
            note = Note(
                note=delivery_notes,
                user_id=rando_user.id,
            )
            delivery.notes.append(note)
        
        toolorder.deliveries.append(delivery)
        toolorder.delivered += delivery.quantity

        if toolorder.quantity == toolorder.delivered:
            toolorder.fulfilled = True
        else:
            toolorder.fulfilled = False

        session.add(toolorder)
        session.commit()
        # session.refresh(delivery)

        return {"message": f"Delivery for order {order_id} created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
