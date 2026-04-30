from sqlalchemy import Column, DateTime, Float, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), index=True, nullable=False)
    metric = Column(String(100), index=True, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
