from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

################# WORKPIECE #####################
class WorkpieceBase(SQLModel):
    name: str
    description: str

class Workpiece(WorkpieceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    recipes: List["Recipe"] = Relationship(back_populates="workpiece")


class WorkPieceCreate(WorkpieceBase):
    pass

from .recipe import Recipe