from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, Column, JSON

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


from .log_device import LogDevice
from .tool_life import ToolLife
from .recipe import Recipe
from .change_over import ChangeOver
