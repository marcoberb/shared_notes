"""Search output schemas for the shared notes application.

This module contains Pydantic models for search response output serialization.
"""

from datetime import datetime
from typing import List

from note_output import NoteResponse, NotesListResponse
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
    pagination: dict  # PaginationInfo from note_output
    search_timestamp: datetime
    search_query: str
    search_section: str
    total_results: int

    class Config:
        """Pydantic model configuration."""

        schema_extra = {
            "example": {
                "notes": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Work Meeting Notes",
                        "content": "Discussed project timeline and deliverables",
                        "owner_id": "user123",
                        "tags": [
                            {"id": "tag1", "name": "work"},
                            {"id": "tag2", "name": "meeting"},
                        ],
                        "created_at": "2024-01-01T10:00:00Z",
                        "updated_at": "2024-01-01T11:00:00Z",
                    }
                ],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 3,
                    "total_notes": 42,
                    "notes_per_page": 15,
                    "has_next": True,
                    "has_previous": False,
                },
                "search_timestamp": "2024-01-01T12:00:00Z",
                "search_query": "work meeting",
                "search_section": "my-notes",
                "total_results": 42,
            }
        }


# For compatibility, we can also expose the existing NotesListResponse
__all__ = ["SearchResultResponse", "NotesListResponse"]
