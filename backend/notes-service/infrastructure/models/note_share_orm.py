"""SQLAlchemy ORM model for NoteShare entity.

This module contains the NoteShareORM class that defines the database schema
for note sharing relationships and handles note sharing data persistence.

Classes:
    NoteShareORM: SQLAlchemy model for note sharing between users.

Architecture:
    This ORM model is part of the Infrastructure layer and should only be used by:
    - SqlAlchemyNoteShareRepository implementation
    - Database migration scripts
    - Other infrastructure-specific code

    Domain code should use NoteShareEntity instead of this ORM model.
"""

import uuid
from datetime import datetime

from infrastructure.models.base import Base
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class NoteShareORM(Base):
    """SQLAlchemy ORM model for note sharing between users.

    This model represents the database schema for note sharing relationships
    and provides SQLAlchemy ORM capabilities for data persistence operations.

    Attributes:
        id (UUID): Primary key, auto-generated UUID.
        note_id (UUID): Foreign key to the shared note.
        shared_by_user_id (str): Keycloak UUID of user who shared the note.
        shared_with_user_id (str): Keycloak UUID of user who receives the share.
        created_at (datetime): Timestamp when share was created.
        note (NoteORM): Many-to-one relationship to the shared note.

    Table Schema:
        - Table name: 'note_shares'
        - Primary key: id (UUID)
        - Foreign key: note_id -> notes.id
        - Indexes: id (primary key index)

    Relationships:
        - note: Many-to-one with NoteORM (creates backref 'shares' on NoteORM)

    Example:
        >>> share_orm = NoteShareORM(
        ...     note_id=note.id,
        ...     shared_by_user_id="owner-uuid",
        ...     shared_with_user_id="recipient-uuid"
        ... )
        >>> db.add(share_orm)
        >>> db.commit()
        >>> print(f"Created share: {share_orm.id}")

    Note:
        This is an infrastructure-level ORM model. Domain logic should use
        NoteShareEntity instead. Use NoteShareConverter to transform between them.
    """

    __tablename__ = "note_shares"

    # Primary key with auto-generated UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key, auto-generated UUID",
    )

    # Foreign key to the shared note
    note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id"),
        nullable=False,
        comment="Foreign key to the shared note",
    )

    # User who shared the note (Keycloak UUID)
    shared_by_user_id = Column(
        String(255), nullable=False, comment="Keycloak UUID of user who shared the note"
    )

    # User who receives the share (Keycloak UUID)
    shared_with_user_id = Column(
        String(255),
        nullable=False,
        comment="Keycloak UUID of user who receives the share",
    )

    # Creation timestamp
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp when share was created",
    )

    # Many-to-one relationship with note
    # This creates a backref 'shares' on NoteORM automatically
    note = relationship("NoteORM", backref="shares", lazy="select")

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: Human-readable representation of the note share.
        """
        return (
            f"<NoteShareORM(id={self.id}, note_id={self.note_id}, "
            f"shared_by={self.shared_by_user_id}, shared_with={self.shared_with_user_id})>"
        )

    def __str__(self) -> str:
        """User-friendly string representation.

        Returns:
            str: Share description for display purposes.
        """
        return f"Share of note {self.note_id} from {self.shared_by_user_id} to {self.shared_with_user_id}"
