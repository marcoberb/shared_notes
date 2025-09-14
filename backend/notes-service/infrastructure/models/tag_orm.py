"""SQLAlchemy ORM model for Tag entity.

This module contains the TagORM class that defines the database schema
for tags and handles tag data persistence.

Classes:
    TagORM: SQLAlchemy model for note tags with validation and relationships.

Architecture:
    This ORM model is part of the Infrastructure layer and should only be used by:
    - SqlAlchemyTagRepository implementation
    - Database migration scripts
    - Other infrastructure-specific code

    Domain code should use TagEntity instead of this ORM model.
"""

import uuid
from datetime import datetime

from infrastructure.models.base import Base
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class TagORM(Base):
    """SQLAlchemy ORM model for tags that categorize notes.

    This model represents the database schema for tags and provides
    SQLAlchemy ORM capabilities for data persistence operations.

    Attributes:
        id (UUID): Primary key, auto-generated UUID.
        name (str): Tag name, max 50 characters, unique across all tags.
        created_at (datetime): Timestamp when tag was created.
        notes (List[NoteORM]): Many-to-many relationship with notes.

    Table Schema:
        - Table name: 'tags'
        - Primary key: id (UUID)
        - Unique constraint: name
        - Indexes: id (primary key index), name (unique index)

    Relationships:
        - notes: Many-to-many with NoteORM through note_tags association table

    Example:
        >>> tag_orm = TagORM(name="work")
        >>> db.add(tag_orm)
        >>> db.commit()
        >>> print(f"Created tag: {tag_orm.id}")

    Note:
        This is an infrastructure-level ORM model. Domain logic should use
        TagEntity instead. Use TagConverter to transform between them.
    """

    __tablename__ = "tags"

    # Primary key with auto-generated UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary key, auto-generated UUID",
    )

    # Tag name with uniqueness constraint
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        comment="Tag name, must be unique across all tags",
    )

    # Creation timestamp
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp when tag was created",
    )

    # Many-to-many relationship with notes
    # Import is deferred to avoid circular import issues
    notes = relationship(
        "NoteORM", secondary="note_tags", back_populates="tags", lazy="select"
    )

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: Human-readable representation of the tag.
        """
        return f"<TagORM(id={self.id}, name='{self.name}')>"

    def __str__(self) -> str:
        """User-friendly string representation.

        Returns:
            str: Tag name for display purposes.
        """
        return self.name
