from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

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
    recipes: List["Recipe"] = Relationship(back_populates="tools", link_model="RecipeTool")
    tool_lifes: List["ToolLife"] = Relationship(back_populates="tool")
    tool_orders: List["ToolOrder"] = Relationship(back_populates="tool")
    
class ToolCreate(ToolBase):
    pass

class ToolUpdate(ToolBase):
    pass



from .manufacturer import Manufacturer
from .recipe import Recipe
from .model_connections import RecipeTool
from .tool_life import ToolLife
from .tool_order import ToolOrder