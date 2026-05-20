from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String(30), default="viewer", nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_jti = Column(String(80), unique=True, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    role = Column(String(30), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Tank(Base):
    __tablename__ = "tanks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(100), nullable=True)
    temp_min = Column(Float, nullable=False)
    temp_max = Column(Float, nullable=False)
    status = Column(String(20), default="active", nullable=False)

    readings = relationship("Reading", back_populates="tank")
    alerts = relationship("Alert", back_populates="tank")


class Reading(Base):
    __tablename__ = "readings"

    id = Column(BigInteger, primary_key=True, index=True)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)

    tank = relationship("Tank", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    tank_id = Column(Integer, ForeignKey("tanks.id"), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    fired_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    tank = relationship("Tank", back_populates="alerts")
    acknowledged_by_user = relationship("User")


class YeastProfile(Base):
    __tablename__ = "yeast_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, index=True, nullable=False)
    strain = Column(String(120), nullable=True)
    attenuation_min = Column(Float, nullable=True)
    attenuation_max = Column(Float, nullable=True)
    temperature_min_c = Column(Float, nullable=True)
    temperature_max_c = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    batches = relationship("Batch", back_populates="yeast_profile")


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), index=True, nullable=False)
    style = Column(String(120), index=True, nullable=False)
    status = Column(String(30), index=True, default="planned", nullable=False)
    fermenter_id = Column(String(100), index=True, nullable=True)
    yeast_profile_id = Column(Integer, ForeignKey("yeast_profiles.id"), nullable=True)
    original_gravity = Column(Float, nullable=True)
    final_gravity = Column(Float, nullable=True)
    volume_liters = Column(Float, nullable=True)
    started_at = Column(DateTime(timezone=True), index=True, nullable=True)
    ended_at = Column(DateTime(timezone=True), index=True, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    yeast_profile = relationship("YeastProfile", back_populates="batches")
    events = relationship(
        "BatchEvent",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="BatchEvent.occurred_at",
    )


class BatchEvent(Base):
    __tablename__ = "batch_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), index=True, nullable=False)
    event_type = Column(String(80), index=True, nullable=False)
    description = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)
    occurred_at = Column(DateTime(timezone=True), index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    batch = relationship("Batch", back_populates="events")
