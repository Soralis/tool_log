from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from enum import IntEnum

if TYPE_CHECKING:
    from .tool import ToolLife, ToolOrder
    from .change_over import ChangeOver


class UserRole(IntEnum):
    OPERATOR = 1
    SUPERVISOR = 2
    MAINTENANCE = 3
    ENGINEER = 4


class Token(SQLModel):
    access_token: str
    token_type: str


class UserBase(SQLModel):
    initials: str = Field(index=True, max_length=4, unique=True)
    name: str
    pin: str = Field(min_length=3, max_length=5)
    role: UserRole


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_login: Optional[datetime] = Field(default=None)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    tool_lifes: List['ToolLife'] = Relationship(back_populates='creator')
    performed_change_overs: List['ChangeOver'] = Relationship(back_populates='user')
    tool_orders: List['ToolOrder'] = Relationship(back_populates='user')


class UserCreate(UserBase):
    pass


class UserUpdate(UserCreate):
    id: int
    active: bool


class UserRead(SQLModel):
    id: int
    name: str
    initials: str
    role: UserRole
    active: bool
