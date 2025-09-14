"""SQLAlchemy declarative base for all ORM models.

This module provides a shared declarative base that all ORM models inherit from.
Having a centralized base ensures metadata consistency across all models.

Usage:
    >>> from .base import Base
    >>>
    >>> class MyModel(Base):
    ...     __tablename__ = 'my_table'
    ...     # ... column definitions
"""

from sqlalchemy.ext.declarative import declarative_base

# Shared declarative base for all ORM models in the infrastructure layer
Base = declarative_base()
