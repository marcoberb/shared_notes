import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from infrastructure.models.associations import note_tags
from infrastructure.models.note_orm import NoteORM
from infrastructure.models.note_share_orm import NoteShareORM
from infrastructure.models.tag_orm import TagORM
from utils.dependencies import get_current_user_id, get_db
from utils.keycloak import get_user_email_by_id, get_user_id_by_email
from application.utils import convert_note_to_response
from application.rest.schemas.input.note_input import NoteCreate, NoteUpdate
from application.rest.schemas.input.share_input import ShareRequest
from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.note_output import NoteResponse, NotesListResponse, PaginationInfo
from ..schemas.output.share_output import NoteSharesResponse, ShareResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    path="/notes",
    description="Retrieve all notes for the current user with pagination support.",
    response_model=NotesListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NotesListResponse,
            "description": "Paginated list of user's notes.",
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
                "application/json": {"example": {"detail": "Failed to retrieve notes."}}
            },
        },
    },
)
async def get_notes(
    request: Request, page: int = 1, limit: int = 10, db: Session = Depends(get_db)
):
    """Get all notes for the current user with pagination.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 10.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NotesListResponse: Paginated list of user's notes with pagination metadata.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await get_notes(request)
        >>> print(f"Total notes: {len(result.notes)}")
        Total notes: 5
    """
    user_id = get_current_user_id(request)
    logger.info(f"Getting notes for user_id: {user_id}, page: {page}, limit: {limit}")

    # Calculate offset
    offset = (page - 1) * limit

    # Get total count
    total_notes = (
        db.query(NoteORM)
        .filter(NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .count()
    )

    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1

    # Get notes for current page
    notes = (
        db.query(NoteORM)
        .filter(NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .order_by(NoteORM.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    logger.info(f"Found {len(notes)} notes for user {user_id} on page {page}")

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

    logger.info(f"Returning {len(notes_list)} notes with pagination: {pagination}")
    return NotesListResponse(notes=notes_list, pagination=pagination)


@router.get(
    path="/notes/my-notes",
    description="Retrieve all notes owned by the current user with pagination.",
    response_model=NotesListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NotesListResponse,
            "description": "Paginated list of user's own notes.",
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
                "application/json": {
                    "example": {"detail": "Failed to retrieve user notes."}
                }
            },
        },
    },
)
async def get_my_notes(
    request: Request,
    page: int = 1,
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db),
):
    """Get paginated list of user's own notes that are NOT shared with others.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NotesListResponse: Paginated list of user's private notes with pagination metadata.

    Raises:
        HTTPException: 400 if tag UUIDs are invalid format.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 for internal server errors.

    Example:
        >>> result = await get_my_notes(request, tags="uuid1,uuid2")
        >>> print(f"Private notes: {len(result.notes)}")
        Private notes: 3
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

    # Calculate offset
    offset = (page - 1) * limit

    # Get note IDs that are shared (to exclude them)
    shared_note_ids_subquery = (
        db.query(NoteShareORM.note_id)
        .filter(NoteShareORM.shared_by_user_id == user_id)
        .subquery()
    )

    # Base query for user's own notes that are NOT shared
    base_query = db.query(NoteORM).filter(
        NoteORM.owner_id == user_id,
        ~NoteORM.is_deleted,
        ~NoteORM.id.in_(db.query(shared_note_ids_subquery.c.note_id)),
    )

    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = (
            base_query.join(note_tags)
            .filter(note_tags.c.tag_id.in_(tag_ids))
            .group_by(NoteORM.id)
            .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
        )

    # Get total count
    total_notes = base_query.count()

    # Get notes for current page
    notes = (
        base_query.order_by(NoteORM.updated_at.desc()).offset(offset).limit(limit).all()
    )

    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1

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
        f"Returning {len(notes_list)} my notes for user {user_id} on page {page}"
    )
    return NotesListResponse(notes=notes_list, pagination=pagination)


@router.get(
    path="/notes/shared-by-me",
    description="Retrieve all notes that the current user has shared with others, with pagination.",
    response_model=NotesListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NotesListResponse,
            "description": "Paginated list of notes shared by the user.",
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
                "application/json": {
                    "example": {"detail": "Failed to retrieve shared notes."}
                }
            },
        },
    },
)
async def get_notes_shared_by_me(
    request: Request,
    page: int = 1,
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db),
):
    """Get notes owned by user that ARE shared with others.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NotesListResponse: Paginated list of notes shared by the user with pagination metadata.

    Raises:
        HTTPException: 400 if tag UUIDs are invalid format.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 for internal server errors.

    Example:
        >>> result = await get_notes_shared_by_me(request)
        >>> print(f"Shared by me: {result.pagination.total_notes}")
        Shared by me: 7
    """
    user_id = get_current_user_id(request)
    logger.info(
        f"Getting notes shared by me for user_id: {user_id}, page: {page}, limit: {limit}"
    )

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

    # Calculate offset
    offset = (page - 1) * limit

    # Get notes that are owned by user AND shared (present in note_shares)
    subquery = (
        db.query(NoteShareORM.note_id)
        .filter(NoteShareORM.shared_by_user_id == user_id)
        .subquery()
    )

    # Base query
    base_query = db.query(NoteORM).filter(
        NoteORM.owner_id == user_id,
        ~NoteORM.is_deleted,
        NoteORM.id.in_(db.query(subquery.c.note_id)),
    )

    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = (
            base_query.join(note_tags)
            .filter(note_tags.c.tag_id.in_(tag_ids))
            .group_by(NoteORM.id)
            .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
        )

    # Get total count
    total_notes = base_query.count()

    # Get notes for current page
    notes = (
        base_query.order_by(NoteORM.updated_at.desc()).offset(offset).limit(limit).all()
    )

    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1

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

    logger.info(f"Returning {len(notes_list)} notes shared by me")
    return NotesListResponse(notes=notes_list, pagination=pagination)


@router.get(
    path="/notes/shared-with-me",
    description="Retrieve all notes that have been shared with the current user, with pagination.",
    response_model=NotesListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NotesListResponse,
            "description": "Paginated list of notes shared with the user.",
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
                "application/json": {
                    "example": {"detail": "Failed to retrieve shared notes."}
                }
            },
        },
    },
)
async def get_notes_shared_with_me(
    request: Request,
    page: int = 1,
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db),
):
    """Get notes shared WITH the current user (not owned by them).

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NotesListResponse: Paginated list of notes shared with the user with pagination metadata.

    Raises:
        HTTPException: 400 if tag UUIDs are invalid format.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await get_notes_shared_with_me(request)
        >>> print(f"Shared with me: {result.pagination.total_notes}")
        Shared with me: 3
    """
    user_id = get_current_user_id(request)
    logger.info(
        f"Getting notes shared with me for user_id: {user_id}, page: {page}, limit: {limit}"
    )

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

    # Calculate offset
    offset = (page - 1) * limit

    # Get notes shared WITH user (not owned by user)
    subquery = (
        db.query(NoteShareORM.note_id)
        .filter(NoteShareORM.shared_with_user_id == user_id)
        .subquery()
    )

    # Base query
    base_query = db.query(NoteORM).filter(
        ~NoteORM.is_deleted, NoteORM.id.in_(db.query(subquery.c.note_id))
    )

    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = (
            base_query.join(note_tags)
            .filter(note_tags.c.tag_id.in_(tag_ids))
            .group_by(NoteORM.id)
            .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
        )

    # Get total count
    total_notes = base_query.count()

    # Get notes for current page
    notes = (
        base_query.order_by(NoteORM.updated_at.desc()).offset(offset).limit(limit).all()
    )

    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1

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

    logger.info(f"Returning {len(notes_list)} notes shared with me")
    return NotesListResponse(notes=notes_list, pagination=pagination)


@router.get(
    path="/notes/{note_id}",
    description="Retrieve a specific note by its ID. User must own the note or have it shared with them.",
    response_model=NoteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NoteResponse,
            "description": "Note details retrieved successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid note ID format.",
            "content": {
                "application/json": {"example": {"detail": "Invalid note ID format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to access this note.",
            "content": {
                "application/json": {
                    "example": {"detail": "Access denied to this note."}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found.",
            "content": {"application/json": {"example": {"detail": "Note not found."}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - database query failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to retrieve note."}}
            },
        },
    },
)
async def get_note(note_id: str, request: Request, db: Session = Depends(get_db)):
    """Get a specific note by ID.

    Args:
        note_id (str): UUID of the note to retrieve.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NoteResponse: Note details including title, content, tags, and metadata.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found or not owned by user.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> note = await get_note("uuid-123", request)
        >>> print(note.title)
        "My Important Note"
    """
    user_id = get_current_user_id(request)

    note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return convert_note_to_response(note)


@router.post(
    path="/notes",
    description="Create a new note with optional tags and sharing with other users.",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": NoteResponse,
            "description": "Note created successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid request data - missing required fields or invalid values.",
            "content": {
                "application/json": {
                    "example": {"detail": "Title and content are required."}
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
            "description": "Internal server error - note creation failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to create note."}}
            },
        },
    },
)
async def create_note(
    note: NoteCreate, request: Request, db: Session = Depends(get_db)
):
    """Create a new note with optional tags and sharing.

    Args:
        note (NoteCreate): Note creation data including title, content, tags, and share emails.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NoteResponse: Created note details including assigned UUID and metadata.

    Raises:
        HTTPException: 400 if user not found for share email.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> note_data = NoteCreate(title="Work Note", content="Important task", tags=["uuid1"])
        >>> created = await create_note(note_data, request)
        >>> print(created.id)
        "uuid-new-note"
    """
    user_id = get_current_user_id(request)

    # Create note
    db_note = NoteORM(title=note.title, content=note.content, owner_id=user_id)

    # Handle tags (now by ID)
    if note.tags:
        for tag_id in note.tags:
            tag = db.query(TagORM).filter(TagORM.id == tag_id).first()
            if tag:
                db_note.tags.append(tag)

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    # Handle sharing during creation
    if note.share_emails:
        for email in note.share_emails:
            # Resolve email to Keycloak user ID
            shared_with_user_id = await get_user_id_by_email(email)

            if not shared_with_user_id:
                # Rollback the note creation
                db.delete(db_note)
                db.commit()
                raise HTTPException(
                    status_code=400, detail=f"Utente non trovato per l'email: {email}"
                )

            # Check if already shared with this user (shouldn't happen during creation, but safety check)
            existing_share = (
                db.query(NoteShareORM)
                .filter(
                    NoteShareORM.note_id == db_note.id,
                    NoteShareORM.shared_with_user_id == shared_with_user_id,
                )
                .first()
            )

            if not existing_share:
                db_share = NoteShareORM(
                    note_id=db_note.id,
                    shared_by_user_id=user_id,
                    shared_with_user_id=shared_with_user_id,
                )
                db.add(db_share)

        db.commit()

    return convert_note_to_response(db_note)


@router.put(
    path="/notes/{note_id}",
    description="Update an existing note's title, content, or tags.",
    response_model=NoteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NoteResponse,
            "description": "Note updated successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid request data or note ID format.",
            "content": {
                "application/json": {"example": {"detail": "Invalid note ID format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to update this note.",
            "content": {
                "application/json": {
                    "example": {"detail": "You can only update your own notes."}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found.",
            "content": {"application/json": {"example": {"detail": "Note not found."}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - update operation failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to update note."}}
            },
        },
    },
)
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update an existing note.

    Args:
        note_id (str): UUID of the note to update.
        note_update (NoteUpdate): Updated note data with optional title, content, and tags.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NoteResponse: Updated note details with new timestamp.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found or not owned by user.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> update_data = NoteUpdate(title="Updated Title")
        >>> updated = await update_note("uuid-123", update_data, request)
        >>> print(updated.title)
        "Updated Title"
    """
    user_id = get_current_user_id(request)

    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Update fields
    if note_update.title is not None:
        db_note.title = note_update.title
    if note_update.content is not None:
        db_note.content = note_update.content

    # Update tags
    if note_update.tags is not None:
        db_note.tags.clear()
        for tag_id in note_update.tags:
            tag = db.query(TagORM).filter(TagORM.id == tag_id).first()
            if tag:
                db_note.tags.append(tag)

    db_note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_note)

    return convert_note_to_response(db_note)


