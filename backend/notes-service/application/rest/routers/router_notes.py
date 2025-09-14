"""
This module contains the FastAPI router for note operations.
"""

import logging
import uuid
from typing import Optional
from uuid import UUID

from application.rest.schemas.input.note_input import NoteCreate, NoteUpdate
from application.rest.schemas.input.share_input import ShareRequest
from application.rest.schemas.output.common_output import ErrorResponse
from application.rest.schemas.output.note_output import (
    NoteResponse,
    NotesListResponse,
    PaginationInfo,
)
from application.rest.schemas.output.share_output import (
    NoteSharesResponse,
    ShareResponse,
)
from domain.services.note_service import NoteError, NoteNotFoundError, NoteService
from domain.services.tag_service import TagService
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from utils.dependencies import (
    get_current_user_id,
    get_db,
    get_note_service,
    get_tag_service,
)
from utils.keycloak import get_user_email_by_id, get_user_id_by_email

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
    request: Request,
    page: int = 1,
    limit: int = 10,
    tag_ids: Optional[str] = None,
    note_service: NoteService = Depends(get_note_service),
    db: Session = Depends(get_db),
) -> NotesListResponse:
    """Retrieve all notes for the current user with pagination support.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 10.
        tag_ids (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        note_service (NoteService): Domain service for note operations.
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
    try:
        user_id = get_current_user_id(request)
        logger.info(
            f"Getting notes for user_id: {user_id}, page: {page}, limit: {limit}"
        )

        # Parse tag_ids if provided
        tag_uuids = None
        if tag_ids:
            try:
                tag_uuids = [uuid.UUID(tag_id.strip()) for tag_id in tag_ids.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid tag ID format")

        notes, pagination = await note_service.get_user_notes_paginated(
            db, user_id, page, limit, tag_uuids
        )

        note_responses = [NoteResponse.from_entity(note) for note in notes]

        response = NotesListResponse(
            notes=note_responses,
            pagination=PaginationInfo.from_entity(pagination),
        )

        logger.info(f"Returning {len(note_responses)} notes for user {user_id}")
        return response

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notes")

    except Exception as e:
        logger.error(f"Unexpected error getting notes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_service: NoteService = Depends(get_note_service),
):
    """Get paginated list of user's own notes that are NOT shared with others.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(f"Getting my notes for user {user_id}, page {page}, limit {limit}")

    try:
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

        # Use domain service to get paginated notes
        notes, pagination = await note_service.get_my_notes_paginated(
            db_session=db,
            user_id=user_id,
            page=page,
            limit=limit,
            tag_ids=tag_ids,
        )

        note_responses = [NoteResponse.from_entity(note) for note in notes]

        response = NotesListResponse(
            notes=note_responses,
            pagination=PaginationInfo.from_entity(pagination),
        )

        logger.info(f"Returning {len(note_responses)} my notes for user {user_id}")
        return response

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve my notes")

    except Exception as e:
        logger.error(f"Unexpected error getting my notes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_service: NoteService = Depends(get_note_service),
):
    """Get notes owned by user that ARE shared with others.

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
        f"Getting notes shared by me for user {user_id}, page {page}, limit {limit}"
    )

    try:
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

        # Use domain service to get paginated notes
        notes, pagination = await note_service.get_notes_shared_by_me_paginated(
            db_session=db,
            user_id=user_id,
            page=page,
            limit=limit,
            tag_ids=tag_ids,
        )

        note_responses = [NoteResponse.from_entity(note) for note in notes]

        response = NotesListResponse(
            notes=note_responses,
            pagination=PaginationInfo.from_entity(pagination),
        )

        logger.info(f"Returning {len(note_responses)} notes shared by me")
        return response

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve shared notes")

    except Exception as e:
        logger.error(f"Unexpected error getting shared notes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_service: NoteService = Depends(get_note_service),
):
    """Get notes shared WITH the current user (not owned by them).

    Args:
        request (Request): FastAPI request object containing user headers.
        page (int, optional): Page number for pagination. Defaults to 1.
        limit (int, optional): Number of notes per page. Defaults to 15.
        tags (Optional[str], optional): Comma-separated tag UUIDs for filtering. Defaults to None.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
        f"Getting notes shared with me for user {user_id}, page {page}, limit {limit}"
    )

    try:
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

        # Use domain service to get paginated notes
        notes, pagination = await note_service.get_notes_shared_with_me_paginated(
            db_session=db,
            user_id=user_id,
            page=page,
            limit=limit,
            tag_ids=tag_ids,
        )

        note_responses = [NoteResponse.from_entity(note) for note in notes]

        response = NotesListResponse(
            notes=note_responses,
            pagination=PaginationInfo.from_entity(pagination),
        )

        logger.info(f"Returning {len(note_responses)} notes shared with me")
        return response

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve shared notes")

    except Exception as e:
        logger.error(f"Unexpected error getting shared notes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
async def get_note(
    note_id: str,
    request: Request,
    db: Session = Depends(get_db),
    note_service: NoteService = Depends(get_note_service),
):
    """Get a specific note by ID.

    Args:
        note_id (str): UUID of the note to retrieve.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(f"Getting note {note_id} for user {user_id}")

    try:
        # Parse note UUID
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid note ID format")

        # Use domain service to get note
        note = await note_service.get_note(
            db_session=db,
            note_id=note_uuid,
            user_id=user_id,
        )

        response = NoteResponse.from_entity(note)
        logger.info(f"Retrieved note {note_id} successfully")
        return response

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve note")

    except Exception as e:
        logger.error(f"Unexpected error getting note: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note: NoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    note_service: NoteService = Depends(get_note_service),
    tag_service: TagService = Depends(get_tag_service),
):
    """Create a new note with optional tags and sharing.

    Args:
        note (NoteCreate): Note creation data including title, content, tags, and share emails.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.
        tag_service (TagService): Domain service for tag operations.

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
    logger.info(f"Creating note for user {user_id}")
    logger.info(
        f"Note data: title='{note.title}', content length={len(note.content)}, tags={note.tags}, share_emails={note.share_emails}"
    )

    try:
        # Convert tag IDs to tag entities
        tag_entities = []
        if note.tags:
            # Convert string UUIDs to UUID objects for comparison
            requested_tag_uuids = [UUID(tag_id) for tag_id in note.tags]

            # Get all tags from repository and filter by requested IDs
            all_tags = await tag_service.get_all_tags(db)
            tag_entities = [tag for tag in all_tags if tag.id in requested_tag_uuids]

            # Validate that all requested tags exist
            found_tag_ids = {tag.id for tag in tag_entities}
            requested_tag_ids = set(requested_tag_uuids)
            missing_tags = requested_tag_ids - found_tag_ids
            if missing_tags:
                raise HTTPException(
                    status_code=400, detail=f"Tags not found: {list(missing_tags)}"
                )

        # Validate all emails BEFORE creating the note
        shared_user_ids = []
        if note.share_emails:
            logger.info(
                f"Processing {len(note.share_emails)} emails for sharing: {note.share_emails}"
            )
            for email in note.share_emails:
                # Resolve email to Keycloak user ID
                shared_with_user_id = await get_user_id_by_email(email)

                if not shared_with_user_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Utente non trovato per l'email: {email}",
                    )

                logger.info(f"Email {email} resolved to user ID: {shared_with_user_id}")
                shared_user_ids.append((email, shared_with_user_id))
        else:
            logger.info("No emails provided for sharing")

        # Use domain service to create note
        created_note = await note_service.create_note(
            db_session=db,
            title=note.title,
            content=note.content,
            owner_id=user_id,
            tag_entities=tag_entities,
        )

        # Handle sharing after successful note creation
        if shared_user_ids:
            try:
                # Extract just the user IDs for the sharing operation
                user_ids_to_share_with = [user_id for _, user_id in shared_user_ids]
                emails_list = [email for email, _ in shared_user_ids]

                logger.info(
                    f"Sharing note {created_note.id} with {len(user_ids_to_share_with)} users: {emails_list}"
                )

                # Use domain service to share note with all users at once
                await note_service.share_note_with_users(
                    db_session=db,
                    note_id=created_note.id,
                    owner_id=user_id,
                    shared_with_user_ids=user_ids_to_share_with,
                )
                logger.info(
                    f"Successfully shared note {created_note.id} with all users"
                )

            except Exception as e:
                logger.error(f"Failed to share note: {str(e)}")
                raise e

        response = NoteResponse.from_entity(created_note)
        logger.info(f"Successfully created note {created_note.id}")
        return response

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create note: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error creating note: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_service: NoteService = Depends(get_note_service),
    tag_service: TagService = Depends(get_tag_service),
):
    """Update an existing note.

    Args:
        note_id (str): UUID of the note to update.
        note_update (NoteUpdate): Updated note data with optional title, content, and tags.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.
        tag_service (TagService): Domain service for tag operations.

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
    logger.info(f"Updating note {note_id} for user {user_id}")

    try:
        # Parse note UUID
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid note ID format")

        # Convert tag IDs to tag entities if provided
        tag_entities = None
        if note_update.tags is not None:
            # Convert string UUIDs to UUID objects for comparison
            requested_tag_uuids = [UUID(tag_id) for tag_id in note_update.tags]

            # Get all tags from repository and filter by requested IDs
            all_tags = await tag_service.get_all_tags(db)
            tag_entities = [tag for tag in all_tags if tag.id in requested_tag_uuids]

            # Validate that all requested tags exist
            found_tag_ids = {tag.id for tag in tag_entities}
            requested_tag_ids = set(requested_tag_uuids)
            missing_tags = requested_tag_ids - found_tag_ids
            if missing_tags:
                raise HTTPException(
                    status_code=400, detail=f"Tags not found: {list(missing_tags)}"
                )

        # Use domain service to update note
        updated_note = await note_service.update_note(
            db_session=db,
            note_id=note_uuid,
            user_id=user_id,
            title=note_update.title,
            content=note_update.content,
            tag_entities=tag_entities,
        )

        response = NoteResponse.from_entity(updated_note)
        logger.info(f"Successfully updated note {note_id}")
        return response

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update note: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error updating note: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
async def delete_note(
    note_id: str,
    request: Request,
    db: Session = Depends(get_db),
    note_service: NoteService = Depends(get_note_service),
):
    """Delete a note (soft delete).

    Args:
        note_id (str): UUID of the note to delete.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(f"Deleting note {note_id} for user {user_id}")

    try:
        # Parse note UUID
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid note ID format")

        # Use domain service to delete note
        success = await note_service.delete_note(
            db_session=db,
            note_id=note_uuid,
            user_id=user_id,
        )

        if success:
            logger.info(f"Successfully deleted note {note_id}")
            return {"message": "Note deleted successfully"}
        else:
            logger.warning(f"Failed to delete note {note_id}")
            raise HTTPException(status_code=500, detail="Failed to delete note")

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except HTTPException:
        raise

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete note: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error deleting note: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_service: NoteService = Depends(get_note_service),
):
    """Share a note with one or more users by email.

    Args:
        note_id (str): UUID of the note to share.
        share_request (ShareRequest): Request containing note ID and list of emails to share with.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(
        f"Sharing note {note_id} for user {user_id} with {len(share_request.emails)} recipients"
    )

    try:
        # Parse note UUID
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid note ID format")

        # Validate that note_id in request matches URL parameter
        if share_request.note_id != note_id:
            raise HTTPException(status_code=400, detail="Note ID mismatch")

        # First validate all emails exist in Keycloak before creating any shares
        validated_user_ids = []
        for email in share_request.emails:
            shared_with_user_id = await get_user_id_by_email(email)
            if not shared_with_user_id:
                raise HTTPException(
                    status_code=400, detail=f"Utente non trovato per l'email: {email}"
                )
            validated_user_ids.append(shared_with_user_id)

        # Share note with each validated user using domain service
        for shared_with_user_id in validated_user_ids:
            try:
                await note_service.share_note(
                    db_session=db,
                    note_id=note_uuid,
                    shared_by_user_id=user_id,
                    shared_with_user_id=shared_with_user_id,
                )
            except NoteError as e:
                # Skip if already shared - this is not an error in this context
                logger.info(
                    f"Note already shared with user {shared_with_user_id}: {str(e)}"
                )
                continue

        # Get all current shares for the note using domain service
        shares = await note_service.get_note_shares(
            db_session=db,
            note_id=note_uuid,
            user_id=user_id,
        )

        # Build response with emails
        shares_response = []
        for share in shares:
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

        response = NoteSharesResponse(note_id=str(note_id), shares=shares_response)
        logger.info(
            f"Successfully shared note {note_id} with {len(validated_user_ids)} users"
        )
        return response

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to share note")

    except Exception as e:
        logger.error(f"Unexpected error sharing note: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_id: str,
    request: Request,
    note_service: NoteService = Depends(get_note_service),
    db: Session = Depends(get_db),
) -> NoteSharesResponse:
    """Get all shares for a specific note.

    Args:
        note_id (str): UUID of the note to get shares for.
        request (Request): FastAPI request object containing user headers.
        note_service: Note service dependency
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
    try:
        user_id = get_current_user_id(request)
        note_uuid = uuid.UUID(note_id)

        logger.info(f"Getting shares for note {note_uuid} by user {user_id}")

        # Use domain service to get shares
        shares_data = await note_service.get_note_shares(db, note_uuid, user_id)

        # Enrich shares with user emails from Keycloak
        enriched_shares_data = []
        for share_data in shares_data:
            shared_email = await get_user_email_by_id(share_data["shared_with_user_id"])
            enriched_share = {
                **share_data,
                "shared_with_email": shared_email or "Email not found",
            }
            enriched_shares_data.append(enriched_share)

        # Use classmethod to convert to response
        response = NoteSharesResponse.from_shares_data(note_id, enriched_shares_data)

        logger.info(
            f"Retrieved {len(enriched_shares_data)} shares for note {note_uuid}"
        )
        return response

    except ValueError as e:
        logger.warning(f"Invalid note ID format: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid note ID format")

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve note shares")

    except Exception as e:
        logger.error(f"Unexpected error getting note shares: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_id: str,
    share_id: str,
    request: Request,
    db: Session = Depends(get_db),
    note_service: NoteService = Depends(get_note_service),
):
    """Remove a specific share from a note by share ID.

    Args:
        note_id (str): UUID of the note to remove share from.
        share_id (str): UUID of the specific share to remove.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(f"Removing share {share_id} from note {note_id} for user {user_id}")

    try:
        # Parse UUIDs
        try:
            note_uuid = uuid.UUID(note_id)
            share_uuid = uuid.UUID(share_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format")

        # First get the share details to find the shared_with_user_id
        shares = await note_service.get_note_shares(
            db_session=db,
            note_id=note_uuid,
            user_id=user_id,
        )

        # Find the specific share by ID
        target_share = None
        for share in shares:
            if share.id == share_uuid:
                target_share = share
                break

        if not target_share:
            raise HTTPException(status_code=404, detail="Share not found")

        # Use domain service to unshare note
        success = await note_service.unshare_note(
            db_session=db,
            note_id=note_uuid,
            shared_by_user_id=user_id,
            shared_with_user_id=target_share.shared_with_user_id,
        )

        if success:
            logger.info(f"Successfully removed share {share_id}")
            return {"message": "Share removed successfully"}
        else:
            logger.warning(f"Failed to remove share {share_id}")
            raise HTTPException(status_code=500, detail="Failed to remove share")

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to remove share")

    except Exception as e:
        logger.error(f"Unexpected error removing share: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


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
    note_id: str,
    email: str,
    request: Request,
    db: Session = Depends(get_db),
    note_service: NoteService = Depends(get_note_service),
):
    """Remove a share from a note by email address.

    Args:
        note_id (str): UUID of the note to remove share from.
        email (str): Email address of the user to remove from sharing.
        request (Request): FastAPI request object containing user headers.
        db (Session): Database session dependency injected by FastAPI.
        note_service (NoteService): Domain service for note operations.

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
    logger.info(
        f"Removing share from note {note_id} for email {email} by user {user_id}"
    )

    try:
        # Parse note UUID
        try:
            note_uuid = uuid.UUID(note_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid note ID format")

        # Get user ID from email
        shared_with_user_id = await get_user_id_by_email(email)
        if not shared_with_user_id:
            raise HTTPException(
                status_code=400, detail=f"User not found for email: {email}"
            )

        # Use domain service to unshare note
        success = await note_service.unshare_note(
            db_session=db,
            note_id=note_uuid,
            shared_by_user_id=user_id,
            shared_with_user_id=shared_with_user_id,
        )

        if success:
            logger.info(
                f"Successfully removed share from note {note_id} for email {email}"
            )
            return {"message": "Share removed successfully"}
        else:
            logger.warning(
                f"Failed to remove share from note {note_id} for email {email}"
            )
            raise HTTPException(status_code=404, detail="Share not found")

    except NoteNotFoundError as e:
        logger.warning(f"Note not found: {str(e)}")
        raise HTTPException(status_code=404, detail="Note not found")

    except ValueError as e:
        logger.warning(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except NoteError as e:
        logger.error(f"Note service error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to remove share")

    except Exception as e:
        logger.error(f"Unexpected error removing share: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
