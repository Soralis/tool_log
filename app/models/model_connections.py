from typing import Optional
from sqlmodel import Field, SQLModel


class RecipeTool(SQLModel, table=True):
    recipe_id: Optional[int] = Field(
        default=None, foreign_key='recipe.id', primary_key=True
    )
    tool_id: Optional[int] = Field(
        default=None, foreign_key='tool.id', primary_key=True
    )