from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

UserRole = Literal["admin", "operador", "viewer"]

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = "viewer"

class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class LogoutResponse(BaseModel):
    msg: str

class HealthResponse(BaseModel):
    status: str
    version: str

TankStatus = Literal["normal", "warning", "alert", "offline"]

class TankResponse(BaseModel):
    id: int
    name: str
    location: Optional[str]
    temp_min: float
    temp_max: float
    status: str
    current_temperature: Optional[float] = None
    last_reading_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    id: int
    tank_id: int
    temperature: float
    fired_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AlertDetailResponse(AlertResponse):
    tank_name: str = ""
    alert_type: Optional[str] = None  # 'above_max' | 'below_min'

class TankStatusResponse(BaseModel):
    tank_id: int
    name: str
    current_temperature: Optional[float]
    last_reading_at: Optional[datetime]
    temp_min: float
    temp_max: float
    tank_status: TankStatus
    active_alerts: list[AlertResponse] = Field(default_factory=list)

class TankConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None

    @model_validator(mode="after")
    def validate_temp_range(self):
        if self.temp_min is not None and self.temp_max is not None:
            if self.temp_min >= self.temp_max:
                raise ValueError("temp_min deve ser menor que temp_max")
        return self

class ReadingCreate(BaseModel):
    tank_id: int = Field(..., gt=0)
    temperature: float = Field(..., allow_inf_nan=False)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReadingResponse(BaseModel):
    id: int
    tank_id: int
    temperature: float
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)

ControlMode = Literal["cooling", "heating", "idle"]


class TankControlSet(BaseModel):
    setpoint: float = Field(..., ge=-20, le=60)


class TankControlResponse(BaseModel):
    tank_id: int
    setpoint: float
    mode: ControlMode
    updated_at: datetime
    updated_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ETAResponse(BaseModel):
    eta_minutes: Optional[float]
    rate_per_minute: Optional[float]
    current_temp: Optional[float]
    setpoint: float
    sufficient_data: bool


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

