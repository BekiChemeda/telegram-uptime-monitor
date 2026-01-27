import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, DateTime,
    BigInteger, Boolean, Integer, ForeignKey, Uuid
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=True)

    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Global settings
    is_notification_enabled = Column(Boolean, default=True, nullable=False)

    monitors = relationship(
        "Monitor",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)

    owner_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    url = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)

    interval_seconds = Column(Integer, default=60, nullable=False)
    timeout_seconds = Column(Integer, default=10, nullable=False)

    expected_status = Column(Integer, default=200, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_notification_enabled = Column(Boolean, default=True, nullable=False)
    last_status = Column(Boolean, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_checked = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="monitors")
    checks = relationship(
        "CheckLog",
        back_populates="monitor",
        cascade="all, delete-orphan"
    )


class CheckLog(Base):
    __tablename__ = "checks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)

    monitor_id = Column(
        Uuid,
        ForeignKey("monitors.id", ondelete="CASCADE"),
        index=True
    )

    status_code = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)

    is_up = Column(Boolean, nullable=False)

    error_message = Column(String, nullable=True)

    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    monitor = relationship("Monitor", back_populates="checks")
