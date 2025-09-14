"""Share output schemas for API responses.

This module contains Pydantic models for share-related API responses.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel


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
    shared_with_email: str
    created_at: datetime

    @classmethod
    def from_share_data(cls, share_data: dict) -> "ShareResponse":
        """Create ShareResponse from repository share data.

        Args:
            share_data: Dictionary from repository with share information

        Returns:
            ShareResponse: The converted share response schema
        """
        return cls(
            id=str(share_data["id"]),
            note_id=str(share_data["note_id"]),
            shared_by_user_id=str(share_data["shared_by_user_id"]),
            shared_with_user_id=str(share_data["shared_with_user_id"]),
            shared_with_email=share_data.get("shared_with_email", ""),
            created_at=share_data["created_at"],
        )


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

    @classmethod
    def from_shares_data(
        cls, note_id: str, shares_data: List[dict]
    ) -> "NoteSharesResponse":
        """Create NoteSharesResponse from repository shares data.

        Args:
            note_id: UUID string of the note
            shares_data: List of share dictionaries from repository

        Returns:
            NoteSharesResponse: The converted note shares response schema
        """
        return cls(
            note_id=note_id,
            shares=[ShareResponse.from_share_data(share) for share in shares_data],
        )
