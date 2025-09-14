"""Search router for the shared notes application.

This module contains the FastAPI router for search operations.
"""

import logging
from typing import Annotated, Union

from application.rest.schemas.input.search_input import SearchNotesRequest
from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.search_output import SearchResultResponse
from domain.entities.search import SearchCriteria
from domain.services.search_service import SearchError, SearchService
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from utils.dependencies import get_current_user_id, get_db, get_search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    path="/search",
    description="Search notes using full-text search and tag filtering across different sections.",
    response_model=SearchResultResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": SearchResultResponse,
            "description": "Search results with notes, pagination, and search metadata.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid request parameters.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid section parameter."}
                }
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error.",
            "content": {
                "application/json": {"example": {"detail": "Search operation failed."}}
            },
        },
    },
)
async def search_notes(
    request: Request,
    q: Annotated[str, Query(description="Search query string")] = "",
    tags: Annotated[
        Union[str, None], Query(description="Comma-separated tag UUIDs")
    ] = None,
    section: Annotated[
        str,
        Query(description="Section to search: my-notes, shared-by-me, shared-with-me"),
    ] = "my-notes",
    page: Annotated[int, Query(ge=1, description="Page number (1-based)")] = 1,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of results per page")
    ] = 15,
    search_service: SearchService = Depends(get_search_service),
    db: Session = Depends(get_db),
) -> SearchResultResponse:
    """Search notes with optional text query and tag filters.

    Args:
        request: FastAPI request object
        q: Search query string
        tags: Comma-separated tag UUIDs for filtering
        section: Section to search in
        page: Page number for pagination
        limit: Number of results per page
        search_service: Search service dependency
        db: Database session dependency

    Returns:
        SearchResultResponse: Complete search results with metadata and pagination

    Raises:
        HTTPException: 400 for invalid parameters, 401 for auth errors, 500 for server errors
    """
    try:
        user_id = get_current_user_id(request)

        search_request = SearchNotesRequest(
            q=q, tags=tags, section=section, page=page, limit=limit
        )

        if not search_request.has_search_criteria():
            raise HTTPException(
                status_code=400, detail="Search query or tags must be provided"
            )

        search_criteria = SearchCriteria.from_search_request(search_request, user_id)
        search_service.validate_search_criteria(search_criteria)

        search_result = await search_service.search_notes(db, search_criteria)
        response = SearchResultResponse.from_entity(search_result)

        logger.info(
            f"Search completed: found {len(search_result.notes)} notes "
            f"out of {search_result.pagination.total_notes} total for user {user_id}"
        )

        return response

    except ValueError as e:
        logger.warning(f"Invalid search request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except SearchError as e:
        logger.error(f"Search service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Search operation failed")

    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
