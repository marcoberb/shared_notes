"""Search input schemas for the shared notes application.

This module contains Pydantic models for search request input validation.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class SearchNotesRequest(BaseModel):
    """Pydantic model for search notes request input.

    This model validates and structures the input for search operations,
    ensuring all required fields are present and properly formatted.

    Attributes:
        q: Search query string for full-text search (optional)
        tags: Comma-separated tag IDs for filtering (optional)
        section: Section to search in (my-notes, shared-by-me, shared-with-me)
        page: Page number for pagination (1-based)
        limit: Number of results per page
    """

    q: Optional[str] = Field(
        default="", description="Search query string for full-text search"
    )

    tags: Optional[str] = Field(
        default=None, description="Comma-separated tag UUIDs for filtering"
    )

    section: str = Field(default="my-notes", description="Section to search in")

    page: int = Field(
        default=1, ge=1, description="Page number for pagination (1-based)"
    )

    limit: int = Field(
        default=15, ge=1, le=100, description="Number of results per page"
    )

    @validator("section")
    def validate_section(cls, v):
        """Validate the section parameter."""
        allowed_sections = {"my-notes", "shared-by-me", "shared-with-me"}
        if v not in allowed_sections:
            raise ValueError(f'Section must be one of: {", ".join(allowed_sections)}')
        return v

    @validator("q")
    def validate_query(cls, v):
        """Validate and normalize the search query."""
        if v is None:
            return ""
        return v.strip()

    def get_tag_ids(self) -> Optional[List[UUID]]:
        """Parse and return tag IDs from the tags string.

        Returns:
            List of UUID objects parsed from the tags string, or None if no tags

        Raises:
            ValueError: If any tag ID is not a valid UUID format
        """
        if not self.tags:
            return None

        try:
            return [
                UUID(tag_id.strip())
                for tag_id in self.tags.split(",")
                if tag_id.strip()
            ]
        except ValueError as e:
            raise ValueError(f"Invalid UUID format for tag IDs: {str(e)}")

    def has_search_criteria(self) -> bool:
        """Check if the request has any search criteria.

        Returns:
            True if either query or tags are provided, False otherwise
        """
        return bool(self.q and self.q.strip()) or bool(self.tags)
