from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    fermenter_id = Column(String(100), index=True, nullable=False)
    metric = Column(String(100), index=True, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

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
