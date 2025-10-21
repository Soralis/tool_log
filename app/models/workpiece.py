from typing import Optional, List, TYPE_CHECKING
import datetime as dt
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .recipe import Recipe
    from .user import User
    from .tool import ToolConsumption, ToolLife
    from .machine import Line
    from .model_connections import WorkpieceGroupMembership, WorkpieceLine, WorkpieceGroupLine
else:
    from .model_connections import WorkpieceGroupMembership, WorkpieceLine, WorkpieceGroupLine


class WorkpieceBase(SQLModel):
    name: str = Field(unique=True)
    description: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None


class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    recipes: List['Recipe'] = Relationship(back_populates='workpiece', cascade_delete=True)
    order_completions: List['OrderCompletion'] = Relationship(back_populates='workpiece', cascade_delete=False)
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='workpiece', cascade_delete=False)
    tool_lifes: List['ToolLife'] = Relationship(back_populates='workpiece', cascade_delete=False)
    productions: List['Production'] = Relationship(back_populates='workpiece', cascade_delete=False)
    
    # Many-to-many relationships
    groups: List['WorkpieceGroup'] = Relationship(
        back_populates='workpieces',
        link_model=WorkpieceGroupMembership
    )
    lines: List['Line'] = Relationship(
        back_populates='workpieces',
        link_model=WorkpieceLine
    )

class WorkpieceCreate(WorkpieceBase):
    groups: List[int] = []  # List of workpiece group IDs
    lines: List[int] = []  # List of line IDs


class WorkpieceUpdate(WorkpieceCreate):
    id: int
    active: bool


class WorkpieceRead(SQLModel):
    id: int
    name: str
    active: bool
    line__name: str

class WorkpieceFilter(SQLModel):
    name: str
    active: bool
    line_id: int


class WorkpieceGroup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    
    # Many-to-many relationships
    workpieces: List['Workpiece'] = Relationship(
        back_populates='groups',
        link_model=WorkpieceGroupMembership
    )
    lines: List['Line'] = Relationship(
        back_populates='workpiece_groups',
        link_model=WorkpieceGroupLine
    )
    
    # One-to-many relationships
    recipes: List['Recipe'] = Relationship(back_populates='workpiece_group')
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='workpiece_group')
    tool_lifes: List['ToolLife'] = Relationship(back_populates='workpiece_group')

class WorkpieceGroupCreate(SQLModel):
    name: str
    description: Optional[str] = None
    workpieces: List[int] = []  # List of workpiece IDs
    lines: List[int] = []  # List of line IDs

class WorkpieceGroupUpdate(WorkpieceGroupCreate):
    id: int

class WorkpieceGroupRead(SQLModel):
    id: int
    name: str
    description: Optional[str] = None

class WorkpieceGroupFilter(SQLModel):
    name: str 

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
    date: Optional[dt.date] = None
    line_id: Optional[int] = None
    workpiece_id: Optional[int] = None
    start_time: Optional[dt.time] = None
    end_time: Optional[dt.time] = None
