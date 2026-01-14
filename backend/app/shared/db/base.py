"""
Base class for all SQLAlchemy ORM models.
All table models should inherit from Base.
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all ORM models.
    This is used by Alembic to detect schema changes.
    """
    pass


class TimestampMixin:
    """
    Mixin to add created_at and updated_at columns to any model.
    Usage: class MyModel(Base, TimestampMixin):
    """
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        onupdate=func.now()
    )
