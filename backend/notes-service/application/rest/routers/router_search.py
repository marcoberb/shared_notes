import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

from infrastructure.models.associations import note_tags
from infrastructure.models.note_orm import NoteORM
from infrastructure.models.note_share_orm import NoteShareORM
from utils.dependencies import get_current_user_id, get_db
from application.utils import convert_note_to_response
from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.note_output import NotesListResponse, PaginationInfo

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    path="/search",
    description="Search notes using full-text search and tag filtering across different sections.",
    response_model=NotesListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NotesListResponse,
            "description": "List of notes matching search criteria with pagination.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid request parameters (invalid section, page, limit, etc.).",
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
            "description": "Internal server error - database query failed.",
            "content": {
                "application/json": {"example": {"detail": "Search operation failed."}}
            },
        },
    },
)
async def search_notes(
    request: Request,
    q: str = "",
    tags: Optional[str] = None,  # Comma-separated tag IDs
    section: str = "my-notes",  # Section to search: my-notes, shared-by-me, shared-with-me
    page: int = 1,
    limit: int = 15,
    db: Session = Depends(get_db),
) -> NotesListResponse:
    """Search notes using PostgreSQL full-text search and/or tag filtering in specific section.

    Args:
        request (Request): FastAPI request object containing user headers.
        q (str, optional): Search query string for full-text search. Defaults to "".
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        section (str, optional): Section to search in. Options: "my-notes", "shared-by-me",
            "shared-with-me". Defaults to "my-notes".
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of results per page. Defaults to 15.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NotesListResponse: Paginated list of notes matching search criteria with pagination info.

    Raises:
        HTTPException: 400 if neither search query nor tags provided.
        HTTPException: 400 if tag UUIDs are invalid format.
        HTTPException: 400 if section parameter is invalid.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await search_notes(request, q="work", tags="uuid1,uuid2", section="my-notes")
        >>> print(result.pagination.total_notes)
        5
    """
    user_id = get_current_user_id(request)

    # Parse tag IDs from query parameter
    tag_ids = []
    if tags:
        try:
            tag_ids = [
                uuid.UUID(tag_id.strip())
                for tag_id in tags.split(",")
                if tag_id.strip()
            ]
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid UUID format for tag IDs"
            )

    # If neither text search nor tag filter, return error
    if not q.strip() and not tag_ids:
        raise HTTPException(
            status_code=400, detail="Search query or tags must be provided"
        )

    # Calculate offset
    offset = (page - 1) * limit

    # Start building the query based on section
    if section == "my-notes":
        # Get notes shared by user (exclude these from personal notes)
        shared_note_ids_subquery = (
            db.query(NoteShareORM.note_id).filter(
                NoteShareORM.shared_by_user_id == user_id
            )
        ).subquery()

        # Query only personal notes (not shared by user)
        base_query = db.query(NoteORM).filter(
            NoteORM.owner_id == user_id,
            ~NoteORM.is_deleted,
            ~NoteORM.id.in_(db.query(shared_note_ids_subquery.c.note_id)),
        )
    elif section == "shared-by-me":
        # Get notes that are owned by user AND shared (present in note_shares)
        shared_note_ids_subquery = (
            db.query(NoteShareORM.note_id)
            .filter(NoteShareORM.shared_by_user_id == user_id)
            .subquery()
        )

        base_query = db.query(NoteORM).filter(
            NoteORM.owner_id == user_id,
            ~NoteORM.is_deleted,
            NoteORM.id.in_(db.query(shared_note_ids_subquery.c.note_id)),
        )
    elif section == "shared-with-me":
        # Get notes shared with user (not owned by user)
        shared_note_ids_subquery = (
            db.query(NoteShareORM.note_id)
            .filter(NoteShareORM.shared_with_user_id == user_id)
            .subquery()
        )

        base_query = db.query(NoteORM).filter(
            ~NoteORM.is_deleted,
            NoteORM.id.in_(db.query(shared_note_ids_subquery.c.note_id)),
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid section. Must be one of: my-notes, shared-by-me, shared-with-me",
        )

    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        # Join with note_tags and group by note to ensure the note has ALL selected tags
        base_query = (
            base_query.join(note_tags)
            .filter(note_tags.c.tag_id.in_(tag_ids))
            .group_by(NoteORM.id)
            .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
        )

    # Add text search if provided
    if q.strip():
        search_query = q.strip()
        search_pattern = f"%{search_query}%"

        # Full-text search condition
        fulltext_condition = NoteORM.search_vector.op("@@")(
            func.plainto_tsquery("simple", search_query)
        )

        # Substring search condition (case-insensitive)
        substring_condition = or_(
            NoteORM.title.ilike(search_pattern), NoteORM.content.ilike(search_pattern)
        )

        # Combine both conditions with OR
        search_condition = or_(fulltext_condition, substring_condition)
        base_query = base_query.filter(search_condition)

    # Get total count for pagination
    total_notes = base_query.count()

    # Get notes with ordering
    notes = (
        base_query.order_by(NoteORM.updated_at.desc()).offset(offset).limit(limit).all()
    )

    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1

    logger.info(
        f"Found {len(notes)} notes for search '{q}' with tags {tag_ids} in section '{section}' for user {user_id} on page {page}"
    )

    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))

    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous,
    )

    logger.info(
        f"Returning {len(notes_list)} search results with pagination: {pagination}"
    )
    return NotesListResponse(notes=notes_list, pagination=pagination)
