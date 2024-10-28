from __future__ import annotations
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


#################### CHANGE OVERS ########################

class ChangeOverBase(SQLModel):
    machine_id: int = Field(foreign_key="machine.id")
    recipe_id: int = Field(foreign_key="recipe.id")

class ChangeOver(ChangeOverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    performed_by: int = Field(foreign_key="user.id")
    timestamps: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    machine: "Machine" = Relationship(back_populates="change_overs")
    user: "User" = Relationship(back_populates="performed_change_overs")
    recipe: "Recipe" = Relationship(back_populates="change_overs")

class ChangeOverCreate(ChangeOverBase):
    pass


from .user import User
from .machine import Machine
from .recipe import Recipe