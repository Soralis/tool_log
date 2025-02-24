from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship, DateTime
from datetime import datetime
from sqlalchemy import Column, Index

if TYPE_CHECKING:
    from .machine import Machine


class Heartbeat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    log_device_id: Optional[int] = Field(default=None, foreign_key="logdevice.id")
    log_device: Optional["LogDevice"] = Relationship(back_populates="heartbeats")
    
    __table_args__ = (Index("ix_heartbeat_log_device_id_timestamp", "log_device_id", "timestamp"),)


class LogDevice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    active: bool = Field(default=True, nullable=False)
    token: Optional[str] = Field(default=None, max_length=255)
    token_expiry: Optional[datetime] = Field(default=None)
    track_health: bool = Field(default=True, nullable=False)

    machines: List['Machine'] = Relationship(back_populates='log_device')
    heartbeats: List[Heartbeat] = Relationship(back_populates="log_device")


class LogDeviceSetMachine(SQLModel):
    machine_ids: List[int]