@router.delete(
    path="/notes/{note_id}",
    description="Delete a note using soft delete (marks as deleted without removing from database).",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Note deleted successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid note ID format.",
            "content": {
                "application/json": {"example": {"detail": "Invalid note ID format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to delete this note.",
            "content": {
                "application/json": {
                    "example": {"detail": "You can only delete your own notes."}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found or already deleted.",
            "content": {"application/json": {"example": {"detail": "Note not found."}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - delete operation failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to delete note."}}
            },
        },
    },
)
async def delete_note(note_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a note (soft delete).

    Args:
        note_id (str): UUID of the note to delete.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        dict: Success message confirming deletion.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found or not owned by user.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await delete_note("uuid-123", request)
        >>> print(result["message"])
        "Note deleted successfully"
    """
    user_id = get_current_user_id(request)

    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    db_note.is_deleted = True
    db_note.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Note deleted successfully"}


# Share endpoints
@router.post(
    path="/notes/{note_id}/share",
    description="Share a note with one or more users by their email addresses.",
    response_model=NoteSharesResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": NoteSharesResponse,
            "description": "Note shared successfully with specified users.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid request data - invalid note ID, empty email list, or user not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email addresses provided."}
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
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to share this note.",
            "content": {
                "application/json": {
                    "example": {"detail": "You can only share your own notes."}
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found.",
            "content": {"application/json": {"example": {"detail": "Note not found."}}},
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Note already shared with one or more of the specified users.",
            "content": {
                "application/json": {
                    "example": {"detail": "Note already shared with user@example.com"}
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - sharing operation failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to share note."}}
            },
        },
    },
)
async def share_note(
    note_id: str,
    share_request: ShareRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Share a note with one or more users by email.

    Args:
        note_id (str): UUID of the note to share.
        share_request (ShareRequest): Request containing note ID and list of emails to share with.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NoteSharesResponse: All current shares for the note including newly created ones.

    Raises:
        HTTPException: 400 if note ID mismatch or user not found for email.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found or not owned by user.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> share_req = ShareRequest(note_id="uuid-123", emails=["user@email.com"])
        >>> shares = await share_note("uuid-123", share_req, request)
        >>> print(len(shares.shares))
        1
    """
    user_id = get_current_user_id(request)

    # Verify that the note exists and is owned by the current user
    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Validate that note_id in request matches URL parameter
    if share_request.note_id != note_id:
        raise HTTPException(status_code=400, detail="Note ID mismatch")

    created_shares = []

    # First validate all emails exist in Keycloak before creating any shares
    for email in share_request.emails:
        shared_with_user_id = await get_user_id_by_email(email)
        if not shared_with_user_id:
            raise HTTPException(
                status_code=400, detail=f"Utente non trovato per l'email: {email}"
            )

    # If all emails are valid, proceed with sharing
    for email in share_request.emails:
        # Resolve email to Keycloak user ID (we know it exists now)
        shared_with_user_id = await get_user_id_by_email(email)

        # Check if already shared with this user
        existing_share = (
            db.query(NoteShareORM)
            .filter(
                NoteShareORM.note_id == note_id,
                NoteShareORM.shared_with_user_id == shared_with_user_id,
            )
            .first()
        )

        if existing_share:
            continue  # Skip if already shared

        # Create new share
        db_share = NoteShareORM(
            note_id=note_id,
            shared_by_user_id=user_id,
            shared_with_user_id=shared_with_user_id,
        )

        db.add(db_share)
        created_shares.append(db_share)

    db.commit()

    # Return all shares for this note with emails
    all_shares = db.query(NoteShareORM).filter(NoteShareORM.note_id == note_id).all()
    shares_response = []

    for share in all_shares:
        # Get email for each shared user
        shared_email = await get_user_email_by_id(share.shared_with_user_id)
        shares_response.append(
            ShareResponse(
                id=str(share.id),
                note_id=str(share.note_id),
                shared_by_user_id=share.shared_by_user_id,
                shared_with_user_id=share.shared_with_user_id,
                shared_with_email=shared_email or "Email not found",
                created_at=share.created_at,
            )
        )

    return NoteSharesResponse(note_id=str(note_id), shares=shares_response)


@router.get(
    path="/notes/{note_id}/shares",
    description="Get all shares for a specific note. Only the note owner can access this information.",
    response_model=NoteSharesResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": NoteSharesResponse,
            "description": "List of all shares for the specified note.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid note ID format.",
            "content": {
                "application/json": {"example": {"detail": "Invalid note ID format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to view shares for this note.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can only view shares for your own notes."
                    }
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found.",
            "content": {"application/json": {"example": {"detail": "Note not found."}}},
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - database query failed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to retrieve note shares."}
                }
            },
        },
    },
)
async def get_note_shares(
    note_id: str, request: Request, db: Session = Depends(get_db)
):
    """Get all shares for a specific note.

    Args:
        note_id (str): UUID of the note to get shares for.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        NoteSharesResponse: All current shares for the note with user emails.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found or not owned by user.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> shares = await get_note_shares("uuid-123", request)
        >>> print(f"Shared with {len(shares.shares)} users")
        Shared with 2 users
    """
    user_id = get_current_user_id(request)

    # Verify that the note exists and is owned by the current user
    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get all shares for this note
    shares = db.query(NoteShareORM).filter(NoteShareORM.note_id == note_id).all()
    shares_response = []

    for share in shares:
        # Get email for each shared user
        shared_email = await get_user_email_by_id(share.shared_with_user_id)
        shares_response.append(
            ShareResponse(
                id=str(share.id),
                note_id=str(share.note_id),
                shared_by_user_id=share.shared_by_user_id,
                shared_with_user_id=share.shared_with_user_id,
                shared_with_email=shared_email or "Email not found",
                created_at=share.created_at,
            )
        )

    return NoteSharesResponse(note_id=str(note_id), shares=shares_response)


@router.delete(
    path="/notes/{note_id}/shares/{share_id}",
    description="Remove a specific share by share ID. Only the note owner can remove shares.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Share removed successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid note ID or share ID format.",
            "content": {
                "application/json": {"example": {"detail": "Invalid share ID format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to remove shares for this note.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can only remove shares for your own notes."
                    }
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note or share not found.",
            "content": {
                "application/json": {"example": {"detail": "Share not found."}}
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - share removal failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to remove share."}}
            },
        },
    },
)
async def remove_note_share(
    note_id: str, share_id: str, request: Request, db: Session = Depends(get_db)
):
    """Remove a specific share from a note by share ID.

    Args:
        note_id (str): UUID of the note to remove share from.
        share_id (str): UUID of the specific share to remove.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        dict: Success message confirming share removal.

    Raises:
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found, not owned by user, or share not found.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await remove_note_share("uuid-123", "share-uuid", request)
        >>> print(result["message"])
        "Share removed successfully"
    """
    user_id = get_current_user_id(request)

    # Verify that the note exists and is owned by the current user
    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Find the share to delete
    db_share = (
        db.query(NoteShareORM)
        .filter(NoteShareORM.id == share_id, NoteShareORM.note_id == note_id)
        .first()
    )

    if not db_share:
        raise HTTPException(status_code=404, detail="Share not found")

    db.delete(db_share)
    db.commit()

    return {"message": "Share removed successfully"}


@router.delete(
    path="/notes/{note_id}/shares/by-email/{email}",
    description="Remove a share by specifying the email address of the user. Only the note owner can remove shares.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Share removed successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid note ID format or malformed email address.",
            "content": {
                "application/json": {"example": {"detail": "Invalid email format."}}
            },
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "User authentication required.",
            "content": {
                "application/json": {"example": {"detail": "Authentication required."}}
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "User not authorized to remove shares for this note.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You can only remove shares for your own notes."
                    }
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Note not found, user not found, or note not shared with specified user.",
            "content": {
                "application/json": {
                    "example": {"detail": "Note not shared with this user."}
                }
            },
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error - share removal failed.",
            "content": {
                "application/json": {"example": {"detail": "Failed to remove share."}}
            },
        },
    },
)
async def remove_note_share_by_email(
    note_id: str, email: str, request: Request, db: Session = Depends(get_db)
):
    """Remove a share from a note by email address.

    Args:
        note_id (str): UUID of the note to remove share from.
        email (str): Email address of the user to remove from sharing.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.

    Returns:
        dict: Success message confirming share removal.

    Raises:
        HTTPException: 400 if user not found for email.
        HTTPException: 401 if user ID not found in headers.
        HTTPException: 404 if note not found, not owned by user, or share not found.
        HTTPException: 500 if internal server errors occur.

    Example:
        >>> result = await remove_note_share_by_email("uuid-123", "user@email.com", request)
        >>> print(result["message"])
        "Share removed successfully"
    """
    user_id = get_current_user_id(request)

    # Verify that the note exists and is owned by the current user
    db_note = (
        db.query(NoteORM)
        .filter(NoteORM.id == note_id, NoteORM.owner_id == user_id, ~NoteORM.is_deleted)
        .first()
    )

    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get user ID from email
    shared_with_user_id = await get_user_id_by_email(email)
    if not shared_with_user_id:
        raise HTTPException(
            status_code=400, detail=f"User not found for email: {email}"
        )

    # Find the share to delete
    db_share = (
        db.query(NoteShareORM)
        .filter(
            NoteShareORM.note_id == note_id,
            NoteShareORM.shared_with_user_id == shared_with_user_id,
        )
        .first()
    )

    if not db_share:
        raise HTTPException(status_code=404, detail="Share not found")

    db.delete(db_share)
    db.commit()

    return {"message": "Share removed successfully"}
