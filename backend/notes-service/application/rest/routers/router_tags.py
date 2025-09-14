from typing import List
from uuid import UUID

from application.converters.tag_converter import TagConverter
from application.rest.schemas.input.tag_input import TagCreate, TagUpdate
from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.tag_output import TagResponse
from domain.services.tag_service import (
    TagAlreadyExistsError,
    TagNotFoundError,
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
        # Get domain entities from domain service (with fresh session)
        tag_entities = await tag_service.get_all_tags(db)

        # Convert to response schemas using converter
        return TagConverter.entities_to_responses(tag_entities)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tags",
        ) from e


@router.post(
    path="/tags",
    description="Create a new tag using clean DDD architecture with business rule validation.",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": TagResponse,
            "description": "Tag created successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid tag data or tag already exists.",
            "content": {
                "application/json": {
                    "example": {"detail": "Tag with name 'work' already exists"}
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - tag creation failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to create tag."}}
            },
        },
    },
)
async def create_tag(
    tag_create: TagCreate,
    db: Session = Depends(get_db),
    tag_service: TagService = Depends(get_tag_service),
) -> TagResponse:
    """Create a new tag with domain business rule validation.

    Args:
        tag_create (TagCreate): Pydantic schema containing tag creation data.
        db (Session): Fresh database session for this request.
        tag_service (TagService): Domain service with injected repository.

    Returns:
        TagResponse: Created tag response schema.

    Raises:
        HTTPException: 400 if tag already exists or invalid data.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> tag_input = TagCreate(name="urgent")
        >>> created_tag = await create_tag(tag_input, db, tag_service)
        >>> print(created_tag.name)
        "urgent"
    """
    try:
        # Create tag using domain service (with fresh session)
        created_entity = await tag_service.create_tag(db, tag_create.name)

        # Convert result to response schema
        return TagConverter.entity_to_response(created_entity)
    except TagAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tag",
        ) from e


@router.get(
    path="/tags/{tag_id}",
    description="Retrieve a specific tag by its unique identifier.",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": TagResponse,
            "description": "Tag retrieved successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Tag not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Tag with ID 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid UUID format.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid UUID format: invalid-id"}
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - tag retrieval failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to retrieve tag."}}
            },
        },
    },
)
async def get_tag_by_id(
    tag_id: str,
    db: Session = Depends(get_db),
    tag_service: TagService = Depends(get_tag_service),
) -> TagResponse:
    """Get a specific tag by its unique identifier.

    Args:
        tag_id (str): String representation of the tag UUID.
        db (Session): Fresh database session for this request.
        tag_service (TagService): Domain service with injected repository.

    Returns:
        TagResponse: Tag response schema.

    Raises:
        HTTPException: 400 if UUID format is invalid.
        HTTPException: 404 if tag not found.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> tag = await get_tag_by_id("123e4567-e89b-12d3-a456-426614174000", db, tag_service)
        >>> print(tag.name)
        "work"
    """
    try:
        # Convert string to UUID and get domain entity
        tag_uuid = UUID(tag_id)
        tag_entity = await tag_service.get_tag_by_id(db, tag_uuid)

        # Convert to response schema
        return TagConverter.entity_to_response(tag_entity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {tag_id}",
        ) from e
    except TagNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tag",
        ) from e


@router.put(
    path="/tags/{tag_id}",
    description="Update an existing tag name with domain validation.",
    response_model=TagResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": TagResponse,
            "description": "Tag updated successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid UUID format or tag already exists.",
            "content": {
                "application/json": {
                    "example": {"detail": "Tag with name 'work' already exists"}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Tag not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Tag with ID 123e4567-e89b-12d3-a456-426614174000 not found"
                    }
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - tag update failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to update tag."}}
            },
        },
    },
)
async def update_tag(
    tag_id: str,
    tag_update: TagUpdate,
    db: Session = Depends(get_db),
    tag_service: TagService = Depends(get_tag_service),
) -> TagResponse:
    """Update an existing tag name.

    Args:
        tag_id (str): String representation of the tag UUID.
        tag_update (TagUpdate): Pydantic schema containing new tag name.
        db (Session): Fresh database session for this request.
        tag_service (TagService): Domain service with injected repository.

    Returns:
        TagResponse: Updated tag response schema.

    Raises:
        HTTPException: 400 if UUID format is invalid or tag name already exists.
        HTTPException: 404 if tag not found.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> tag_update = TagUpdate(name="important")
        >>> updated_tag = await update_tag("123e4567-e89b-12d3-a456-426614174000", tag_update, db, tag_service)
        >>> print(updated_tag.name)
        "important"
    """
    try:
        # Convert string to UUID and update using domain service
        tag_uuid = UUID(tag_id)
        updated_entity = await tag_service.update_tag(db, tag_uuid, tag_update.name)

        # Convert result to response schema
        return TagConverter.entity_to_response(updated_entity)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {tag_id}",
        ) from e
    except TagAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except TagNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tag",
        ) from e


@router.delete(
    path="/tags/{tag_id}",
    description="Delete a tag by its unique identifier.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Tag deleted successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid UUID format.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid UUID format: invalid-id"}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Tag not found.",
            "content": {"application/json": {"example": {"detail": "Tag not found"}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - tag deletion failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to delete tag."}}
            },
        },
    },
)
async def delete_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    tag_service: TagService = Depends(get_tag_service),
) -> None:
    """Delete a tag by its unique identifier.

    Args:
        tag_id (str): String representation of the tag UUID.
        db (Session): Fresh database session for this request.
        tag_service (TagService): Domain service with injected repository.

    Raises:
        HTTPException: 400 if UUID format is invalid.
        HTTPException: 404 if tag not found.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> await delete_tag("123e4567-e89b-12d3-a456-426614174000", db, tag_service)
        # Tag deleted successfully (204 No Content)
    """
    try:
        # Convert string to UUID and delete using domain service
        tag_uuid = UUID(tag_id)
        deleted = await tag_service.delete_tag(db, tag_uuid)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {tag_id}",
        ) from e
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag",
        ) from e
