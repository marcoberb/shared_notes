"""Tag input schemas for API requests.

This module contains Pydantic models for tag-related API requests,
including tag creation and update operations.
"""

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Schema for creating a new tag.

    Attributes:
        name (str): The name of the tag to create. Must be non-empty and trimmed.

    Example:
        >>> tag_data = TagCreate(name="work")
        >>> print(tag_data.name)
        "work"
    """

    name: str = Field(..., min_length=1, strip_whitespace=True, description="Tag name")


class TagUpdate(BaseModel):
    """Schema for updating an existing tag.

    Attributes:
        name (str): The new name for the tag. Must be non-empty and trimmed.

    Example:
        >>> tag_update = TagUpdate(name="important")
        >>> print(tag_update.name)
        "important"
    """

    name: str = Field(
        ..., min_length=1, strip_whitespace=True, description="New tag name"
    )
