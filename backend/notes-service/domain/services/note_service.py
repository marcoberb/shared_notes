"""Note domain service for the shared notes application.

This module contains the NoteService that orchestrates note operations
following Domain-Driven Design principles.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

from domain.entities.note import Note
from domain.entities.search import PaginationMetadata
from domain.entities.tag import TagEntity

if TYPE_CHECKING:
    from domain.repositories.note_repository import NoteRepository
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NoteError(Exception):
    """Base exception for note-related errors."""

    pass


class NoteNotFoundError(NoteError):
    """Exception raised when a note is not found."""

    pass


class NoteAccessDeniedError(NoteError):
    """Exception raised when user doesn't have access to a note."""

    pass


class NoteService:
    """Domain service for handling note operations.

    This service encapsulates the business logic for note management,
    including CRUD operations, sharing, and access control.
    """

    def __init__(self, note_repository: "NoteRepository"):
        """Initialize the note service with dependencies.

        Args:
            note_repository: Repository for performing note operations
        """
        self._note_repository = note_repository

    async def create_note(
        self,
        db_session: "Session",
        title: str,
        content: str,
        owner_id: UUID,
        tag_entities: List[TagEntity],
    ) -> Note:
        """Create a new note with business logic validation.

        Args:
            db_session: Database session for this operation
            title: Note title
            content: Note content
            owner_id: UUID of the note owner
            tag_entities: List of tag entities to associate

        Returns:
            Note: Created note with assigned ID

        Raises:
            ValueError: If title or content are invalid
            NoteError: If creation fails
        """
        logger.info(f"Creating note for user {owner_id} with {len(tag_entities)} tags")

        try:
            # Create note using domain entity factory
            note = Note.from_creation_request(
                title=title,
                content=content,
                owner_id=owner_id,
                tag_entities=tag_entities,
            )

            # Delegate to repository
            created_note = await self._note_repository.create_note(db_session, note)

            logger.info(f"Successfully created note {created_note.id}")
            return created_note

        except ValueError as e:
            logger.warning(f"Invalid note data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create note: {str(e)}")
            raise NoteError(f"Failed to create note: {str(e)}")

    async def get_note(
        self, db_session: "Session", note_id: UUID, user_id: UUID
    ) -> Note:
        """Get a note by ID with access control.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note to retrieve
            user_id: UUID of the user requesting the note

        Returns:
            Note: Retrieved note

        Raises:
            NoteNotFoundError: If note not found or user doesn't have access
        """
        logger.info(f"Getting note {note_id} for user {user_id}")

        try:
            note = await self._note_repository.get_note_by_id(
                db_session, note_id, user_id
            )

            if not note:
                raise NoteNotFoundError(f"Note {note_id} not found or access denied")

            return note

        except NoteNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get note {note_id}: {str(e)}")
            raise NoteError(f"Failed to retrieve note: {str(e)}")

    async def update_note(
        self,
        db_session: "Session",
        note_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tag_entities: Optional[List[TagEntity]] = None,
    ) -> Note:
        """Update an existing note with business logic validation.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note to update
            user_id: UUID of the user attempting the update
            title: New title (optional)
            content: New content (optional)
            tag_entities: New tags (optional)

        Returns:
            Note: Updated note

        Raises:
            NoteNotFoundError: If note not found or user doesn't own it
            ValueError: If update data is invalid
            NoteError: If update fails
        """
        logger.info(f"Updating note {note_id} for user {user_id}")

        try:
            # Get existing note (only owner can update)
            existing_note = await self._note_repository.get_note_by_id(
                db_session, note_id, user_id
            )

            if not existing_note:
                raise NoteNotFoundError(f"Note {note_id} not found")

            if not existing_note.is_owned_by(user_id):
                raise NoteAccessDeniedError("Only note owner can update the note")

            # Apply updates using domain logic
            if title is not None or content is not None:
                existing_note.update_content(
                    title=title if title is not None else existing_note.title,
                    content=content if content is not None else existing_note.content,
                )

            if tag_entities is not None:
                # Replace all tags
                existing_note.tags = tag_entities

            # Delegate to repository
            updated_note = await self._note_repository.update_note(
                db_session, existing_note
            )

            logger.info(f"Successfully updated note {note_id}")
            return updated_note

        except (NoteNotFoundError, NoteAccessDeniedError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Failed to update note {note_id}: {str(e)}")
            raise NoteError(f"Failed to update note: {str(e)}")

    async def delete_note(
        self, db_session: "Session", note_id: UUID, user_id: UUID
    ) -> bool:
        """Delete a note with business logic validation.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note to delete
            user_id: UUID of the user attempting deletion

        Returns:
            bool: True if deletion successful

        Raises:
            NoteNotFoundError: If note not found or user doesn't own it
            NoteError: If deletion fails
        """
        logger.info(f"Deleting note {note_id} for user {user_id}")

        try:
            # Verify ownership before deletion
            existing_note = await self._note_repository.get_note_by_id(
                db_session, note_id, user_id
            )

            if not existing_note:
                raise NoteNotFoundError(f"Note {note_id} not found")

            if not existing_note.is_owned_by(user_id):
                raise NoteAccessDeniedError("Only note owner can delete the note")

            # Delegate to repository
            success = await self._note_repository.delete_note(
                db_session, note_id, user_id
            )

            if success:
                logger.info(f"Successfully deleted note {note_id}")
            else:
                logger.warning(f"Note {note_id} not found for deletion")

            return success

        except (NoteNotFoundError, NoteAccessDeniedError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete note {note_id}: {str(e)}")
            raise NoteError(f"Failed to delete note: {str(e)}")

    async def get_user_notes_paginated(
        self,
        db_session: "Session",
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], PaginationMetadata]:
        """Get paginated list of all user's notes.

        Args:
            db_session: Database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple containing notes and pagination metadata

        Raises:
            ValueError: If pagination parameters are invalid
            NoteError: If retrieval fails
        """
        self._validate_pagination(page, limit)

        try:
            notes, total_count = await self._note_repository.get_user_notes(
                db_session, user_id, page, limit, tag_ids
            )

            pagination = PaginationMetadata.calculate(
                current_page=page, total_notes=total_count, notes_per_page=limit
            )

            logger.info(f"Retrieved {len(notes)} user notes for user {user_id}")
            return notes, pagination

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get user notes: {str(e)}")
            raise NoteError(f"Failed to retrieve user notes: {str(e)}")

    async def get_my_notes_paginated(
        self,
        db_session: "Session",
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], PaginationMetadata]:
        """Get paginated list of user's private notes.

        Args:
            db_session: Database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple containing private notes and pagination metadata

        Raises:
            ValueError: If pagination parameters are invalid
            NoteError: If retrieval fails
        """
        self._validate_pagination(page, limit)

        try:
            notes, total_count = await self._note_repository.get_my_notes(
                db_session, user_id, page, limit, tag_ids
            )

            pagination = PaginationMetadata.calculate(
                current_page=page, total_notes=total_count, notes_per_page=limit
            )

            logger.info(f"Retrieved {len(notes)} private notes for user {user_id}")
            return notes, pagination

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get private notes: {str(e)}")
            raise NoteError(f"Failed to retrieve private notes: {str(e)}")

    async def get_notes_shared_by_me_paginated(
        self,
        db_session: "Session",
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], PaginationMetadata]:
        """Get paginated list of notes shared by user.

        Args:
            db_session: Database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple containing shared notes and pagination metadata

        Raises:
            ValueError: If pagination parameters are invalid
            NoteError: If retrieval fails
        """
        self._validate_pagination(page, limit)

        try:
            notes, total_count = await self._note_repository.get_notes_shared_by_me(
                db_session, user_id, page, limit, tag_ids
            )

            pagination = PaginationMetadata.calculate(
                current_page=page, total_notes=total_count, notes_per_page=limit
            )

            logger.info(f"Retrieved {len(notes)} notes shared by user {user_id}")
            return notes, pagination

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get notes shared by user: {str(e)}")
            raise NoteError(f"Failed to retrieve notes shared by user: {str(e)}")

    async def get_notes_shared_with_me_paginated(
        self,
        db_session: "Session",
        user_id: UUID,
        page: int,
        limit: int,
        tag_ids: Optional[List[UUID]] = None,
    ) -> Tuple[List[Note], PaginationMetadata]:
        """Get paginated list of notes shared with user.

        Args:
            db_session: Database session for this operation
            user_id: UUID of the user
            page: Page number (1-based)
            limit: Number of notes per page
            tag_ids: Optional list of tag UUIDs for filtering

        Returns:
            Tuple containing shared notes and pagination metadata

        Raises:
            ValueError: If pagination parameters are invalid
            NoteError: If retrieval fails
        """
        self._validate_pagination(page, limit)

        try:
            notes, total_count = await self._note_repository.get_notes_shared_with_me(
                db_session, user_id, page, limit, tag_ids
            )

            pagination = PaginationMetadata.calculate(
                current_page=page, total_notes=total_count, notes_per_page=limit
            )

            logger.info(f"Retrieved {len(notes)} notes shared with user {user_id}")
            return notes, pagination

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get notes shared with user: {str(e)}")
            raise NoteError(f"Failed to retrieve notes shared with user: {str(e)}")

    async def share_note_with_users(
        self,
        db_session: "Session",
        note_id: UUID,
        owner_id: UUID,
        shared_with_user_ids: List[UUID],
    ) -> bool:
        """Share a note with multiple users.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note to share
            owner_id: UUID of the note owner
            shared_with_user_ids: List of user UUIDs to share with

        Returns:
            bool: True if sharing successful

        Raises:
            NoteNotFoundError: If note not found or user doesn't own it
            ValueError: If user list is empty
            NoteError: If sharing fails
        """
        if not shared_with_user_ids:
            raise ValueError("Must specify at least one user to share with")

        logger.info(f"Sharing note {note_id} with {len(shared_with_user_ids)} users")

        try:
            # Verify ownership
            note = await self._note_repository.get_note_by_id(
                db_session, note_id, owner_id
            )

            if not note:
                raise NoteNotFoundError(f"Note {note_id} not found")

            if not note.is_owned_by(owner_id):
                raise NoteAccessDeniedError("Only note owner can share the note")

            # Delegate to repository
            success = await self._note_repository.share_note(
                db_session, note_id, owner_id, shared_with_user_ids
            )

            if success:
                logger.info(f"Successfully shared note {note_id}")

            return success

        except (NoteNotFoundError, NoteAccessDeniedError, ValueError):
            raise
        except Exception as e:
            logger.error(f"Failed to share note {note_id}: {str(e)}")
            raise NoteError(f"Failed to share note: {str(e)}")

    async def unshare_note_with_user(
        self,
        db_session: "Session",
        note_id: UUID,
        owner_id: UUID,
        shared_with_user_id: UUID,
    ) -> bool:
        """Remove a user from note sharing.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note
            owner_id: UUID of the note owner
            shared_with_user_id: UUID of the user to remove from sharing

        Returns:
            bool: True if unsharing successful

        Raises:
            NoteNotFoundError: If note not found or user doesn't own it
            NoteError: If unsharing fails
        """
        logger.info(f"Unsharing note {note_id} with user {shared_with_user_id}")

        try:
            # Verify ownership
            note = await self._note_repository.get_note_by_id(
                db_session, note_id, owner_id
            )

            if not note:
                raise NoteNotFoundError(f"Note {note_id} not found")

            if not note.is_owned_by(owner_id):
                raise NoteAccessDeniedError("Only note owner can unshare the note")

            # Delegate to repository
            success = await self._note_repository.unshare_note(
                db_session, note_id, owner_id, shared_with_user_id
            )

            if success:
                logger.info(f"Successfully unshared note {note_id}")

            return success

        except (NoteNotFoundError, NoteAccessDeniedError):
            raise
        except Exception as e:
            logger.error(f"Failed to unshare note {note_id}: {str(e)}")
            raise NoteError(f"Failed to unshare note: {str(e)}")

    async def get_note_shares(
        self, db_session: "Session", note_id: UUID, user_id: UUID
    ) -> List[dict]:
        """Get all shares for a note.

        Args:
            db_session: Database session for this operation
            note_id: UUID of the note
            user_id: UUID of the user (must be note owner)

        Returns:
            List of share information

        Raises:
            NoteNotFoundError: If note not found or user doesn't own it
            NoteError: If retrieval fails
        """
        logger.info(f"Getting shares for note {note_id}")

        try:
            # Verify ownership is handled by repository
            shares = await self._note_repository.get_note_shares(
                db_session, note_id, user_id
            )

            logger.info(f"Retrieved {len(shares)} shares for note {note_id}")
            return shares

        except Exception as e:
            logger.error(f"Failed to get note shares: {str(e)}")
            raise NoteError(f"Failed to retrieve note shares: {str(e)}")

    def _validate_pagination(self, page: int, limit: int) -> None:
        """Validate pagination parameters.

        Args:
            page: Page number
            limit: Items per page

        Raises:
            ValueError: If parameters are invalid
        """
        if page < 1:
            raise ValueError("Page number must be at least 1")
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
