from __future__ import annotations
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from enum import Enum


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

class ToolLife(SQLModel, table=True):
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


from .user import User
from .machine import Machine
from .tool import Tool
from .recipe import Recipe
from .tool_order import ToolOrder