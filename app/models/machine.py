from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint

if TYPE_CHECKING:
    from .log_device import LogDevice
    from .tool_life import ToolLife
    from .recipe import Recipe
    from .change_over import ChangeOver


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
