from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .recipe import Recipe


class WorkpieceBase(SQLModel):
    name: str = Field(unique=True)
    description: Optional[str] = None
    material: Optional[str] = None
    dimensions: Optional[str] = None


class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    recipes: List['Recipe'] = Relationship(back_populates='workpiece')


class WorkpieceCreate(WorkpieceBase):
    pass


class WorkpieceUpdate(WorkpieceCreate):
    id: int
    active: bool


class WorkPieceRead(SQLModel):
    id: int
    name: str
    active: bool
