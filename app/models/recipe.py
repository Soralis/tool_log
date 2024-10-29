from __future__ import annotations
from typing import Optional, List
from .model_connections import RecipeTool
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


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

class RecipeUpdate(RecipeBase):
    id: int
    active: bool


class ToolPositionBase(SQLModel):
    name: str
    tool_id: int = Field(foreign_key="tool.id")
    expected_life_id: int = Field(foreign_key="toollifeexpectancy.id")

class ToolPosition(ToolPositionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    recipe_id: int = Field(foreign_key="recipe.id")
    recipe: "Recipe" = Relationship(back_populates="tool_positions")
    tool: "Tool" = Relationship(back_populates="tool_positions")
    tool_settings: List[int] = Relationship(back_populates="tool_position")

class ToolPositionCreate(ToolPositionBase):
    tool_settings: List["ToolSettingsCreate"]

class ToolPositionUpdate(ToolPositionBase):
    id: int
    active: bool


class ToolSettingsBase(SQLModel):
    name: str
    values: str

class ToolSettings(ToolSettingsBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    date_created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    tool_position_id: int = Field(foreign_key="toolposition.id")
    tool_position: "ToolPosition" = Relationship(back_populates="tool_settings")

class ToolSettingsCreate(ToolSettingsBase):
    pass

class ToolSettingsUpdate(ToolSettingsBase):
    id: int
    active: bool


class ToolLifeExpectancy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date_created: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    tool_settings_id: int = Field(foreign_key="toolsettings.id")
    tool_settings: "ToolSettings" = Relationship(back_populates="expected_life_id")
    expected_life: int

class ToolLifeExpectancyCreate(SQLModel):
    expected_life: int



from .tool import Tool
from .tool_life import ToolLife
from .change_over import ChangeOver
from .machine import Machine
from .workpiece import Workpiece
