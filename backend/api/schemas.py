from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

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

BatchStatus = Literal["planned", "active", "completed", "cancelled"]

class YeastProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    strain: Optional[str] = Field(default=None, max_length=120)
    attenuation_min: Optional[float] = Field(default=None, ge=0, le=100)
    attenuation_max: Optional[float] = Field(default=None, ge=0, le=100)
    temperature_min_c: Optional[float] = Field(default=None, ge=-20, le=60)
    temperature_max_c: Optional[float] = Field(default=None, ge=-20, le=60)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.attenuation_min is not None
            and self.attenuation_max is not None
            and self.attenuation_min > self.attenuation_max
        ):
            raise ValueError("attenuation_min must be less than or equal to attenuation_max")

        if (
            self.temperature_min_c is not None
            and self.temperature_max_c is not None
            and self.temperature_min_c > self.temperature_max_c
        ):
            raise ValueError("temperature_min_c must be less than or equal to temperature_max_c")

        return self

class YeastProfileCreate(YeastProfileBase):
    pass

class YeastProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    strain: Optional[str] = Field(default=None, max_length=120)
    attenuation_min: Optional[float] = Field(default=None, ge=0, le=100)
    attenuation_max: Optional[float] = Field(default=None, ge=0, le=100)
    temperature_min_c: Optional[float] = Field(default=None, ge=-20, le=60)
    temperature_max_c: Optional[float] = Field(default=None, ge=-20, le=60)
    notes: Optional[str] = None

class YeastProfileResponse(YeastProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BatchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    style: str = Field(..., min_length=1, max_length=120)
    status: BatchStatus = "planned"
    fermenter_id: Optional[str] = Field(default=None, max_length=100)
    yeast_profile_id: Optional[int] = Field(default=None, gt=0)
    original_gravity: Optional[float] = Field(default=None, ge=0.99, le=1.2)
    final_gravity: Optional[float] = Field(default=None, ge=0.99, le=1.2)
    volume_liters: Optional[float] = Field(default=None, gt=0)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_batch(self):
        if self.ended_at and self.started_at and self.ended_at < self.started_at:
            raise ValueError("ended_at must be after started_at")

        if (
            self.original_gravity is not None
            and self.final_gravity is not None
            and self.final_gravity > self.original_gravity
        ):
            raise ValueError("final_gravity must be less than or equal to original_gravity")

        return self

class BatchCreate(BatchBase):
    pass

class BatchUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    style: Optional[str] = Field(default=None, min_length=1, max_length=120)
    status: Optional[BatchStatus] = None
    fermenter_id: Optional[str] = Field(default=None, max_length=100)
    yeast_profile_id: Optional[int] = Field(default=None, gt=0)
    original_gravity: Optional[float] = Field(default=None, ge=0.99, le=1.2)
    final_gravity: Optional[float] = Field(default=None, ge=0.99, le=1.2)
    volume_liters: Optional[float] = Field(default=None, gt=0)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None

class BatchEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=80)
    description: str = Field(..., min_length=1)
    value: Optional[float] = Field(default=None, allow_inf_nan=False)
    unit: Optional[str] = Field(default=None, max_length=30)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BatchEventResponse(BatchEventCreate):
    id: int
    batch_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BatchResponse(BatchBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BatchDetailResponse(BatchResponse):
    abv: Optional[float] = None
    apparent_attenuation: Optional[float] = None
    yeast_profile: Optional[YeastProfileResponse] = None
    events: list[BatchEventResponse] = Field(default_factory=list)
