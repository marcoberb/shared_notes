"""SQLAlchemy implementation of the note repository.

This module contains the concrete implementation of the NoteRepository
using SQLAlchemy for database operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from domain.entities.note import Note
from domain.entities.tag import TagEntity
from domain.repositories.note_repository import NoteRepository
from infrastructure.models.associations import note_tags
from infrastructure.models.note_orm import NoteORM
from infrastructure.models.note_share_orm import NoteShareORM
from infrastructure.models.tag_orm import TagORM
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SQLAlchemyNoteRepository(NoteRepository):
    """SQLAlchemy implementation of the note repository.

    This class provides concrete implementation for note operations
    using SQLAlchemy ORM and PostgreSQL database.

    NOTE: This repository does not store the session internally.
    Each method receives a fresh session to ensure proper transaction management
    and avoid session leaks.
    """

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
        try:
            # Create ORM object from domain entity
            db_note = NoteORM(
                title=note.title,
                content=note.content,
                owner_id=note.owner_id,
                is_deleted=note.is_deleted,
            )

            # Handle tags - only link existing tags, never create new ones
            for tag in note.tags:
                tag_orm = db_session.query(TagORM).filter(TagORM.id == tag.id).first()
                if tag_orm:
                    db_note.tags.append(tag_orm)

            db_session.add(db_note)
            db_session.commit()
            db_session.refresh(db_note)

            # Convert back to domain entity
            return self._orm_to_domain_entity(db_note)

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to create note: {str(e)}")
            raise

    async def get_note_by_id(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> Optional[Note]:
        """Get a note by ID if user has access to it.

        Args:
            db_session (Session): Database session.
            note_id (UUID): The ID of the note to retrieve.
            user_id (UUID): The ID of the user requesting the note.

        Returns:
            Optional[Note]: The note if found and accessible, None otherwise.

        Raises:
            RepositoryError: If there's an error retrieving the note.
        """
        try:
            logger.info(f"Looking for note {note_id} accessible by user {user_id}")
            note_orm = (
                db_session.query(NoteORM)
                .filter(
                    NoteORM.id == note_id,
                    ~NoteORM.is_deleted,
                    or_(
                        NoteORM.owner_id == user_id,
                        NoteORM.id.in_(
                            db_session.query(NoteShareORM.note_id).filter(
                                NoteShareORM.shared_with_user_id == user_id
                            )
                        ),
                    ),
                )
                .first()
            )

            if not note_orm:
                logger.info(
                    f"Note {note_id} not found or not accessible by user {user_id}"
                )
                return None

            logger.info(f"Found note {note_id} owned by {note_orm.owner_id}")
            return self._orm_to_domain_entity(note_orm)

        except Exception as e:
            logger.error(f"Failed to get note {note_id}: {str(e)}")
            raise

    async def update_note(self, db_session: Session, note: Note) -> Note:
        """Update an existing note in the repository.

        Args:
            db_session (Session): Database session.
            note (Note): The note entity with updated data.

        Returns:
            Note: The updated note entity.

        Raises:
            ValueError: If the note is not found or not accessible.
            RepositoryError: If there's an error updating the note.
        """
        try:
            logger.info(f"Updating note {note.id} for owner {note.owner_id}")
            db_note = (
                db_session.query(NoteORM)
                .filter(
                    NoteORM.id == note.id,
                    NoteORM.owner_id == note.owner_id,
                    ~NoteORM.is_deleted,
                )
                .first()
            )

            if not db_note:
                logger.warning(
                    f"Note {note.id} not found or not accessible for owner {note.owner_id}"
                )
                raise ValueError(f"Note {note.id} not found or not accessible")

            # Update fields
            db_note.title = note.title
            db_note.content = note.content
            db_note.updated_at = datetime.utcnow()

            # Update tags - only link existing tags, never create new ones
            db_note.tags.clear()
            for tag in note.tags:
                tag_orm = db_session.query(TagORM).filter(TagORM.id == tag.id).first()
                if tag_orm:
                    db_note.tags.append(tag_orm)

            logger.info(f"Committing update for note {note.id}")
            db_session.commit()
            db_session.refresh(db_note)

            logger.info(f"Successfully updated note {note.id}")
            return self._orm_to_domain_entity(db_note)

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to update note {note.id}: {str(e)}")
            raise

    async def delete_note(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> bool:
        """Soft delete a note (mark as deleted).

        Args:
            db_session (Session): Database session.
            note_id (UUID): The ID of the note to delete.
            user_id (UUID): The ID of the user who owns the note.

        Returns:
            bool: True if the note was successfully deleted, False if not found.

        Raises:
            RepositoryError: If there's an error deleting the note.
        """
        try:
            db_note = (
                db_session.query(NoteORM)
                .filter(
                    NoteORM.id == note_id,
                    NoteORM.owner_id == user_id,
                    ~NoteORM.is_deleted,
                )
                .first()
            )

            if not db_note:
                return False

            db_note.is_deleted = True
            db_note.updated_at = datetime.utcnow()
            db_session.commit()

            return True

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to delete note {note_id}: {str(e)}")
            raise

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
            db_session (Session): Database session.
            user_id (UUID): The ID of the user whose notes to retrieve.
            page (int): Page number (1-based).
            limit (int): Number of notes per page.
            tag_ids (Optional[List[UUID]]): Optional list of tag IDs to filter by.

        Returns:
            Tuple[List[Note], int]: A tuple containing the list of notes and total count.

        Raises:
            RepositoryError: If there's an error retrieving the notes.
        """
        try:
            offset = (page - 1) * limit

            # Base query for user's notes
            base_query = db_session.query(NoteORM).filter(
                NoteORM.owner_id == user_id, ~NoteORM.is_deleted
            )

            # Add tag filtering if provided
            if tag_ids:
                # tag_ids are already UUID objects, no need to convert to strings
                base_query = (
                    base_query.join(note_tags)
                    .filter(note_tags.c.tag_id.in_(tag_ids))
                    .group_by(NoteORM.id)
                    .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
                )

            # Get total count
            total_count = base_query.count()

            # Get notes for current page
            notes_orm = (
                base_query.order_by(NoteORM.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Convert to domain entities
            notes = [self._orm_to_domain_entity(note_orm) for note_orm in notes_orm]

            return notes, total_count

        except Exception as e:
            logger.error(f"Failed to get user notes for {user_id}: {str(e)}")
            raise

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
            db_session (Session): Database session.
            user_id (UUID): The ID of the user whose private notes to retrieve.
            page (int): Page number (1-based).
            limit (int): Number of notes per page.
            tag_ids (Optional[List[UUID]]): Optional list of tag IDs to filter by.

        Returns:
            Tuple[List[Note], int]: A tuple containing the list of private notes and total count.

        Raises:
            RepositoryError: If there's an error retrieving the notes.
        """
        try:
            offset = (page - 1) * limit

            # Get note IDs that are shared (to exclude them)
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id)
                .filter(NoteShareORM.shared_by_user_id == user_id)
                .subquery()
            )

            # Base query for user's private notes
            base_query = db_session.query(NoteORM).filter(
                NoteORM.owner_id == user_id,
                ~NoteORM.is_deleted,
                ~NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

            # Add tag filtering if provided
            if tag_ids:
                # tag_ids are already UUID objects, no need to convert to strings
                base_query = (
                    base_query.join(note_tags)
                    .filter(note_tags.c.tag_id.in_(tag_ids))
                    .group_by(NoteORM.id)
                    .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
                )

            # Get total count
            total_count = base_query.count()

            # Get notes for current page
            notes_orm = (
                base_query.order_by(NoteORM.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Convert to domain entities
            notes = [self._orm_to_domain_entity(note_orm) for note_orm in notes_orm]

            return notes, total_count

        except Exception as e:
            logger.error(f"Failed to get my notes for {user_id}: {str(e)}")
            raise

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
            db_session (Session): Database session.
            user_id (UUID): The ID of the user who owns the shared notes.
            page (int): Page number (1-based).
            limit (int): Number of notes per page.
            tag_ids (Optional[List[UUID]]): Optional list of tag IDs to filter by.

        Returns:
            Tuple[List[Note], int]: A tuple containing the list of shared notes and total count.

        Raises:
            RepositoryError: If there's an error retrieving the notes.
        """
        try:
            offset = (page - 1) * limit

            # Get notes that are owned by user AND shared
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id)
                .filter(NoteShareORM.shared_by_user_id == user_id)
                .subquery()
            )

            # Base query
            base_query = db_session.query(NoteORM).filter(
                NoteORM.owner_id == user_id,
                ~NoteORM.is_deleted,
                NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

            # Add tag filtering if provided
            if tag_ids:
                # tag_ids are already UUID objects, no need to convert to strings
                base_query = (
                    base_query.join(note_tags)
                    .filter(note_tags.c.tag_id.in_(tag_ids))
                    .group_by(NoteORM.id)
                    .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
                )

            # Get total count
            total_count = base_query.count()

            # Get notes for current page
            notes_orm = (
                base_query.order_by(NoteORM.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Convert to domain entities
            notes = [self._orm_to_domain_entity(note_orm) for note_orm in notes_orm]

            return notes, total_count

        except Exception as e:
            logger.error(f"Failed to get notes shared by {user_id}: {str(e)}")
            raise

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
            db_session (Session): Database session.
            user_id (UUID): The ID of the user with whom notes are shared.
            page (int): Page number (1-based).
            limit (int): Number of notes per page.
            tag_ids (Optional[List[UUID]]): Optional list of tag IDs to filter by.

        Returns:
            Tuple[List[Note], int]: A tuple containing the list of notes shared with the user and total count.

        Raises:
            RepositoryError: If there's an error retrieving the notes.
        """
        try:
            offset = (page - 1) * limit

            # Get notes shared WITH user
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id)
                .filter(NoteShareORM.shared_with_user_id == user_id)
                .subquery()
            )

            # Base query
            base_query = db_session.query(NoteORM).filter(
                ~NoteORM.is_deleted,
                NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

            # Add tag filtering if provided
            if tag_ids:
                # tag_ids are already UUID objects, no need to convert to strings
                base_query = (
                    base_query.join(note_tags)
                    .filter(note_tags.c.tag_id.in_(tag_ids))
                    .group_by(NoteORM.id)
                    .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
                )

            # Get total count
            total_count = base_query.count()

            # Get notes for current page
            notes_orm = (
                base_query.order_by(NoteORM.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            # Convert to domain entities
            notes = [self._orm_to_domain_entity(note_orm) for note_orm in notes_orm]

            return notes, total_count

        except Exception as e:
            logger.error(f"Failed to get notes shared with {user_id}: {str(e)}")
            raise

    async def share_note(
        self,
        db_session: Session,
        note_id: UUID,
        shared_by_user_id: UUID,
        shared_with_user_ids: List[UUID],
    ) -> bool:
        """Share a note with multiple users.

        Args:
            db_session (Session): Database session.
            note_id (UUID): The ID of the note to share.
            shared_by_user_id (UUID): The ID of the user sharing the note.
            shared_with_user_ids (List[UUID]): List of user IDs to share the note with.

        Returns:
            bool: True if the note was successfully shared, False otherwise.

        Raises:
            RepositoryError: If there's an error sharing the note.
        """
        try:
            # Verify note exists and is owned by user
            note_exists = (
                db_session.query(NoteORM)
                .filter(
                    NoteORM.id == note_id,
                    NoteORM.owner_id == shared_by_user_id,
                    ~NoteORM.is_deleted,
                )
                .first()
            )

            if not note_exists:
                return False

            # Create shares for each user
            for shared_with_user_id in shared_with_user_ids:
                # Check if already shared
                existing_share = (
                    db_session.query(NoteShareORM)
                    .filter(
                        NoteShareORM.note_id == note_id,
                        NoteShareORM.shared_with_user_id == shared_with_user_id,
                    )
                    .first()
                )

                if not existing_share:
                    db_share = NoteShareORM(
                        note_id=note_id,
                        shared_by_user_id=shared_by_user_id,
                        shared_with_user_id=shared_with_user_id,
                    )
                    db_session.add(db_share)

            db_session.commit()
            return True

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to share note {note_id}: {str(e)}")
            raise

    async def unshare_note(
        self,
        db_session: Session,
        note_id: UUID,
        shared_by_user_id: UUID,
        shared_with_user_id: UUID,
    ) -> bool:
        """Remove a share from a note."""
        try:
            db_share = (
                db_session.query(NoteShareORM)
                .filter(
                    NoteShareORM.note_id == note_id,
                    NoteShareORM.shared_by_user_id == shared_by_user_id,
                    NoteShareORM.shared_with_user_id == shared_with_user_id,
                )
                .first()
            )

            if not db_share:
                return False

            db_session.delete(db_share)
            db_session.commit()
            return True

        except Exception as e:
            db_session.rollback()
            logger.error(f"Failed to unshare note {note_id}: {str(e)}")
            raise

    async def get_note_shares(
        self, db_session: Session, note_id: UUID, user_id: UUID
    ) -> List[dict]:
        """Get all shares for a note (only for note owner)."""
        try:
            # Verify user owns the note
            note_exists = (
                db_session.query(NoteORM)
                .filter(
                    NoteORM.id == note_id,
                    NoteORM.owner_id == user_id,
                    ~NoteORM.is_deleted,
                )
                .first()
            )

            if not note_exists:
                return []

            # Get all shares
            shares = (
                db_session.query(NoteShareORM)
                .filter(NoteShareORM.note_id == note_id)
                .all()
            )

            # Convert to dict format
            return [
                {
                    "id": str(share.id),
                    "note_id": str(share.note_id),
                    "shared_by_user_id": share.shared_by_user_id,
                    "shared_with_user_id": share.shared_with_user_id,
                    "created_at": share.created_at,
                }
                for share in shares
            ]

        except Exception as e:
            logger.error(f"Failed to get shares for note {note_id}: {str(e)}")
            raise

    def _orm_to_domain_entity(self, note_orm: NoteORM) -> Note:
        """Convert SQLAlchemy ORM object to domain entity."""
        # Convert tags
        tag_entities = []
        for tag_orm in note_orm.tags:
            # tag_orm.id is already a UUID object due to as_uuid=True
            tag_entity = TagEntity(id=tag_orm.id, name=tag_orm.name)
            tag_entities.append(tag_entity)

        return Note(
            id=note_orm.id,
            title=note_orm.title,
            content=note_orm.content,
            owner_id=note_orm.owner_id,
            tags=tag_entities,
            created_at=note_orm.created_at,
            updated_at=note_orm.updated_at,
            is_deleted=note_orm.is_deleted,
            search_vector=note_orm.search_vector,
        )
