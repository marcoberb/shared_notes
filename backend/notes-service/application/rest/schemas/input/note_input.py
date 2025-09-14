"""Note input schemas for API requests.

This module contains Pydantic models for note-related API requests,
including note creation and update operations.
"""

from pydantic import BaseModel
from typing import List, Optional


class NoteCreate(BaseModel):
    """Schema for creating a new note.
    
    Attributes:
        title (str): The title of the note.
        content (str): The content/body of the note.
        tags (List[str], optional): List of tag UUID strings to associate with the note.
        share_emails (List[str], optional): List of email addresses to share the note with during creation.
        
    Example:
        >>> note_data = NoteCreate(
        ...     title="Meeting Notes", 
        ...     content="Important discussion points",
        ...     tags=["tag-uuid-1", "tag-uuid-2"],
        ...     share_emails=["colleague@example.com"]
        ... )
    """
    title: str
    content: str
    tags: Optional[List[str]] = []  # UUID strings
    share_emails: Optional[List[str]] = []  # Emails to share with during creation


class NoteUpdate(BaseModel):
    """Schema for updating an existing note.
    
    All fields are optional for partial updates. Only provided fields will be updated.
    
    Attributes:
        title (str, optional): New title for the note.
        content (str, optional): New content for the note.
        tags (List[str], optional): New list of tag UUID strings to replace existing tags.
        
    Example:
        >>> update_data = NoteUpdate(title="Updated Title", tags=["new-tag-uuid"])
    """
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None  # UUID strings
