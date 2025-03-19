from typing import Optional, List, Dict, TYPE_CHECKING
from .tool_type import Sentiment
from pydantic import field_validator
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from sqlalchemy import UniqueConstraint
from datetime import datetime as dt
from decimal import Decimal
from .model_connections import RecipeTool

if TYPE_CHECKING:
    from .recipe import Recipe, ToolPosition
    from .machine import Machine
    from .user import User
    from .manufacturer import Manufacturer
    from .workpiece import Workpiece
    from .tool_type import ToolType, ChangeReason, Sentiment
    from .model_connections import ToolAttributeValue

class ToolBase(SQLModel):
    name: str = Field(index=True)
    number: str = Field(index=True, unique=True)
    erp_number: Optional[str] = Field(default=None, index=True, unique=True)
    cpn_number: Optional[str] = Field(default=None, index=True, unique=True)
    description: Optional[str] = None
    
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    manufacturer_id: int = Field(foreign_key='manufacturer.id', ondelete='CASCADE')
    regrind: bool = Field(default=False)
    max_uses: int = Field(default=1)
    has_serialnumber: bool = Field(default=False)

    __table_args__ = (UniqueConstraint('name', 'tool_type_id', 'manufacturer_id'),)


class Tool(ToolBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    manufacturer: 'Manufacturer' = Relationship(back_populates='tools')
    inventory: Optional[int] = Field(default=0)
    price: Decimal = Field(default=0.0, ge=0)
    stop_order: bool = Field(default=False)
    tool_type: 'ToolType' = Relationship(back_populates='tools')
    active: bool = Field(default=True, nullable=False)
    recipes: List['Recipe'] = Relationship(back_populates='tools', link_model=RecipeTool, cascade_delete=False)
    tool_lifes: List['ToolLife'] = Relationship(back_populates='tool', cascade_delete=True)
    tool_orders: List['ToolOrder'] = Relationship(back_populates='tool', cascade_delete=True)
    tool_positions: List['ToolPosition'] = Relationship(back_populates='tool', cascade_delete=True)
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='tool', cascade_delete=True)
    tool_attributes: List['ToolAttributeValue'] = Relationship(back_populates="tool", cascade_delete=True)


class ToolCreate(ToolBase):
    # tool_attributes: List['ToolAttributeValue'] = []
    pass


class ToolUpdate(ToolCreate):
    id: int
    active: bool
    inventory: Optional[int] = Field(default=None)
    stop_order: bool = Field(default=False)


class ToolRead(SQLModel):
    id: int
    name: str
    inventory: int
    stop_order: bool
    manufacturer: 'Manufacturer'
    tool_type: 'ToolType'
    active: bool


class ToolOrderBase(SQLModel):
    tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
    quantity: int
    number: str = Field(index=True)
    suffix: str
    line: str
    order_date: dt = Field(default_factory=dt.now, nullable=False)
    estimated_delivery_date: Optional[dt] = Field(default=None)
    gross_price: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    tool_price: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    tracking_number: Optional[str] = Field(default=None)
    shipping_company: Optional[str] = Field(default=None)


