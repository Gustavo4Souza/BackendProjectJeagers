from datetime import datetime, timezone
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class HealthResponse(BaseModel):
    status: str
    version: str

class ReadingCreate(BaseModel):
    fermenter_id: str = Field(
        ...,
        validation_alias=AliasChoices("fermenter_id", "device_id"),
        min_length=1,
        max_length=100,
    )
    metric: str = Field(..., min_length=1, max_length=100)
    value: float = Field(..., allow_inf_nan=False)
    unit: Optional[str] = Field(default=None, max_length=30)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)

class ReadingResponse(ReadingCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
