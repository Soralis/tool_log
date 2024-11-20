from typing import Optional
from sqlmodel import Field, SQLModel
from decimal import Decimal
from datetime import datetime


class RequestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    method: str
    endpoint: str
    status_code: int
    response_time: Decimal = Field(max_digits=10, decimal_places=3)  # in seconds
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ServiceMetrics(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    total_requests: int = Field(default=0)
    total_errors: int = Field(default=0)
    avg_response_time: Decimal = Field(default=0, max_digits=10, decimal_places=3)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
