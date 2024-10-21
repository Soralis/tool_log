from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, ARRAY, Column, String, JSON
from datetime import datetime
from decimal import Decimal
from enum import Enum

class UserRole(str, Enum):
    OPERATOR = "Operator"
    SUPERVISOR = "Supervisor"
    MAINTENANCE = "Maintenance"
    ENGINEER = "Engineer"
   
############# USERS ################

class UserBase(SQLModel):
    initials: str = Field(index=True, max_length=4)
    name: str
    pin: str = Field(max_length=4)
    role: UserRole

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_login: Optional[datetime] = Field(default=None)

    tool_lifes: List["ToolLife"] = Relationship(back_populates="creator")
    performed_maintenances: List["Maintenance"] = Relationship(back_populates="user")

class UserRead(UserBase):
    id: int
    active: bool

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    id: int
    active: bool


############# TOOLS ################

class ToolLife(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pieces_machined: int
    spindle_load: Optional[float] = None
    channel: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now, nullable=False)
    tool_order_id: int = Field(foreign_key="toolorder.id")

    created_by: int = Field(foreign_key="user.id")
    machine_id: int = Field(foreign_key="machine.id")
    tool_id: int = Field(foreign_key="tool.id")
    workpiece_id: int = Field(foreign_key="workpiece.id")

    creator: User = Relationship(back_populates="tool_lifes")
    machine: "Machine" = Relationship(back_populates="tool_lifes")
    tool: "Tool" = Relationship(back_populates="tool_lifes")
    workpiece: "Workpiece" = Relationship(back_populates="tool_lifes")
    tool_order: "ToolOrder" = Relationship(back_populates="tool_lifes")


############# MACHINES ################

class MachineBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    model: Optional[str] = Field(default=None)
    # serial_number: Optional[str] = Field(default=None)
    manufacturer: Optional[str] = Field(default=None)
    # purchase_date: Optional[datetime] = Field(default=None)
    channels: int = Field(gt=0)
    positions: List[str] = Field(default=[], sa_column=Column(JSON))

class Machine(MachineBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    tool_lifes: List[ToolLife] = Relationship(back_populates="machine")
    maintenances: List["Maintenance"] = Relationship(back_populates="machine")

    # created_by: int = Field(foreign_key="user.id")

class MachineCreate(MachineBase):
    pass

class MachineUpdate(MachineBase):
    id: int

class MachineRead(MachineBase):
    id: int



class WorkpieceTool(SQLModel, table=True):
    workpiece_id: Optional[int] = Field(
        default=None, foreign_key="workpiece.id", primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key="tool.id", primary_key=True
    )


###### Tools #######

class ManufacturerBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class Manufacturer(ManufacturerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tools: List["Tool"] = Relationship(back_populates="manufacturer")

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerUpdate(ManufacturerBase):
    id: int


class ToolType(str, Enum):
    MILL = "Mill"
    DRILL = "Drill"
    LATHE = "Lathe"
    BRUSH = "Brush"
    OTHER = "Other"

class ToolBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    tool_type: ToolType
    perishable: bool = Field(default=True)
    manufacturer_id: int = Field(foreign_key="manufacturer.id")

class Tool(ToolBase, table=True):
    manufacturer: Manufacturer = Relationship(back_populates="tools")
    workpieces: List["Workpiece"] = Relationship(back_populates="tools", link_model=WorkpieceTool)
    tool_lifes: List[ToolLife] = Relationship(back_populates="tool")
    tool_orders: List["ToolOrder"] = Relationship(back_populates="tool")
    
class ToolCreate(ToolBase):
    pass

class ToolUpdate(ToolBase):
    pass

class ToolOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id")
    quantity: int
    batch_number: Optional[str] = Field(default=None)
    price_per_unit: Decimal = Field(max_digits=10, decimal_places=2)
    order_date: datetime = Field(default_factory=datetime.now, nullable=False)
    remaining_quantity: int

    tool: Tool = Relationship(back_populates="tool_orders")
    tool_lifes: List[ToolLife] = Relationship(back_populates="tool_order")


class Workpiece(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    material: str
    dimensions: str  # e.g., "100x50x25 mm"
    weight: Optional[float] = None  # Weight in kg
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    tool_lifes: List[ToolLife] = Relationship(back_populates="workpiece")
    tools: List[Tool] = Relationship(back_populates="workpieces", link_model=WorkpieceTool)

class ProgramBase(SQLModel):
    name: str = Field(index=True, unique=True)


class Maintenance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    machine_id: int = Field(foreign_key="machine.id")
    performed_by: int = Field(foreign_key="user.id")
    maintenance_type: str
    description: str
    date_performed: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    next_maintenance_date: Optional[datetime] = Field(default=None)
    cost: Optional[Decimal] = Field(max_digits=10, decimal_places=2, default=None)

    machine: Machine = Relationship(back_populates="maintenances")
    user: User = Relationship(back_populates="performed_maintenances")



