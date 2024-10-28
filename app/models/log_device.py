from __future__ import annotations
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

################## LOG DEVICE ########################
class LogDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    active: bool = Field(default=True, nullable=False)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)

    machine_id: Optional[int] = Field(default=None, foreign_key="machine.id")
    machine: Optional["Machine"] = Relationship(back_populates="log_device")

class LogDeviceSetMachine(SQLModel):
    machine_id: int


from .machine import Machine