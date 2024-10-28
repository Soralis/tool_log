from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


############## RECIPES #################

class RecipeBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    machine_id: int = Field(foreign_key="machine.id")

class Recipe(RecipeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    tools: List["Tool"] = Relationship(back_populates="recipes", link_model="RecipeTool")
    tool_lifes: List["ToolLife"] = Relationship(back_populates="recipe")
    change_overs: List["ChangeOver"] = Relationship(back_populates="recipe")
    machine: "Machine" = Relationship(back_populates="recipes")

class RecipeCreate(RecipeBase):
    pass

class RecipeUpdate(RecipeBase):
    id: int


from .tool import Tool
from .tool_life import ToolLife
from .change_over import ChangeOver
from .machine import Machine
