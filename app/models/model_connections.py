from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
if TYPE_CHECKING:
    from .tool import Tool
    from .tool_type import ToolAttribute


class WorkpieceGroupMembership(SQLModel, table=True):
    workpiece_id: int = Field(foreign_key='workpiece.id', primary_key=True, ondelete='CASCADE')
    group_id: int = Field(foreign_key='workpiecegroup.id', primary_key=True, ondelete='CASCADE')


class WorkpieceLine(SQLModel, table=True):
    workpiece_id: int = Field(foreign_key='workpiece.id', primary_key=True, ondelete='CASCADE')
    line_id: int = Field(foreign_key='line.id', primary_key=True, ondelete='CASCADE')


class WorkpieceGroupLine(SQLModel, table=True):
    group_id: int = Field(foreign_key='workpiecegroup.id', primary_key=True, ondelete='CASCADE')
    line_id: int = Field(foreign_key='line.id', primary_key=True, ondelete='CASCADE')


class RecipeTool(SQLModel, table=True):
    recipe_id: Optional[int] = Field(
        default=None, foreign_key='recipe.id', primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key='tool.id', primary_key=True
    )

class ToolAttributeValue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", nullable=False, ondelete="CASCADE")
    tool_attribute_id: int = Field(foreign_key="toolattribute.id", nullable=False, ondelete="CASCADE")
    value: str  # Store value as a string; convert as needed

    tool: "Tool" = Relationship(back_populates="tool_attributes")
    tool_attribute: "ToolAttribute" = Relationship(back_populates="attribute_values")

class ToolAttributeValueCreate(SQLModel):
    tool_id: int
    tool_attribute_id: int
    value: str

class ToolAttributeValueUpdate(ToolAttributeValueCreate):
    id: int

class ToolAttributeValueRead(ToolAttributeValueCreate):
    id: int
    value: str
