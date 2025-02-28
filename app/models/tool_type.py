from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint
from enum import IntEnum

if TYPE_CHECKING:
    from .tool import Tool, ToolLife
    from .model_connections import ToolAttributeValue


class ToolTypeBase(SQLModel):
    name: str = Field(index=True, unique=True)
    perishable: bool = Field(default=True)


class ToolType(ToolTypeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    tool_settings: List['ToolSetting'] = Relationship(back_populates='tool_type', cascade_delete=True)
    tool_attributes: List['ToolAttribute'] = Relationship(back_populates='tool_type', cascade_delete=True)
    change_reasons: List['ChangeReason'] = Relationship(back_populates='tool_type', cascade_delete=True)
    tools: List['Tool'] = Relationship(back_populates='tool_type', cascade_delete=True)


class ToolTypeCreate(ToolTypeBase):
    change_reasons: List['ChangeReason'] = []
    tool_settings: List['ToolSetting'] = []
    tool_attributes: List['ToolAttribute'] = []


class ToolTypeUpdate(ToolTypeCreate):
    id: int
    active: bool


class ToolTypeRead(ToolTypeBase):
    id: int


class ToolAttributeBase(SQLModel):
    name: str
    unit: str
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')

class ToolAttribute(ToolAttributeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_type: ToolType = Relationship(back_populates='tool_attributes')
    attribute_values: List['ToolAttributeValue'] = Relationship(back_populates='tool_attribute', cascade_delete=True)

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)
    

class ToolAttributeCreate(ToolAttributeBase):
    pass

class ToolAttributeUpdate(ToolAttributeCreate):
    id: int

class ToolAttributeRead(SQLModel):
    name: str
    unit: str


class ToolSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    unit: str
    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: ToolType = Relationship(back_populates='tool_settings')

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)


class ToolSettingCreate(SQLModel):
    name: str
    unit: str
    tool_type_id: int


class ToolSettingUpdate(ToolSettingCreate):
    id: int


class ToolSettingRead(SQLModel):
    id: int
    name: str
    unit: str

class Sentiment(IntEnum):
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5

class ChangeReasonBase(SQLModel):
    name: str = Field(index=True)
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL)


class ChangeReason(ChangeReasonBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    tool_type_id: int = Field(foreign_key='tooltype.id', ondelete='CASCADE')
    tool_type: 'ToolType' = Relationship(back_populates='change_reasons')

    tool_lifes: List['ToolLife'] = Relationship(back_populates='change_reason', cascade_delete=False)

    __table_args__ = (UniqueConstraint('name', 'tool_type_id'),)


class ChangeReasonCreate(ChangeReasonBase):
    pass


class ChangeReasonUpdate(ChangeReasonCreate):
    id: int
    active: bool


class ChangeReasonRead(ChangeReasonBase):
    id: int

