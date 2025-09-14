"""
This module contains the FastAPI router for tags operations.
"""

from typing import List

from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.tag_output import TagResponse
from domain.services.tag_service import (
    TagService,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from utils.dependencies import get_db, get_tag_service

router = APIRouter()


@router.get(
    path="/tags",
    description="Retrieve all available tags using clean DDD architecture.",
    response_model=List[TagResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": List[TagResponse],
            "description": "List of all available tags.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - database connection failed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Database connection error."}
                }
            },
        },
    },
)
async def get_tags(
    db: Session = Depends(get_db), tag_service: TagService = Depends(get_tag_service)
) -> List[TagResponse]:
    """Get all available tags using clean DDD architecture.

    This endpoint demonstrates clean DDD architecture:
    1. Router receives request and fresh DB session
    2. Router delegates to Domain Service, passing session
    3. Domain Service applies business rules and delegates to Repository
    4. Repository handles data persistence using SQLAlchemy with session
    5. Results flow back through layers with conversions (Entity -> Pydantic)

    Args:
        db (Session): Fresh database session for this request.
        tag_service (TagService): Domain service with injected repository.

    Returns:
        List[TagResponse]: List of all tag response schemas.

    Raises:
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> tags = await get_tags(db, tag_service)
        >>> print([tag.name for tag in tags])
        ['personal', 'work']
    """
    try:
        tag_entities = await tag_service.get_all_tags(db)
        return [TagResponse.from_entity(tag) for tag in tag_entities]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tags",
        ) from e
