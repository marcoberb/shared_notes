"""Share input schemas for API requests.

This module contains Pydantic models for note sharing-related API requests.
"""

from pydantic import BaseModel
from typing import List


class ShareRequest(BaseModel):
    """Schema for sharing a note with other users.
    
    Attributes:
        note_id (str): UUID string of the note to be shared.
        emails (List[str]): List of email addresses to share the note with.
        
    Example:
        >>> share_data = ShareRequest(
        ...     note_id="note-uuid-123",
        ...     emails=["user1@example.com", "user2@example.com"]
        ... )
    """
    note_id: str  # UUID string
    emails: List[str]  # List of email addresses to share with
