"""SQLAlchemy implementation of the search repository.

This module contains the concrete implementation of the SearchRepository
using SQLAlchemy for database operations.
"""

import logging
from typing import List, Tuple
from uuid import UUID

from domain.entities.note import Note
from domain.entities.search import SearchCriteria, SearchSection
from domain.entities.tag import TagEntity
from domain.repositories.search_repository import SearchRepository
from infrastructure.models.associations import note_tags
from infrastructure.models.note_orm import NoteORM
from infrastructure.models.note_share_orm import NoteShareORM
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SQLAlchemySearchRepository(SearchRepository):
    """SQLAlchemy implementation of the search repository.

    This class provides concrete implementation for search operations
    using SQLAlchemy ORM and PostgreSQL database.

    NOTE: This repository does not store the session internally.
    Each method receives a fresh session to ensure proper transaction management
    and avoid session leaks.
    """

    async def search_notes(
        self, db_session: Session, criteria: SearchCriteria
    ) -> Tuple[List[Note], int]:
        """Search for notes based on the provided criteria.

        This method implements the actual search logic using SQLAlchemy
        and converts ORM objects to domain entities.

        Args:
            db_session (Session): SQLAlchemy database session for this operation.
            criteria (SearchCriteria): The search criteria containing all search parameters.

        Returns:
            Tuple[List[Note], int]: A tuple containing:
                - List of Note domain entities matching the criteria
                - Total count of notes matching the criteria

        Raises:
            Exception: If search operation fails at the database level.
        """
        try:
            # Build base query based on section
            base_query = self._build_section_query(db_session, criteria)

            # Apply tag filtering if provided
            if criteria.has_tag_filter():
                base_query = self._apply_tag_filter(
                    db_session, base_query, criteria.tag_ids
                )

            # Apply text search if provided
            if criteria.has_text_search():
                base_query = self._apply_text_search(base_query, criteria.query)

            # Get total count for pagination (before applying limit/offset)
            count_query = base_query
            if criteria.has_tag_filter():
                # For count with tag filtering, we need to count distinct notes
                total_count = count_query.with_entities(
                    func.count(distinct(NoteORM.id))
                ).scalar()
            else:
                total_count = count_query.count()

            # Apply pagination and ordering
            note_orms = (
                base_query.order_by(NoteORM.updated_at.desc())
                .offset(criteria.offset)
                .limit(criteria.limit)
                .all()
            )

            # Convert ORM objects to domain entities
            notes = [self._convert_orm_to_domain(note_orm) for note_orm in note_orms]

            logger.info(
                f"Search completed: found {len(notes)} notes out of {total_count} total "
                f"for user {criteria.user_id} in section {criteria.section.value}"
            )

            return notes, total_count

        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}")
            raise

    def _build_section_query(self, db_session: Session, criteria: SearchCriteria):
        """Build the base query based on the search section.

        Args:
            db_session: SQLAlchemy database session
            criteria: Search criteria containing section information

        Returns:
            SQLAlchemy query object for the specified section
        """
        if criteria.section == SearchSection.MY_NOTES:
            # Get notes shared by user (exclude these from personal notes)
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id).filter(
                    NoteShareORM.shared_by_user_id == criteria.user_id
                )
            ).subquery()

            # Query only personal notes (not shared by user)
            return db_session.query(NoteORM).filter(
                NoteORM.owner_id == criteria.user_id,
                ~NoteORM.is_deleted,
                ~NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

        elif criteria.section == SearchSection.SHARED_BY_ME:
            # Get notes that are owned by user AND shared
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id)
                .filter(NoteShareORM.shared_by_user_id == criteria.user_id)
                .subquery()
            )

            return db_session.query(NoteORM).filter(
                NoteORM.owner_id == criteria.user_id,
                ~NoteORM.is_deleted,
                NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

        elif criteria.section == SearchSection.SHARED_WITH_ME:
            # Get notes shared with user (not owned by user)
            shared_note_ids_subquery = (
                db_session.query(NoteShareORM.note_id)
                .filter(NoteShareORM.shared_with_user_id == criteria.user_id)
                .subquery()
            )

            return db_session.query(NoteORM).filter(
                ~NoteORM.is_deleted,
                NoteORM.id.in_(db_session.query(shared_note_ids_subquery.c.note_id)),
            )

        else:
            raise ValueError(f"Unsupported search section: {criteria.section}")

    def _apply_tag_filter(self, db_session: Session, query, tag_ids: List[UUID]):
        """Apply tag filtering to the query using AND logic.

        Args:
            db_session: SQLAlchemy database session
            query: Base SQLAlchemy query
            tag_ids: List of tag UUIDs to filter by

        Returns:
            Modified query with tag filtering applied
        """
        # Join with note_tags and group by note to ensure the note has ALL selected tags
        return (
            query.join(note_tags)
            .filter(note_tags.c.tag_id.in_(tag_ids))
            .group_by(NoteORM.id)
            .having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
        )

    def _apply_text_search(self, query, search_query: str):
        """Apply text search to the query using PostgreSQL full-text search.

        Args:
            query: Base SQLAlchemy query
            search_query: Text query for searching

        Returns:
            Modified query with text search applied
        """
        search_pattern = f"%{search_query}%"

        # Full-text search condition
        fulltext_condition = NoteORM.search_vector.op("@@")(
            func.plainto_tsquery("simple", search_query)
        )

        # Substring search condition (case-insensitive)
        substring_condition = or_(
            NoteORM.title.ilike(search_pattern), NoteORM.content.ilike(search_pattern)
        )

        # Combine both conditions with OR
        search_condition = or_(fulltext_condition, substring_condition)
        return query.filter(search_condition)

    def _convert_orm_to_domain(self, note_orm: NoteORM) -> Note:
        """Convert a NoteORM object to a Note domain entity.

        Args:
            note_orm: SQLAlchemy ORM object

        Returns:
            Note domain entity
        """
        # Convert associated tags to domain entities
        tag_entities = [TagEntity(id=tag.id, name=tag.name) for tag in note_orm.tags]

        return Note(
            id=note_orm.id,
            title=note_orm.title,
            content=note_orm.content,
            owner_id=note_orm.owner_id,
            tags=tag_entities,
            created_at=note_orm.created_at,
            updated_at=note_orm.updated_at,
            is_deleted=note_orm.is_deleted,
            search_vector=str(note_orm.search_vector)
            if note_orm.search_vector
            else None,
        )
