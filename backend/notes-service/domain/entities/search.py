"""Search domain entities for the shared notes application.

This module contains the domain entities for search functionality, representing
the core business concepts related to searching notes.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

if TYPE_CHECKING:
    from domain.entities.note import Note


class SearchSection(Enum):
    """Enumeration for different search sections."""

    MY_NOTES = "my-notes"
    SHARED_BY_ME = "shared-by-me"
    SHARED_WITH_ME = "shared-with-me"


@dataclass
class SearchCriteria:
    """Domain entity representing search criteria for notes.

    This entity encapsulates all the parameters needed to perform a search
    operation on notes, following Domain-Driven Design principles.

    Attributes:
        user_id: UUID of the user performing the search
        query: Text query for full-text search (optional)
        tag_ids: List of tag UUIDs for filtering (optional)
        section: Section to search in (my-notes, shared-by-me, shared-with-me)
        page: Page number for pagination (1-based)
        limit: Number of results per page
    """

    user_id: UUID
    query: Optional[str] = None
    tag_ids: Optional[List[UUID]] = None
    section: SearchSection = SearchSection.MY_NOTES
    page: int = 1
    limit: int = 15

    def __post_init__(self):
        """Validate search criteria after initialization."""
        if self.page < 1:
            raise ValueError("Page number must be at least 1")
        if self.limit < 1 or self.limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        if not self.query and not self.tag_ids:
            raise ValueError("Either query or tag_ids must be provided")
        if self.query is not None:
            self.query = self.query.strip()
            if not self.query and not self.tag_ids:
                raise ValueError("Query cannot be empty if no tags provided")

    @property
    def offset(self) -> int:
        """Calculate the offset for database pagination."""
        return (self.page - 1) * self.limit

    def has_text_search(self) -> bool:
        """Check if this criteria includes text search."""
        return self.query is not None and len(self.query.strip()) > 0

    def has_tag_filter(self) -> bool:
        """Check if this criteria includes tag filtering."""
        return self.tag_ids is not None and len(self.tag_ids) > 0

    @classmethod
    def from_search_request(cls, request, user_id: UUID) -> "SearchCriteria":
        """Create SearchCriteria from search request and user ID.

        Args:
            request: Search request with parameters
            user_id: UUID of the user performing the search

        Returns:
            SearchCriteria: Domain entity representing the search criteria

        Raises:
            ValueError: If request contains invalid data
        """
        # Convert section string to enum
        section_map = {
            "my-notes": SearchSection.MY_NOTES,
            "shared-by-me": SearchSection.SHARED_BY_ME,
            "shared-with-me": SearchSection.SHARED_WITH_ME,
        }

        section = section_map.get(request.section)
        if not section:
            raise ValueError(f"Invalid section: {request.section}")

        # Parse tag IDs if provided
        tag_ids = None
        if request.tags:
            tag_ids = request.get_tag_ids()

        # Create and return SearchCriteria domain entity
        return cls(
            user_id=user_id,
            query=request.q if request.q and request.q.strip() else None,
            tag_ids=tag_ids,
            section=section,
            page=request.page,
            limit=request.limit,
        )


@dataclass
class PaginationMetadata:
    """Domain entity representing pagination information for search results.

    This entity contains all the metadata needed to handle pagination
    in search results.

    Attributes:
        current_page: Current page number
        total_pages: Total number of pages
        total_notes: Total number of notes found
        notes_per_page: Number of notes per page
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """

    current_page: int
    total_pages: int
    total_notes: int
    notes_per_page: int
    has_next: bool
    has_previous: bool

    @classmethod
    def calculate(
        cls, current_page: int, total_notes: int, notes_per_page: int
    ) -> "PaginationMetadata":
        """Calculate pagination metadata from basic parameters.

        Args:
            current_page: The current page number (1-based)
            total_notes: Total number of notes found
            notes_per_page: Number of notes per page

        Returns:
            PaginationMetadata: Calculated pagination information
        """
        total_pages = (
            (total_notes + notes_per_page - 1) // notes_per_page
            if total_notes > 0
            else 1
        )
        has_next = current_page < total_pages
        has_previous = current_page > 1

        return cls(
            current_page=current_page,
            total_pages=total_pages,
            total_notes=total_notes,
            notes_per_page=notes_per_page,
            has_next=has_next,
            has_previous=has_previous,
        )


@dataclass
class SearchResult:
    """Domain entity representing the result of a search operation.

    This entity encapsulates the notes found and pagination information
    for a search operation.

    Attributes:
        notes: List of notes found in the search
        pagination: Pagination metadata for the search results
        criteria: The search criteria that produced these results
        search_timestamp: When the search was performed
    """

    notes: List["Note"]
    pagination: PaginationMetadata
    criteria: SearchCriteria
    search_timestamp: datetime

    def __post_init__(self):
        """Validate search result after initialization."""
        if len(self.notes) > self.pagination.notes_per_page:
            raise ValueError("Number of notes exceeds page limit")

    @property
    def notes_count(self) -> int:
        """Get the number of notes in this result page."""
        return len(self.notes)

    def is_empty(self) -> bool:
        """Check if the search result is empty."""
        return len(self.notes) == 0
