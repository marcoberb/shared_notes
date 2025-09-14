"""Note output schemas for API responses.

This module contains Pydantic models for note-related API responses,
including single notes, pagination info, and note lists.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel


class NoteResponse(BaseModel):
    """Schema for note data in API responses.

    Attributes:
        id (str): UUID string identifier of the note.
        title (str): The title of the note.
        content (str): The content/body of the note.
        owner_id (str): Keycloak UUID of the note owner.
        created_at (datetime): Timestamp when the note was created.
        updated_at (datetime): Timestamp when the note was last updated.
        tags (List[dict]): List of tags associated with the note.

    Example:
        >>> note_response = NoteResponse(
        ...     id="note-uuid-123",
        ...     title="Meeting Notes",
        ...     content="Important points",
        ...     owner_id="user-uuid-456",
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now(),
        ...     tags=[{"id": "tag-uuid", "name": "work"}]
        ... )
    """

    id: str  # UUID as string
    title: str
    content: str
    owner_id: str  # Keycloak UUID
    created_at: datetime
    updated_at: datetime
    tags: List[dict]  # Will be List[TagResponse] at runtime


class PaginationInfo(BaseModel):
    """Schema for pagination metadata in API responses.

    Attributes:
        current_page (int): Current page number (1-indexed).
        total_pages (int): Total number of pages available.
        total_notes (int): Total number of notes across all pages.
        notes_per_page (int): Number of notes per page.
        has_next (bool): Whether there is a next page available.
        has_previous (bool): Whether there is a previous page available.

    Example:
        >>> pagination = PaginationInfo(
        ...     current_page=2,
        ...     total_pages=5,
        ...     total_notes=47,
        ...     notes_per_page=10,
        ...     has_next=True,
        ...     has_previous=True
        ... )
    """

    current_page: int
    total_pages: int
    total_notes: int
    notes_per_page: int
    has_next: bool
    has_previous: bool


class NotesListResponse(BaseModel):
    """Schema for paginated notes list API responses.

    Attributes:
        notes (List[NoteResponse]): List of notes for the current page.
        pagination (PaginationInfo): Pagination metadata.

    Example:
        >>> notes_list = NotesListResponse(
        ...     notes=[note1, note2, note3],
        ...     pagination=pagination_info
        ... )
    """

    notes: List[NoteResponse]
    pagination: PaginationInfo
