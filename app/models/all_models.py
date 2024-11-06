from typing import Optional, List, Dict
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from sqlalchemy import UniqueConstraint
from decimal import Decimal
from enum import IntEnum
from datetime import datetime


#################### CHANGE OVERS ########################
class ChangeOverBase(SQLModel):
    machine_id: int = Field(foreign_key='machine.id')
    recipe_id: int = Field(foreign_key='recipe.id')

class ChangeOver(ChangeOverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    performed_by: Optional[int] = Field(foreign_key='user.id')
    timestamps: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    machine: 'Machine' = Relationship(back_populates='change_overs')
    user: 'User' = Relationship(back_populates='performed_change_overs')
    recipe: 'Recipe' = Relationship(back_populates='change_overs')

class ChangeOverCreate(ChangeOverBase):
    pass

class ChangeOverUpdate(ChangeOverBase):
    id: int

class ChangeOverRead(SQLModel):
    id: int
    recipe: 'Recipe'
    machine: 'Machine'


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

    machines: List['Machine'] = Relationship(back_populates='log_device')

class LogDeviceSetMachine(SQLModel):
    machine_ids: List[int]


############# MACHINES ################
class MeasureableBase(SQLModel):
    name: str = Field(index=True)

class Measureable(MeasureableBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    machine_id: int = Field(foreign_key='machine.id', ondelete='CASCADE')
    machine: 'Machine' = Relationship(back_populates='measureables')

    __table_args__ = (UniqueConstraint('name', 'machine_id'),)

class MeasureableCreate(MeasureableBase):
    pass

class MeasureableUpdate(MeasureableCreate):
    id: int
    active: bool

class MeasureableRead(MeasureableBase):
    id: int
    active: bool
    machine: 'Machine'


class MachineBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    model: Optional[str] = Field(default=None)
    manufacturer: Optional[str] = Field(default=None)
    channels: int = Field(gt=0)

class Machine(MachineBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    log_device_id: Optional[int] = Field(default=None, foreign_key='logdevice.id')
    log_device: Optional['LogDevice'] = Relationship(back_populates='machines')

    measureables: List[Measureable] = Relationship(back_populates='machine')
    tool_lifes: List['ToolLife'] = Relationship(back_populates='machine')
    recipes: List['Recipe'] = Relationship(back_populates='machine', sa_relationship_kwargs={"foreign_keys": "[Recipe.machine_id]"})
    change_overs: List['ChangeOver'] = Relationship(back_populates='machine', cascade_delete=True)

    current_recipe_id: Optional[int] = Field(default=None, foreign_key='recipe.id')
    current_recipe: 'Recipe' = Relationship(back_populates='machine', sa_relationship_kwargs={"foreign_keys": "[Machine.current_recipe_id]"})

class MachineCreate(MachineBase):
    measureables: List[Measureable] = []

class MachineUpdate(MachineCreate):
    id: int
    active: bool

class MachineRead(SQLModel):
    id: int
    name: str
    active: bool
    current_recipe: 'Recipe'


###### MANUFACTURER #######
class ManufacturerBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class Manufacturer(ManufacturerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    tools: List['Tool'] = Relationship(back_populates='manufacturer', cascade_delete=True)

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerUpdate(ManufacturerCreate):
    id: int

class ManufacturerRead(SQLModel):
    id: int
    name: str


############# CONNECTION TABLES ################

class RecipeTool(SQLModel, table=True):
    recipe_id: Optional[int] = Field(
        default=None, foreign_key='recipe.id', primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key='tool.id', primary_key=True
    )


############## RECIPES #################
class RecipeBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    workpiece_id: int = Field(foreign_key='workpiece.id')
    machine_id: int = Field(foreign_key='machine.id')

    __table_args__ = (UniqueConstraint('name', 'workpiece_id', 'machine_id'),)

class Recipe(RecipeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    active: bool = Field(default=True, nullable=False)
    tool_positions: List['ToolPosition'] = Relationship(back_populates='recipe', cascade_delete=True)
    machine: 'Machine' = Relationship(back_populates='recipes', sa_relationship_kwargs={"foreign_keys": "[Recipe.machine_id]"})
    workpiece: 'Workpiece' = Relationship(back_populates='recipes')
    tools: List['Tool'] = Relationship(back_populates='recipes', link_model=RecipeTool)
    tool_lifes: List['ToolLife'] = Relationship(back_populates='recipe')
    change_overs: List['ChangeOver'] = Relationship(back_populates='recipe')

class RecipeCreate(RecipeBase):
    pass

class RecipeUpdate(RecipeCreate):
    id: int
    active: bool
    tool_positions: List['ToolPosition']

class RecipeRead(SQLModel):
    id: int
    name: str
    machine: 'Machine'
    workpiece: 'Workpiece'
    active: bool

################# TOOL POSITION ########################
class ToolPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    name: str
    recipe_id: int = Field(foreign_key='recipe.id', ondelete='CASCADE')
    recipe: 'Recipe' = Relationship(back_populates='tool_positions')
    tool_id: Optional[int] = Field(foreign_key='tool.id')
    tool: 'Tool' = Relationship(back_populates='tool_positions')
    tool_lifes: List['ToolLife'] = Relationship(back_populates='tool_position')
    # tool_settings: List['ToolSettings'] = Relationship(back_populates='tool_position')
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    expected_life: Optional[int] = Field(default=None, gt=0)

    __table_args__ = (UniqueConstraint('name', 'recipe_id'),)

class ToolPositionCreate(SQLModel):
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))

class ToolPositionUpdate(ToolPositionCreate):
    id: int
    active: bool

class ToolPositionRead(SQLModel):
    id: int
    name: str
    active: bool
    recipe: 'Recipe'
    tool: 'Tool'
    machine: 'Machine'


############### TOOL SETTING ################
# class ToolSettingsBase(SQLModel):
#     name: str

# class ToolSettings(ToolSettingsBase, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     active: bool = Field(default=True, nullable=False, index=True)
#     tool_position_id: int = Field(foreign_key='toolposition.id', ondelete='CASCADE')
#     tool_position: 'ToolPosition' = Relationship(back_populates='tool_settings')
#     tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
#     tool: 'Tool' = Relationship(back_populates='tool_settings')
#     settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
#     expected_life: Optional[int] = Field(default=None, gt=0)

# class ToolSettingsCreate(ToolSettingsBase):
#     pass

# class ToolSettingsUpdate(ToolSettingsCreate):
#     id: int
#     active: bool


############# TOKEN ##################
class Token(SQLModel):
    access_token: str
    token_type: str


############# TOOLLIFES ################
class ToolLifeBase(SQLModel):
    reached_life: int
    machine_channel: int

class ToolLife(ToolLifeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.now, nullable=False)

    tool_order_id: int = Field(foreign_key='toolorder.id')
    created_by: int = Field(foreign_key='user.id')
    machine_id: int = Field(foreign_key='machine.id')
    tool_id: int = Field(foreign_key='tool.id')
    recipe_id: int = Field(foreign_key='recipe.id')
    change_reason_id: int = Field(foreign_key='changereason.id')
    tool_position_id: int = Field(foreign_key='toolposition.id')

    creator: 'User' = Relationship(back_populates='tool_lifes')
    machine: 'Machine' = Relationship(back_populates='tool_lifes')
    tool: 'Tool' = Relationship(back_populates='tool_lifes')
    recipe: 'Recipe' = Relationship(back_populates='tool_lifes')
    tool_order: 'ToolOrder' = Relationship(back_populates='tool_lifes')
    change_reason: 'ChangeReason' = Relationship(back_populates='tool_lifes')
    tool_position: 'ToolPosition' = Relationship(back_populates='tool_lifes')

class ToolLifeCreate(ToolLifeBase):
    pass

class ToolLifeUpdate(ToolLifeCreate):
    id: int

class ToolLifeRead(SQLModel):
    id: int
    name: str
    tool: 'Tool'


################ TOOL ORDER ######################

class ToolOrderBase(SQLModel):
    tool_id: int = Field(foreign_key='tool.id', ondelete='CASCADE')
    quantity: int
    remaining_quantity: int
    batch_number: Optional[str] = Field(default=None)
    gross_price: Decimal = Field(max_digits=10, decimal_places=2)
    

class ToolOrder(ToolOrderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool: 'Tool' = Relationship(back_populates='tool_orders')
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
    tool: 'Tool'


############# TOOL TYPE ##############
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

class ToolTypeRead:
    id: int
    name: str
    active: bool
    perishable: bool


############# TOOLS ################
class ChangeReasonBase(SQLModel):
    name: str = Field(index=True)

class ChangeReason(ChangeReasonBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: 'ToolType' = Relationship(back_populates='change_reasons')

    tool_lifes: List['ToolLife'] = Relationship(back_populates='change_reason')

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)

class ChangeReasonCreate(ChangeReasonBase):
    pass

class ChangeReasonUpdate(ChangeReasonCreate):
    id: int
    active: bool

class ChangeReasonRead(SQLModel):
    id: int
    name: str
    active: bool
    tool_type: 'ToolType'


class ToolBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    manufacturer_id: int = Field(foreign_key='manufacturer.id', ondelete='CASCADE')

    __table_args__ = (UniqueConstraint('name', 'tool_type_id', 'manufacturer_id'),)


class Tool(ToolBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    manufacturer: 'Manufacturer' = Relationship(back_populates='tools')
    tool_type: 'ToolType' = Relationship(back_populates='tools')
    active: bool = Field(default=True, nullable=False)
    recipes: List['Recipe'] = Relationship(back_populates='tools', link_model=RecipeTool)
    # tool_settings: List['ToolSettings'] = Relationship(back_populates='tool')
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
    tool_type: 'ToolType'
    active: bool
    

class ToolAttribute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    unit: str
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: 'ToolType' = Relationship(back_populates='tool_attributes')

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
    tool_type: 'ToolType'


############# USERS ################
class UserRole(IntEnum):
    OPERATOR = 1
    SUPERVISOR = 2
    MAINTENANCE = 3
    ENGINEER = 4

class UserBase(SQLModel):
    initials: str = Field(index=True, max_length=4, unique=True)
    name: str
    pin: str = Field(min_length=3, max_length=5)
    role: UserRole

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_login: Optional[datetime] = Field(default=None)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    tool_lifes: List['ToolLife'] = Relationship(back_populates='creator')
    performed_change_overs: List['ChangeOver'] = Relationship(back_populates='user')
    tool_orders: List['ToolOrder'] = Relationship(back_populates='user')

class UserCreate(UserBase):
    pass

class UserUpdate(UserCreate):
    id: int
    active: bool

class UserRead(SQLModel):
    id: int
    name: str
    initials: str
    role: UserRole
    active: bool


################# WORKPIECE #####################
class WorkpieceBase(SQLModel):
    name: str = Field(unique=True)
    description: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None

class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    recipes: List['Recipe'] = Relationship(back_populates='workpiece')


class WorkpieceCreate(WorkpieceBase):
    pass

class WorkpieceUpdate(WorkpieceCreate):
    id: int
    active: bool

class WorkPieceRead(SQLModel):
    id: int
    name: str
    active: bool