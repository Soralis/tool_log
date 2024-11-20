from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .tool import Tool


class ManufacturerBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None


class Manufacturer(ManufacturerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    tools: List['Tool'] = Relationship(back_populates='manufacturer', cascade_delete=True)


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerUpdate(ManufacturerCreate):
    id: int


class ManufacturerRead(SQLModel):
    id: int
    name: str
