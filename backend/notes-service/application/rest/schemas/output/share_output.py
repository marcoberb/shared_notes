"""Share output schemas for API responses.

This module contains Pydantic models for share-related API responses.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import List


class ShareResponse(BaseModel):
    """Schema for share data in API responses.
    
    Attributes:
        id (str): UUID string identifier of the share.
        note_id (str): UUID string of the shared note.
        shared_by_user_id (str): Keycloak UUID of the user who shared the note.
        shared_with_user_id (str): Keycloak UUID of the user who received the share.
        shared_with_email (str): Email address of the user who received the share.
        created_at (datetime): Timestamp when the share was created.
        
    Example:
        >>> share_response = ShareResponse(
        ...     id="share-uuid-123",
        ...     note_id="note-uuid-456",
        ...     shared_by_user_id="owner-uuid",
        ...     shared_with_user_id="recipient-uuid",
        ...     shared_with_email="recipient@example.com",
        ...     created_at=datetime.now()
        ... )
    """
    id: str  # UUID string
    note_id: str  # UUID string
    shared_by_user_id: str
    shared_with_user_id: str
    shared_with_email: str  # We'll fetch this from Keycloak when returning
    created_at: datetime


class NoteSharesResponse(BaseModel):
    """Schema for note shares list API responses.
    
    Attributes:
        note_id (str): UUID string of the note.
        shares (List[ShareResponse]): List of shares for the note.
        
    Example:
        >>> note_shares = NoteSharesResponse(
        ...     note_id="note-uuid-123",
        ...     shares=[share1, share2, share3]
        ... )
    """
    note_id: str  # UUID string
    shares: List[ShareResponse]