class ToolOrder(ToolOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool: Tool = Relationship(back_populates='tool_orders')
    batch_number: Optional[str] = Field(default=None)
    fulfilled: bool = Field(default=False, nullable=False)
    deliveries: List['OrderDelivery'] = Relationship(back_populates='order', cascade_delete=True)
    delivered: int = Field(default=0)
        
    user_id: Optional[int] = Field(foreign_key='user.id', ondelete='SET NULL')
    user: 'User' = Relationship(back_populates='tool_orders')
    notes: List['Note'] = Relationship(back_populates='tool_order', cascade_delete=True)

    __table_args__ = (UniqueConstraint('number', 'suffix', 'line'),)
        
    def calculate_delivered_amount(self) -> int:
        delivered = sum(delivery.quantity for delivery in self.deliveries)
        self.delivered = delivered
        if delivered == self.quantity:
            self.fulfilled = True
        else:
            self.fulfilled = False
        return delivered


class ToolOrderCreate(ToolOrderBase):
    pass


class ToolOrderUpdate(ToolOrderCreate):
    id: int
    fulfilled: bool = Field(default=False, nullable=False)
    batch_number: Optional[str] = Field(default=None)


class ToolOrderRead(ToolOrderUpdate):
    pass

class OrderDeliveryBase(SQLModel):
    order_id: int = Field(foreign_key='toolorder.id', ondelete='CASCADE')
    delivery_date: dt = Field(default_factory=dt.now)
    quantity: int
    
class OrderDelivery(OrderDeliveryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order: ToolOrder = Relationship(back_populates='deliveries')
    notes: List['Note'] = Relationship(back_populates='order_delivery', cascade_delete=True)

    __table_args__ = (UniqueConstraint('order_id', 'delivery_date', 'quantity'),)

class OrderDeliveryCreate(OrderDeliveryBase):
    pass

class OrderDeliveryUpdate(OrderDeliveryCreate):
    id: int
    delivery_date: Optional[dt] = Field(default=None)

class OrderDeliveryRead(SQLModel):
    id: int
    order_id: int
    delivery_date: dt
    quantity: int


class ToolLifeBase(SQLModel):
    reached_life: int
    machine_channel: int


class ToolLife(ToolLifeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: dt = Field(default_factory=dt.now, nullable=False)
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    additional_measurements: Dict = Field(default_factory=dict, sa_column=Column(JSON))

    # tool_order_id: Optional[int] = Field(foreign_key='toolorder.id')
    created_by: Optional[int] = Field(foreign_key='user.id', ondelete='SET NULL')
    machine_id: Optional[int] = Field(foreign_key='machine.id', ondelete='SET NULL')
    tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
    recipe_id: Optional[int] = Field(foreign_key='recipe.id', ondelete='SET NULL')
    change_reason_id: Optional[int] = Field(foreign_key='changereason.id', ondelete='SET NULL')
    tool_position_id: Optional[int] = Field(foreign_key='toolposition.id', ondelete='SET NULL')

    creator: 'User' = Relationship(back_populates='tool_lifes')
    machine: 'Machine' = Relationship(back_populates='tool_lifes')
    tool: Tool = Relationship(back_populates='tool_lifes')
    recipe: 'Recipe' = Relationship(back_populates='tool_lifes')
    # tool_order: ToolOrder = Relationship(back_populates='tool_lifes')
    change_reason: 'ChangeReason' = Relationship(back_populates='tool_lifes')
    tool_position: 'ToolPosition' = Relationship(back_populates='tool_lifes')
    notes: List['Note'] = Relationship(back_populates='tool_life', cascade_delete=True)


class ToolLifeCreate(ToolLifeBase):
    notes: List['Note'] = []


class ToolLifeUpdate(ToolLifeCreate):
    id: int


class ToolLifeRead(SQLModel):
    id: int
    name: str
    tool: Tool

class ToolLifeFilter(SQLModel):
    machine: 'Machine'
    tool: 'Tool'
    tool_type: 'ToolType'
    timestamp: dt
    creator: 'User'

class NoteBase(SQLModel):
    note: str
    user_id: int = Field(foreign_key='user.id')
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL)

    tool_life_id: Optional[int] = Field(foreign_key='toollife.id', ondelete='CASCADE', index=True)
    tool_order_id: Optional[int] = Field(foreign_key='toolorder.id', ondelete='CASCADE', index=True)
    order_delivery_id: Optional[int] = Field(foreign_key='orderdelivery.id', ondelete='CASCADE', index=True)

class Note(NoteBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: dt = Field(default_factory=dt.now)
    updated_at: dt = Field(default_factory=dt.now)

    tool_life: Optional[ToolLife] = Relationship(back_populates='notes')
    tool_order: Optional[ToolOrder] = Relationship(back_populates='notes')
    order_delivery: Optional[OrderDelivery] = Relationship(back_populates='notes')
    user: 'User' = Relationship(back_populates='notes')

class NoteRead(SQLModel):
    id: int
    note: str

def check_at_least_one_relationship_id(values, field_names):
    if not any(values.get(field) is not None for field in field_names):
        raise ValueError(
            f'At least one of {", ".join(field_names)} must be provided'
        )
    return values


class NoteCreate(NoteBase):
    @field_validator('tool_life_id', 'tool_order_id', 'order_delivery_id')
    @classmethod
    def validate_at_least_one(cls, v, values):
        field_names = ['tool_life_id', 'tool_order_id', 'order_delivery_id']
        return check_at_least_one_relationship_id(values, field_names)


class NoteUpdate(NoteCreate):
    id: int

class ToolConsumption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    datetime: dt = Field(index=True)
    number: int = Field(index=True, unique=True)
    consumption_type: str = Field(index=True)
    quantity: int
    value: Decimal = Field(max_digits=10, decimal_places=2)
    price: Decimal = Field(max_digits=10, decimal_places=2)
    
    machine_id: Optional[int] = Field(foreign_key='machine.id', default=None, ondelete='SET NULL')
    tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
    recipe_id: Optional[int] = Field(foreign_key='recipe.id', default=None, ondelete='SET NULL')
    tool_position_id: Optional[int] = Field(foreign_key='toolposition.id', default=None, ondelete='SET NULL')
    user_id: Optional[int] = Field(foreign_key='user.id', default=None, ondelete='SET NULL')
    workpiece_id: Optional[int] = Field(foreign_key='workpiece.id', ondelete='SET NULL', default=None)

    machine: 'Machine' = Relationship(back_populates='tool_consumptions')
    tool: 'Tool' = Relationship(back_populates='tool_consumptions')
    recipe: 'Recipe' = Relationship(back_populates='tool_consumptions')
    tool_position: 'ToolPosition' = Relationship(back_populates='tool_consumptions')
    user: 'User' = Relationship(back_populates='tool_consumptions')
    workpiece: 'Workpiece' = Relationship(back_populates='tool_consumptions')


class ToolConsumptionCreate(SQLModel):
    datetime: dt
    number: int
    consumption_type: str
    quantity: int
    value: Decimal
    price: Decimal
    machine_id: Optional[int]
    tool_id: int
    recipe_id: Optional[int]
    tool_position_id: Optional[int]
    user_id: Optional[int]
    workpiece_id: Optional[int]
