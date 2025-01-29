from typing import Optional, List, TYPE_CHECKING
import datetime as dt
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .recipe import Recipe
    from .user import User
    from .tool import ToolConsumption


class WorkpieceBase(SQLModel):
    name: str = Field(unique=True)
    description: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None


class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    recipes: List['Recipe'] = Relationship(back_populates='workpiece')
    order_completions: List['OrderCompletion'] = Relationship(back_populates='workpiece')
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='workpiece')

class WorkpieceCreate(WorkpieceBase):
    pass


class WorkpieceUpdate(WorkpieceCreate):
    id: int
    active: bool


class WorkPieceRead(SQLModel):
    id: int
    name: str
    active: bool


class OrderCompletionBase(SQLModel):
    quantity: int
    vendor: Optional[str] = Field(default=None, index=True)
    batch: Optional[str] = Field(default=None, index=True)
    customer: Optional[str] = Field(default=None, index=True)
    order: Optional[str] = Field(default=None, index=True)
    document_number: str = Field(unique=True, index=True)
    date: dt.date = Field(index=True)
    time: dt.time
    value: float

    workpiece_id: int = Field(foreign_key='workpiece.id', ondelete='CASCADE', index=True)
    user_id: Optional[int] = Field(foreign_key='user.id', ondelete='SET NULL', index=True)

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
