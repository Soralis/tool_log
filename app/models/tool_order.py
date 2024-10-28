from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from decimal import Decimal


################ TOOL ORDER ######################

class ToolOrderBase(SQLModel):
    tool_id: int = Field(foreign_key="tool.id")
    quantity: int
    batch_number: Optional[str] = Field(default=None)
    gross_price: Decimal = Field(max_digits=10, decimal_places=2)

class ToolOrder(ToolOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool: "Tool" = Relationship(back_populates="tool_orders")
    tool_lifes: List["ToolLife"] = Relationship(back_populates="tool_order")
    remaining_quantity: int
    order_date: datetime = Field(default_factory=datetime.now, nullable=False)
    delivery_date: Optional[datetime] = Field(default=None)
    user_id: int = Field(foreign_key="user.id")
    user: "User" = Relationship(back_populates="tool_orders")

class ToolOrderCreate(ToolOrderBase):
    pass

class ToolOrderUpdate(ToolOrderBase):
    delivery_date: Optional[datetime] = Field(default=None)


from .user import User
from .tool import Tool
from .tool_life import ToolLife