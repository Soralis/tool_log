from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from decimal import Decimal
from enum import Enum
from datetime import datetime


#################### CHANGE OVERS ########################

class ChangeOverBase(SQLModel):
    machine_id: int = Field(foreign_key="machine.id")
    recipe_id: int = Field(foreign_key="recipe.id")

class ChangeOver(ChangeOverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    performed_by: int = Field(foreign_key="user.id")
    timestamps: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    machine: "Machine" = Relationship(back_populates="change_overs")
    user: "User" = Relationship(back_populates="performed_change_overs")
    recipe: "Recipe" = Relationship(back_populates="change_overs")

class ChangeOverCreate(ChangeOverBase):
    pass


################## LOG DEVICE ########################
class LogDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    active: bool = Field(default=True, nullable=False)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    machine_id: Optional[int] = Field(default=None, foreign_key="machine.id")
    machine: Optional["Machine"] = Relationship(back_populates="log_device")

class LogDeviceSetMachine(SQLModel):
    machine_id: int

############# MACHINES ################

class MachineBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    model: Optional[str] = Field(default=None)
    manufacturer: Optional[str] = Field(default=None)
    channels: int = Field(gt=0)

class Machine(MachineBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    log_device: Optional["LogDevice"] = Relationship(back_populates="machine")

    tool_lifes: List["ToolLife"] = Relationship(back_populates="machine")
    recipes: List["Recipe"] = Relationship(back_populates="machine")
    change_overs: List["ChangeOver"] = Relationship(back_populates="machine")

    # created_by: int = Field(foreign_key="user.id")

class MachineCreate(MachineBase):
    pass

class MachineUpdate(MachineBase):
    id: int

class MachineRead(MachineBase):
    id: int


###### MANUFACTURER #######

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


############# CONNECTION TABLES ################

class RecipeTool(SQLModel, table=True):
    recipe_id: Optional[int] = Field(
        default=None, foreign_key="recipe.id", primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key="tool.id", primary_key=True
    )


############## RECIPES #################

class RecipeBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    workpiece_id: int = Field(foreign_key="workpiece.id")
    machine_id: int = Field(foreign_key="machine.id")

class Recipe(RecipeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    active: bool = Field(default=True, nullable=False)
    tool_positions: List["ToolPosition"] = Relationship(back_populates="recipe")
    machine: "Machine" = Relationship(back_populates="recipes")
    workpiece: "Workpiece" = Relationship(back_populates="recipes")
    tools: List["Tool"] = Relationship(back_populates="recipes", link_model=RecipeTool)
    tool_lifes: List["ToolLife"] = Relationship(back_populates="recipe")
    change_overs: List["ChangeOver"] = Relationship(back_populates="recipe")

class RecipeCreate(RecipeBase):
    tool_positions: List["ToolPositionCreate"]

class RecipeUpdate(RecipeCreate):
    id: int
    active: bool
    

class ToolPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    name: str
    recipe_id: int = Field(foreign_key="recipe.id")
    recipe: "Recipe" = Relationship(back_populates="tool_positions")
    tool_id: int = Field(foreign_key="tool.id")
    tool: "Tool" = Relationship(back_populates="tool_positions")
    tool_settings: "ToolSettings" = Relationship(back_populates="tool_position")

class ToolPositionCreate(SQLModel):
    tool_settings: List["ToolSettingsCreate"]

class ToolPositionUpdate(ToolPositionCreate):
    id: int
    active: bool


class ToolSettingsBase(SQLModel):
    name: str

class ToolSettings(ToolSettingsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    tool_position_id: int = Field(foreign_key="toolposition.id")
    tool_position: "ToolPosition" = Relationship(back_populates="tool_settings")
    tool_id: int = Field(foreign_key="tool.id")
    tool: "Tool" = Relationship(back_populates="tool_settings")
    settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    expected_life: Optional[int] = Field(default=None, gt=0)

class ToolSettingsCreate(ToolSettingsBase):
    pass

class ToolSettingsUpdate(ToolSettingsBase):
    id: int
    active: bool


############# TOKEN ##################
class Token(SQLModel):
    access_token: str
    token_type: str


############# TOOLLIFES ################
class ChangeReasons(str, Enum):
    BROKEN = "Broken"
    BURR = "Burr"
    SPINDLE_LOAD = "Spindle Load"

class ToolLifeBase(SQLModel):
    pieces_machined: Optional[int] = None
    spindle_load: Optional[float] = None
    channel: Optional[int] = None
    reason: Optional[ChangeReasons] = None

class ToolLife(ToolLifeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now, nullable=False)
    tool_order_id: int = Field(foreign_key="toolorder.id")

    created_by: int = Field(foreign_key="user.id")
    machine_id: int = Field(foreign_key="machine.id")
    tool_id: int = Field(foreign_key="tool.id")
    recipe_id: int = Field(foreign_key="recipe.id")

    creator: "User" = Relationship(back_populates="tool_lifes")
    machine: "Machine" = Relationship(back_populates="tool_lifes")
    tool: "Tool" = Relationship(back_populates="tool_lifes")
    recipe: "Recipe" = Relationship(back_populates="tool_lifes")
    tool_order: "ToolOrder" = Relationship(back_populates="tool_lifes")

class ToolLifeCreate(ToolLifeBase):
    pass


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


############# TOOLS ################

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
    manufacturer: "Manufacturer" = Relationship(back_populates="tools")
    active: bool = Field(default=True, nullable=False)
    recipes: List["Recipe"] = Relationship(back_populates="tools", link_model=RecipeTool)
    tool_settings: List["ToolSettings"] = Relationship(back_populates="tool")
    tool_lifes: List["ToolLife"] = Relationship(back_populates="tool")
    tool_orders: List["ToolOrder"] = Relationship(back_populates="tool")
    tool_positions: List["ToolPosition"] = Relationship(back_populates="tool")
    tool_attributes: List["ToolAttribute"] = Relationship(back_populates="tool")
    
class ToolCreate(ToolBase):
    tool_attributes: List["ToolAttribute"] = []

class ToolUpdate(ToolCreate):
    id: int
    active: bool
    

class ToolAttribute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    unit: str
    tool_id: int = Field(foreign_key="tool.id")
    tool: "Tool" = Relationship(back_populates="tool_attributes")

class ToolAttributeCreate(SQLModel):
    name: str
    unit: str
    tool_id: int

############# USERS ################
class UserRole(str, Enum):
    OPERATOR = "Operator"
    SUPERVISOR = "Supervisor"
    MAINTENANCE = "Maintenance"
    ENGINEER = "Engineer"

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
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    tool_lifes: List["ToolLife"] = Relationship(back_populates="creator")
    performed_change_overs: List["ChangeOver"] = Relationship(back_populates="user")
    tool_orders: List["ToolOrder"] = Relationship(back_populates="user")

class UserRead(UserBase):
    id: int
    active: bool

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    id: int
    active: bool


################# WORKPIECE #####################
class WorkpieceBase(SQLModel):
    name: str
    description: str

class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    recipes: List["Recipe"] = Relationship(back_populates="workpiece")


class WorkPieceCreate(WorkpieceBase):
    pass