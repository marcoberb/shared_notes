"""Note output schemas for API responses.

This module contains Pydantic models for note-related API responses,
including single notes, pagination info, and note lists.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from application.rest.schemas.output.tag_output import TagResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from domain.entities.note import Note
    from domain.entities.search import PaginationMetadata, SearchResult


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
    tags: List[TagResponse]

    @classmethod
    def from_entity(cls, note: Note) -> NoteResponse:
        """Create NoteResponse from Note domain entity.

        Args:
            note: The domain Note entity to convert

        Returns:
            NoteResponse: The converted note response schema
        """

        return cls(
            id=str(note.id),
            title=note.title,
            content=note.content,
            owner_id=str(note.owner_id),
            created_at=note.created_at,
            updated_at=note.updated_at,
            tags=[TagResponse.from_entity(tag) for tag in note.tags],
        )


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

    @classmethod
    def from_entity(cls, pagination_metadata: PaginationMetadata) -> PaginationInfo:
        """Convert domain PaginationMetadata to API response PaginationInfo.

        Args:
            pagination_metadata: Domain pagination metadata entity.

        Returns:
            PaginationInfo: Corresponding API response model.
        """
        return cls(
            current_page=pagination_metadata.current_page,
            total_pages=pagination_metadata.total_pages,
            total_notes=pagination_metadata.total_notes,
            notes_per_page=pagination_metadata.notes_per_page,
            has_next=pagination_metadata.has_next,
            has_previous=pagination_metadata.has_previous,
        )


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

    @classmethod
    def from_entity(cls, search_result: SearchResult) -> NotesListResponse:
        """Convert domain SearchResult to API response NotesListResponse.

        Args:
            search_result: Domain search result entity.

        Returns:
            NotesListResponse: Corresponding API response model.
        """
        return cls(
            notes=[NoteResponse.from_entity(note) for note in search_result.notes],
            pagination=PaginationInfo.from_entity(search_result.pagination),
        )
