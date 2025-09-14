"""Tag output schemas for API responses.

This module contains Pydantic models for tag-related API responses.
"""

from __future__ import annotations

from domain.entities.tag import TagEntity
from pydantic import BaseModel


class TagResponse(BaseModel):
    """Schema for tag data in API responses.

    Attributes:
        id (str): UUID string identifier of the tag.
        name (str): The name of the tag.

    Example:
        >>> tag_response = TagResponse(id="tag-uuid-123", name="work")
    """

    id: str  # UUID as string
    name: str

    @classmethod
    def from_entity(cls, tag_entity: TagEntity) -> TagResponse:
        """Create TagResponse from TagEntity.

        Args:
            tag_entity (TagEntity): The domain entity to convert.

        Returns:
            TagResponse: The converted tag response schema.
        """
        if tag_entity.is_new():
            raise ValueError("Cannot convert new tag entity to response (no ID)")
        return cls(id=str(tag_entity.id), name=tag_entity.name)
