"""Note repository interface for the shared notes application.

This module defines the repository interface for note operations
following Domain-Driven Design principles.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

if TYPE_CHECKING:
    from domain.entities.note import Note
    from sqlalchemy.orm import Session


class NoteRepository(ABC):
    """Abstract repository interface for note operations.

    This interface defines the contract for note repositories,
    allowing different implementations (e.g., SQLAlchemy, MongoDB, etc.)
    while keeping the domain layer independent of infrastructure concerns.
    """

    @abstractmethod
    async def create_note(self, db_session: Session, note: Note) -> Note:
        """Create a new note in the repository.

        Args:
            db_session (Session): SQLAlchemy database session for this operation
            note (Note): Domain Note entity to create

        Returns:
            Note: Created note with assigned ID and timestamps

        Raises:
            RepositoryError: If creation fails at the data layer
        """
        pass

    @abstractmethod
    async def get_note_by_id(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> Optional[Note]:
        """Get a note by ID if user has access to it.

        Args:
            db_session (Session): SQLAlchemy database session for this operation
            note_id (UUID): UUID of the note to retrieve
            user_id (UUID): UUID of the user requesting the note

        Returns:
            Optional[Note]: Note if found and accessible, None otherwise

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass

    @abstractmethod
    async def update_note(self, db_session: Session, note: Note) -> Note:
        """Update an existing note in the repository.

        Args:
            db_session: SQLAlchemy database session for this operation
            note: Domain Note entity with updates

        Returns:
            Note: Updated note with new timestamp

        Raises:
            RepositoryError: If update fails at the data layer
        """
        pass

    @abstractmethod
    async def delete_note(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> bool:
        """Soft delete a note (mark as deleted).

        Args:
            db_session: SQLAlchemy database session for this operation
            note_id: UUID of the note to delete
            user_id: UUID of the user attempting deletion

        Returns:
            bool: True if deletion successful, False if note not found

        Raises:
            RepositoryError: If deletion fails at the data layer
        """
        pass

    @abstractmethod
    async def get_user_notes(
        self,
        db_session: Session,
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], int]:
        """Get paginated list of all user's notes.

        Args:
            db_session: SQLAlchemy database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple[List[Note], int]: Notes and total count

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass

    @abstractmethod
    async def get_my_notes(
        self,
        db_session: Session,
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], int]:
        """Get user's private notes (not shared with others).

        Args:
            db_session: SQLAlchemy database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple[List[Note], int]: Private notes and total count

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass

    @abstractmethod
    async def get_notes_shared_by_me(
        self,
        db_session: Session,
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], int]:
        """Get notes owned by user that are shared with others.

        Args:
            db_session: SQLAlchemy database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple[List[Note], int]: Shared notes and total count

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass

    @abstractmethod
    async def get_notes_shared_with_me(
        self,
        db_session: Session,
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], int]:
        """Get notes shared with the user (not owned by them).

        Args:
            db_session: SQLAlchemy database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple[List[Note], int]: Shared notes and total count

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass

    @abstractmethod
    async def share_note(
        self,
        db_session: Session,
        note_id: UUID,
        shared_by_user_id: UUID,
        shared_with_user_ids: List[UUID],
    ) -> bool:
        """Share a note with multiple users.

        Args:
            db_session: SQLAlchemy database session for this operation
            note_id: UUID of the note to share
            shared_by_user_id: UUID of the user sharing the note
            shared_with_user_ids: List of user UUIDs to share with

        Returns:
            bool: True if sharing successful

        Raises:
            RepositoryError: If sharing fails at the data layer
        """
        pass

    @abstractmethod
    async def unshare_note(
        self,
        db_session: Session,
        note_id: UUID,
        shared_by_user_id: UUID,
        shared_with_user_id: UUID,
    ) -> bool:
        """Remove a share from a note.

        Args:
            db_session: SQLAlchemy database session for this operation
            note_id: UUID of the note
            shared_by_user_id: UUID of the user who shared the note
            shared_with_user_id: UUID of the user to remove from sharing

        Returns:
            bool: True if unsharing successful

        Raises:
            RepositoryError: If unsharing fails at the data layer
        """
        pass

    @abstractmethod
    async def get_note_shares(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> List[dict]:
        """Get all shares for a note (only for note owner).

        Args:
            db_session: SQLAlchemy database session for this operation
            note_id: UUID of the note
            user_id: UUID of the user (must be note owner)

        Returns:
            List[dict]: List of share information

        Raises:
            RepositoryError: If retrieval fails at the data layer
        """
        pass
