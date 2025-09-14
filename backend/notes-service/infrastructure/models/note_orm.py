"""SQLAlchemy ORM model for Note entity.

This module contains the NoteORM class that defines the database schema
for notes and handles note data persistence.

Classes:
    NoteORM: SQLAlchemy model for notes with content, metadata, and relationships.

Architecture:
    This ORM model is part of the Infrastructure layer and should only be used by:
    - SqlAlchemyNoteRepository implementation
    - Database migration scripts
    - Other infrastructure-specific code

    Domain code should use NoteEntity instead of this ORM model.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from infrastructure.models.base import Base


class NoteORM(Base):
    """SQLAlchemy ORM model for notes with tags and sharing capabilities.

    This model represents the database schema for notes and provides
    SQLAlchemy ORM capabilities for data persistence operations.

    Attributes:
        id (UUID): Primary key, auto-generated UUID.
        title (str): Note title, max 255 characters.
        content (str): Note content, unlimited text.
        owner_id (str): Keycloak user UUID who owns the note.
        created_at (datetime): Timestamp when note was created.
        updated_at (datetime): Timestamp when note was last updated.
        is_deleted (bool): Soft delete flag, defaults to False.
        search_vector (str): PostgreSQL tsvector for full-text search.
        tags (List[TagORM]): Many-to-many relationship with tags.
        shares (List[NoteShareORM]): One-to-many relationship with note shares.

    Table Schema:
        - Table name: 'notes'
        - Primary key: id (UUID)
        - Indexes: id (primary key index)

    Relationships:
        - tags: Many-to-many with TagORM through note_tags association table
        - shares: One-to-many with NoteShareORM (backref from NoteShareORM)

    Example:
        >>> note_orm = NoteORM(title="Work Note", content="Important task", owner_id="user-uuid")
        >>> db.add(note_orm)
        >>> db.commit()
        >>> print(f"Created note: {note_orm.id}")

    Note:
        This is an infrastructure-level ORM model. Domain logic should use
        NoteEntity instead. Use NoteConverter to transform between them.
    """

    __tablename__ = "notes"

    # Primary key with auto-generated UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key, auto-generated UUID",
    )

    # Note title
    title = Column(
        String(255), nullable=False, comment="Note title, max 255 characters"
    )

    # Note content
    content = Column(Text, nullable=False, comment="Note content, unlimited text")

    # Owner identification (Keycloak user ID)
    owner_id = Column(
        String(255), nullable=False, comment="Keycloak user UUID who owns the note"
    )

    # Timestamps
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp when note was created",
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Timestamp when note was last updated",
    )

    # Soft delete flag
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Soft delete flag, defaults to False",
    )

    # Full-text search support
    search_vector = Column(Text, comment="PostgreSQL tsvector for full-text search")

    # Many-to-many relationship with tags
    # Import is deferred to avoid circular import issues
    tags = relationship(
        "TagORM", secondary="note_tags", back_populates="notes", lazy="select"
    )

    # Note: shares relationship is defined as backref in NoteShareORM
    # to avoid circular imports. It will be available as self.shares

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: Human-readable representation of the note.
        """
        return (
            f"<NoteORM(id={self.id}, title='{self.title}', owner_id='{self.owner_id}')>"
        )

    def __str__(self) -> str:
        """User-friendly string representation.

        Returns:
            str: Note title for display purposes.
        """
        return self.title
