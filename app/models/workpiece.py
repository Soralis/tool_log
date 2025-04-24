from typing import Optional, List, TYPE_CHECKING
import datetime as dt
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .recipe import Recipe
    from .user import User
    from .tool import ToolConsumption
    from .machine import Line


class WorkpieceBase(SQLModel):
    name: str = Field(unique=True)
    description: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None
    line_id: Optional[int] = Field(foreign_key='line.id', ondelete='SET NULL')


class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    recipes: List['Recipe'] = Relationship(back_populates='workpiece', cascade_delete=True)
    order_completions: List['OrderCompletion'] = Relationship(back_populates='workpiece', cascade_delete=False)
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='workpiece', cascade_delete=False)
    line: Optional['Line'] = Relationship(back_populates='workpieces')
    productions: List['Production'] = Relationship(back_populates='workpiece', cascade_delete=False)

class WorkpieceCreate(WorkpieceBase):
    pass


class WorkpieceUpdate(WorkpieceCreate):
    id: int
    active: bool


class WorkpieceRead(SQLModel):
    id: int
    name: str
    active: bool
    line__name: str

class WorkpieceFilter(SQLModel):
    name: str = None
    active: bool = None
    line_id: int


class OrderCompletionBase(SQLModel):
    quantity: int = Field(nullable=False)
    vendor: Optional[str] = Field(default=None, index=True)
    batch: Optional[str] = Field(default=None, index=True)
    customer: Optional[str] = Field(default=None, index=True)
    order: Optional[str] = Field(default=None, index=True)
    document_number: str = Field(unique=True, index=True, nullable=False)
    date: dt.date = Field(index=True, nullable=False)
    time: dt.time = Field(nullable=False)
    value: float = Field(nullable=False)

    workpiece_id: int = Field(foreign_key='workpiece.id', ondelete='CASCADE', index=True, nullable=False)
    user_id: Optional[int] = Field(foreign_key='user.id', ondelete='SET NULL', index=True, default=None)

class OrderCompletion(OrderCompletionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workpiece: Workpiece = Relationship(back_populates='order_completions')
    user: 'User' = Relationship(back_populates='order_completions')

class OrderCompletionCreate(OrderCompletionBase):
    pass

class OrderCompletionUpdate(OrderCompletionBase):
    id: int

class OrderCompletionRead(SQLModel):
    id: int
    quantity: int


class ProductionBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int = Field(nullable=False)
    date: dt.date = Field(index=True, nullable=False)
    start_time: dt.time = Field(nullable=False)
    end_time: dt.time = Field(nullable=False)
    workpiece_id: int = Field(foreign_key='workpiece.id', ondelete='CASCADE', index=True, nullable=False)
    line_id: Optional[int] = Field(foreign_key='line.id', ondelete='SET NULL')
    target: int = Field(nullable=False)
    finished: int = Field(nullable=False)
    started: int = Field(nullable=False)
    comment: Optional[str] = Field(default=None)


class Production(ProductionBase, table=True):
    workpiece: Workpiece = Relationship(back_populates='productions')
    line: Optional['Line'] = Relationship(back_populates='productions')

class ProductionCreate(ProductionBase):
    pass

class ProductionUpdate(ProductionCreate):
    id: int

class ProductionRead(SQLModel):
    id: int
    quantity: int
    date: dt.date
    start_time: dt.time
    end_time: dt.time
    target: int
    finished: int
    started: int
    comment: Optional[str] = None

class ProductionFilter(SQLModel):
    date: dt.date = None
    line_id: int = None
    workpiece_id: int = None
    start_time: dt.time = None
    end_time: dt.time = None