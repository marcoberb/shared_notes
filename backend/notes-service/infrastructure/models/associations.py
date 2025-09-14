"""Association tables for many-to-many relationships in SQLAlchemy ORM.

This module defines the association tables that are used to create many-to-many
relationships between entities in the database.

Tables:
    note_tags: Associates notes with tags (many-to-many relationship)

Architecture:
    These association tables are part of the Infrastructure layer and are used
    by SQLAlchemy to manage many-to-many relationships automatically.
"""

from infrastructure.models.base import Base
from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", UUID(as_uuid=True), ForeignKey("notes.id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True),
    comment="Association table for many-to-many relationship between notes and tags",
)
