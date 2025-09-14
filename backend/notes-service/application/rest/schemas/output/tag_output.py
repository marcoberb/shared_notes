"""Tag output schemas for API responses.

This module contains Pydantic models for tag-related API responses.
"""

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
