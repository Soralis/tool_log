from sqlalchemy import event
from sqlalchemy.orm import object_session
from app.models.tool import OrderDelivery, ToolOrder

def update_order_delivered(target: OrderDelivery) -> None:
    session = object_session(target)
    if session is None:
        return
    order = session.get(ToolOrder, target.order_id)
    if order:
        order.delivered = order.calculate_delivered_amount()

@event.listens_for(OrderDelivery, "after_insert")
def after_orderdelivery_insert(mapper, connection, target: OrderDelivery) -> None:
    update_order_delivered(target)

@event.listens_for(OrderDelivery, "after_update")
def after_orderdelivery_update(mapper, connection, target: OrderDelivery) -> None:
    update_order_delivered(target)

@event.listens_for(OrderDelivery, "after_delete")
def after_orderdelivery_delete(mapper, connection, target: OrderDelivery) -> None:
    update_order_delivered(target)
