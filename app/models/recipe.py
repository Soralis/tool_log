from typing import Optional, List, Dict, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from sqlalchemy import UniqueConstraint, CheckConstraint, Index, text
from datetime import datetime
from .model_connections import RecipeTool


if TYPE_CHECKING:
    from .machine import Machine
    from .workpiece import Workpiece
    from .tool import Tool, ToolLife
    from .change_over import ChangeOver


class RecipeBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    workpiece_id: int = Field(foreign_key='workpiece.id')
    machine_id: int = Field(foreign_key='machine.id')

    __table_args__ = (UniqueConstraint('name', 'workpiece_id', 'machine_id'),)


class Recipe(RecipeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
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


class ToolPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    selected: bool = Field(default=True, nullable=False)
    name: str
    recipe_id: int = Field(foreign_key='recipe.id', ondelete='CASCADE')
    recipe: Recipe = Relationship(back_populates='tool_positions')
    tool_id: Optional[int] = Field(foreign_key='tool.id')
    tool: 'Tool' = Relationship(back_populates='tool_positions')
    tool_lifes: List['ToolLife'] = Relationship(back_populates='tool_position')
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    expected_life: Optional[int] = Field(default=None, gt=0)
    
    __table_args__ = (
        Index('uq_name_recipe_selected', 'name', 'recipe_id', unique=True,
              postgresql_where=text('selected = true')),
        CheckConstraint('(selected = true)::int <= 1', name='check_single_selected')
    )


class ToolPositionCreate(SQLModel):
    selected: bool
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))


class ToolPositionUpdate(ToolPositionCreate):
    id: int

class ToolPositionRead(SQLModel):
    id: int
    name: str
    selected: bool
    recipe: Recipe
    tool: 'Tool'
    machine: 'Machine'
    tool_settings: Dict = Field(default_factory=dict, sa_column=Column(JSON))
