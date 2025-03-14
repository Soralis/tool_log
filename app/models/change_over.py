from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime


if TYPE_CHECKING:
    from .machine import Machine
    from .user import User
    from .recipe import Recipe


class ChangeOverBase(SQLModel):
    machine_id: int = Field(foreign_key='machine.id', ondelete='CASCADE')
    recipe_id: int = Field(foreign_key='recipe.id', ondelete='CASCADE')


class ChangeOver(ChangeOverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    performed_by: Optional[int] = Field(foreign_key='user.id', ondelete='SET NULL')
    timestamps: datetime = Field(default_factory=datetime.now, nullable=False, index=True)
    machine: 'Machine' = Relationship(back_populates='change_overs')
    user: 'User' = Relationship(back_populates='performed_change_overs')
    recipe: 'Recipe' = Relationship(back_populates='change_overs')


class ChangeOverCreate(ChangeOverBase):
    pass


class ChangeOverUpdate(ChangeOverBase):
    id: int


class ChangeOverRead(SQLModel):
    id: int
    recipe: 'Recipe'
    machine: 'Machine'
