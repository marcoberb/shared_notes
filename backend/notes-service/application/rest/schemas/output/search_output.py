"""Search output schemas for the shared notes application.

This module contains Pydantic models for search response output serialization.
"""

from datetime import datetime
from typing import List

from application.rest.schemas.output.note_output import NoteResponse, PaginationInfo
from pydantic import BaseModel


class SearchResultResponse(BaseModel):
    """Response model for search operations.

    This model structures the complete search response including
    the found notes, pagination information, and search metadata.

    Attributes:
        notes: List of notes found in the search
        pagination: Pagination information for the search results
        search_timestamp: When the search was performed
        search_query: The original search query used
        search_section: The section that was searched
        total_results: Total number of results found (convenience field)
    """

    notes: List[NoteResponse]
    pagination: PaginationInfo
    search_timestamp: datetime
    search_query: str
    search_section: str
    total_results: int

    @classmethod
    def from_entity(cls, search_result) -> "SearchResultResponse":
        """Convert domain SearchResult to API response SearchResultResponse.

        Args:
            search_result: Domain search result entity.

        Returns:
            SearchResultResponse: Complete search response with metadata.
        """

        return cls(
            notes=[NoteResponse.from_entity(note) for note in search_result.notes],
            pagination=PaginationInfo.from_entity(search_result.pagination),
            search_timestamp=search_result.search_timestamp,
            search_query=search_result.criteria.query or "",
            search_section=search_result.criteria.section.value,
            total_results=search_result.pagination.total_notes,
        )
