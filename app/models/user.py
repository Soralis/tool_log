from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from enum import Enum

############# USERS ################
class UserRole(str, Enum):
    OPERATOR = "Operator"
    SUPERVISOR = "Supervisor"
    MAINTENANCE = "Maintenance"
    ENGINEER = "Engineer"

class UserBase(SQLModel):
    initials: str = Field(index=True, max_length=4)
    name: str
    pin: str = Field(max_length=4)
    role: UserRole

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_login: Optional[datetime] = Field(default=None)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    tool_lifes: List["ToolLife"] = Relationship(back_populates="creator")
    performed_change_overs: List["ChangeOver"] = Relationship(back_populates="user")
    tool_orders: List["ToolOrder"] = Relationship(back_populates="user")

class UserRead(UserBase):
    id: int
    active: bool

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    id: int
    active: bool


from .tool_life import ToolLife
from .change_over import ChangeOver
from .tool_order import ToolOrder