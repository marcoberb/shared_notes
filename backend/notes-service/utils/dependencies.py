"""Database and user management dependencies for the Notes Service.

This module provides dependency injection functions for FastAPI,
including database session management and user authentication utilities.

Functions:
    - get_db: Database session factory with automatic cleanup
    - get_current_user_id: Extract user ID from request headers

Architecture:
    These utilities are shared across all layers and provide clean dependency
    injection for database access and user management operations.
"""

import logging
from typing import Generator

from domain.services.tag_service import TagService
from fastapi import HTTPException, Request
from infrastructure.repositories.sqlalchemy_tag_repository import (
    SqlAlchemyTagRepository,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL, LOG_LEVEL

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup.

    Yields:
        Session: SQLAlchemy database session that automatically closes after use.

    Example:
        >>> with get_db() as db:
        ...     notes = db.query(Note).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(request: Request) -> str:
    """Extract user ID from request headers.

    Args:
        request (Request): FastAPI request object containing headers.

    Returns:
        str: User ID extracted from X-User-ID header.

    Raises:
        HTTPException: 401 if X-User-ID header is missing.

    Example:
        >>> user_id = get_current_user_id(request)
        >>> print(user_id)
        "keycloak-user-uuid"
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in headers")
    return user_id


def get_tag_service() -> TagService:
    """Create and configure the tag service with repository dependency.

    This factory function creates the domain service with its repository dependency.
    The session is injected per-request in each endpoint method.

    Returns:
        TagService: Configured domain service ready for use.
    """
    # Infrastructure layer: SQLAlchemy repository (no session stored)
    tag_repository = SqlAlchemyTagRepository()

    # Domain layer: Domain service with business logic
    return TagService(tag_repository)
