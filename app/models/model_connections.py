from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
if TYPE_CHECKING:
    from .tool import Tool
    from .tool_type import ToolAttribute


class RecipeTool(SQLModel, table=True):
    recipe_id: Optional[int] = Field(
        default=None, foreign_key='recipe.id', primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key='tool.id', primary_key=True
    )

class ToolAttributeValue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", nullable=False)
    tool_attribute_id: int = Field(foreign_key="toolattribute.id", nullable=False)
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