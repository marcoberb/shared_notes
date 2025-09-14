"""Note domain entity for the shared notes application.

This module contains the core Note domain entity representing
a note in the system following Domain-Driven Design principles.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

if TYPE_CHECKING:
    from domain.entities.tag import TagEntity


@dataclass
class Note:
    """Domain entity representing a note in the shared notes system.

    This entity encapsulates all the business logic and rules related to notes,
    following Domain-Driven Design principles.

    Attributes:
        id (UUID): Unique identifier for the note.
        title (str): Title of the note.
        content (str): Content/body of the note.
        owner_id (UUID): UUID of the user who owns the note.
        tags (List[TagEntity]): List of tags associated with the note.
        created_at (datetime): Timestamp when the note was created.
        updated_at (datetime): Timestamp when the note was last updated.
        is_deleted (bool): Whether the note is soft deleted.
        search_vector (Optional[str]): Full-text search vector (handled by infrastructure).
    """

    id: UUID
    title: str
    content: str
    owner_id: UUID
    tags: List["TagEntity"]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False
    search_vector: Optional[str] = None  # Handled by infrastructure layer

    def __post_init__(self):
        """Validate note after initialization.

        Raises:
            ValueError: If note title or content are empty.
        """
        if not self.title.strip():
            raise ValueError("Note title cannot be empty")
        if not self.content.strip():
            raise ValueError("Note content cannot be empty")

    @classmethod
    def create_new(
        cls,
        title: str,
        content: str,
        owner_id: UUID,
        tags: Optional[List["TagEntity"]] = None,
    ) -> "Note":
        """Factory method to create a new note with default values.

        Args:
            title (str): Title of the note.
            content (str): Content of the note.
            owner_id (UUID): UUID of the note owner.
            tags (Optional[List[TagEntity]]): Optional list of tags.

        Returns:
            Note: New note instance with generated UUID and timestamps.

        Raises:
            ValueError: If title or content are empty.
        """
        from uuid import uuid4

        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            title=title.strip(),
            content=content.strip(),
            owner_id=owner_id,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            is_deleted=False,
        )

    @classmethod
    def from_creation_request(
        cls, title: str, content: str, owner_id: UUID, tag_entities: List["TagEntity"]
    ) -> "Note":
        """Factory method to create a note from API creation request.

        Args:
            title (str): Note title from request.
            content (str): Note content from request.
            owner_id (UUID): UUID of the user creating the note.
            tag_entities (List[TagEntity]): List of tag entities to associate.

        Returns:
            Note: New note instance ready for persistence.

        Raises:
            ValueError: If title or content are invalid.
        """
        return cls.create_new(
            title=title, content=content, owner_id=owner_id, tags=tag_entities
        )

    def update_content(self, title: str, content: str) -> None:
        """Update the note's title and content.

        Args:
            title (str): New title for the note.
            content (str): New content for the note.

        Raises:
            ValueError: If title or content are empty.
        """
        if not title.strip():
            raise ValueError("Note title cannot be empty")
        if not content.strip():
            raise ValueError("Note content cannot be empty")

        self.title = title.strip()
        self.content = content.strip()
        self.updated_at = datetime.utcnow()

    def add_tag(self, tag: "TagEntity") -> None:
        """Add a tag to the note if not already present.

        Args:
            tag (TagEntity): The tag to add to the note.
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag: "TagEntity") -> None:
        """Remove a tag from the note if present.

        Args:
            tag (TagEntity): The tag to remove from the note.
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.utcnow()

    def soft_delete(self) -> None:
        """Soft delete the note."""
        self.is_deleted = True
        self.updated_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft deleted note."""
        self.is_deleted = False
        self.updated_at = datetime.utcnow()

    def is_owned_by(self, user_id: UUID) -> bool:
        """Check if the note is owned by the specified user.

        Args:
            user_id (UUID): UUID of the user to check ownership for.

        Returns:
            bool: True if the user owns the note, False otherwise.
        """
        return self.owner_id == user_id

    def has_tag(self, tag_id: UUID) -> bool:
        """Check if the note has a specific tag.

        Args:
            tag_id (UUID): UUID of the tag to check for.

        Returns:
            bool: True if the note has the tag, False otherwise.
        """
        return any(tag.id == tag_id for tag in self.tags)

    def has_all_tags(self, tag_ids: List[UUID]) -> bool:
        """Check if the note has all the specified tags.

        Args:
            tag_ids (List[UUID]): List of tag UUIDs to check for.

        Returns:
            bool: True if the note has all specified tags, False otherwise.
        """
        note_tag_ids = {tag.id for tag in self.tags}
        required_tag_ids = set(tag_ids)
        return required_tag_ids.issubset(note_tag_ids)

    def matches_text_search(self, query: str) -> bool:
        """Check if the note matches a text search query.

        This is a simple implementation that checks if the query
        appears in the title or content. The actual full-text search
        is handled by the infrastructure layer.

        Args:
            query (str): The search query string.

        Returns:
            bool: True if the note matches the query, False otherwise.
        """
        if not query.strip():
            return True

        query_lower = query.lower().strip()
        return query_lower in self.title.lower() or query_lower in self.content.lower()
