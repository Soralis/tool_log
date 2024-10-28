from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship


###### MANUFACTURER #######

class ManufacturerBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None

class Manufacturer(ManufacturerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tools: List["Tool"] = Relationship(back_populates="manufacturer")

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerUpdate(ManufacturerBase):
    id: int


from .tool import Tool