from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, time
from enum import IntEnum


if TYPE_CHECKING:
    from .tool import ToolLife, ToolOrder, Note, ToolConsumption
    from .change_over import ChangeOver
    from .workpiece import OrderCompletion


class UserRole(IntEnum):
    OPERATOR = 1
    SUPERVISOR = 2
    MAINTENANCE = 3
    ENGINEER = 4

class PaymentType(IntEnum):
    HOURLY = 1
    SALARY = 2


class Token(SQLModel):
    access_token: str
    token_type: str


class UserBase(SQLModel):
    initials: str = Field(index=True, max_length=4, unique=True)
    name: str
    number: Optional[str]
    pin: str = Field(min_length=3, max_length=5)
    role: UserRole
    payment_type: PaymentType
    shift_id: Optional[int] = Field(foreign_key='shift.id', ondelete='CASCADE')


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    last_login: Optional[datetime] = Field(default=None)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    tool_lifes: List['ToolLife'] = Relationship(back_populates='creator')
    performed_change_overs: List['ChangeOver'] = Relationship(back_populates='user')
    tool_orders: List['ToolOrder'] = Relationship(back_populates='user')
    notes: List['Note'] = Relationship(back_populates='user')
    order_completions: List['OrderCompletion'] = Relationship(back_populates='user')
    tool_consumptions: List['ToolConsumption'] = Relationship(back_populates='user')
    shift: Optional['Shift'] = Relationship(back_populates='users')


class UserCreate(UserBase):
    pass


class UserUpdate(UserCreate):
    id: int
    active: bool


class UserRead(SQLModel):
    id: int
    name: str
    number: str
    initials: str
    role: UserRole
    active: bool


class Shift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    number: int = Field(unique=True)
    start_time: datetime
    end_time: datetime

    users: List['User'] = Relationship(back_populates="shift")

class ShiftCreate(SQLModel):
    name: str
    number: int
    start_time: time
    end_time: time

class ShiftUpdate(ShiftCreate):
    id: int

class ShiftRead(ShiftUpdate):
    pass

class ShiftFilter(ShiftRead):
    pass


# class Role(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str = Field(unique=True)

#     users: List['User'] = Relationship(back_populates="role")

#     # Rights
#     see_dashboard: bool = Field(default=True)


