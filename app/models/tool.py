from typing import Optional, List, Dict, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from sqlalchemy import UniqueConstraint
from datetime import datetime
from decimal import Decimal
from enum import IntEnum
from .model_connections import RecipeTool

if TYPE_CHECKING:
    from .recipe import Recipe, ToolPosition
    from .machine import Machine
    from .user import User
    from .manufacturer import Manufacturer


class ToolTypeBase(SQLModel):
    name: str = Field(index=True, unique=True)
    perishable: bool = Field(default=True)


class ToolType(ToolTypeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    tool_attributes: List['ToolAttribute'] = Relationship(back_populates='tool_type', cascade_delete=True)
    change_reasons: List['ChangeReason'] = Relationship(back_populates='tool_type', cascade_delete=True)
    tools: List['Tool'] = Relationship(back_populates='tool_type')


class ToolTypeCreate(ToolTypeBase):
    change_reasons: List['ChangeReason'] = []
    tool_attributes: List['ToolAttribute'] = []


class ToolTypeUpdate(ToolTypeCreate):
    id: int
    active: bool


class ToolTypeRead(ToolTypeBase):
    id: int
    active: bool


class ToolAttribute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    unit: str
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: ToolType = Relationship(back_populates='tool_attributes')

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)


class ToolAttributeCreate(SQLModel):
    name: str
    unit: str
    tool_type_id: int


class ToolAttributeUpdate(ToolAttributeCreate):
    id: int


class ToolAttributeRead(SQLModel):
    id: int
    name: str
    unit: str


class Sentiment(IntEnum):
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5

class ChangeReasonBase(SQLModel):
    name: str = Field(index=True)
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL)


class ChangeReason(ChangeReasonBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: ToolType = Relationship(back_populates='change_reasons')

    tool_lifes: List['ToolLife'] = Relationship(back_populates='change_reason')

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)


class ChangeReasonCreate(ChangeReasonBase):
    pass


class ChangeReasonUpdate(ChangeReasonCreate):
    id: int
    active: bool


class ChangeReasonRead(ChangeReasonBase):
    id: int


class ToolBase(SQLModel):
    name: str = Field(index=True)
    number: str = Field(index=True, unique=True)
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
    tool_type: ToolType = Relationship(back_populates='tools')
    active: bool = Field(default=True, nullable=False)
    recipes: List['Recipe'] = Relationship(back_populates='tools', link_model=RecipeTool)
    tool_lifes: List['ToolLife'] = Relationship(back_populates='tool')
    tool_orders: List['ToolOrder'] = Relationship(back_populates='tool')
    tool_positions: List['ToolPosition'] = Relationship(back_populates='tool')


class ToolCreate(ToolBase):
    pass


class ToolUpdate(ToolCreate):
    id: int
    active: bool


class ToolRead(SQLModel):
    id: int
    name: str
    manufacturer: 'Manufacturer'
    tool_type: ToolType
    active: bool


class ToolOrderBase(SQLModel):
    tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
    quantity: int
    remaining_quantity: int
    batch_number: Optional[str] = Field(default=None)
    gross_price: Decimal = Field(max_digits=10, decimal_places=2)


class ToolOrder(ToolOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool: Tool = Relationship(back_populates='tool_orders')
    tool_lifes: List['ToolLife'] = Relationship(back_populates='tool_order')
    fulfilled: bool = Field(default=False, nullable=False)
    order_date: datetime = Field(default_factory=datetime.now, nullable=False)
    delivery_date: Optional[datetime] = Field(default=None)
    user_id: Optional[int] = Field(foreign_key='user.id')
    user: 'User' = Relationship(back_populates='tool_orders')


class ToolOrderCreate(ToolOrderBase):
    pass


class ToolOrderUpdate(ToolOrderCreate):
    id: int
    delivery_date: Optional[datetime] = Field(default=None)
    fulfilled: bool = Field(default=False, nullable=False)


class ToolOrderRead(SQLModel):
    id: int
    name: str
    fulfilled: bool
    tool: Tool


class ToolLifeBase(SQLModel):
    reached_life: int
    machine_channel: int


class ToolLife(ToolLifeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now, nullable=False)
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    additional_measurements: Dict = Field(default_factory=dict, sa_column=Column(JSON))

    tool_order_id: Optional[int] = Field(foreign_key='toolorder.id')
    created_by: int = Field(foreign_key='user.id')
    machine_id: int = Field(foreign_key='machine.id')
    tool_id: int = Field(foreign_key='tool.id')
    recipe_id: int = Field(foreign_key='recipe.id')
    change_reason_id: int = Field(foreign_key='changereason.id')
    tool_position_id: int = Field(foreign_key='toolposition.id')

    creator: 'User' = Relationship(back_populates='tool_lifes')
    machine: 'Machine' = Relationship(back_populates='tool_lifes')
    tool: Tool = Relationship(back_populates='tool_lifes')
    recipe: 'Recipe' = Relationship(back_populates='tool_lifes')
    tool_order: ToolOrder = Relationship(back_populates='tool_lifes')
    change_reason: ChangeReason = Relationship(back_populates='tool_lifes')
    tool_position: 'ToolPosition' = Relationship(back_populates='tool_lifes')


class ToolLifeCreate(ToolLifeBase):
    pass


class ToolLifeUpdate(ToolLifeCreate):
    id: int


class ToolLifeRead(SQLModel):
    id: int
    name: str
    tool: Tool
