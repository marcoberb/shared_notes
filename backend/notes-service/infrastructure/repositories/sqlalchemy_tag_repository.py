"""SQLAlchemy implementation of the tag repository.

This module contains the concrete implementation of TagRepositoryInterface
using SQLAlchemy for database operations and entity mapping.
"""

from typing import List, Optional
from uuid import UUID

from domain.entities.tag import TagEntity
from domain.repositories.tag_repository import TagRepositoryInterface
from sqlalchemy.orm import Session

from infrastructure.models.tag_orm import TagORM


class SqlAlchemyTagRepository(TagRepositoryInterface):
    """SQLAlchemy implementation of the tag repository.

    This class implements the TagRepositoryInterface using SQLAlchemy
    for database operations. It handles the conversion between domain
    entities and SQLAlchemy models.

    NOTE: This repository does not store the session internally.
    Each method receives a fresh session to ensure proper transaction management
    and avoid session leaks.

    Example:
        >>> repository = SqlAlchemyTagRepository()
        >>> with get_db_session() as db:
        ...     tags = await repository.get_all(db)
        ...     print(len(tags))
        5
    """

    async def get_all(self, db_session: Session) -> List[TagEntity]:
        """Retrieve all tags from the database.

        Args:
            db_session (Session): Fresh SQLAlchemy database session for this operation.

        Returns:
            List[TagEntity]: List of all available tag entities.
        """
        tag_models = db_session.query(TagORM).all()
        return [self._model_to_entity(model) for model in tag_models]

    async def get_by_id(self, db_session: Session, tag_id: UUID) -> Optional[TagEntity]:
        """Retrieve a tag by its unique identifier.

        Args:
            db_session (Session): Fresh SQLAlchemy database session for this operation.
            tag_id (UUID): The unique identifier of the tag to retrieve.

        Returns:
            Optional[TagEntity]: The tag entity if found, None otherwise.
        """
        tag_model = db_session.query(TagORM).filter(TagORM.id == tag_id).first()
        return self._model_to_entity(tag_model) if tag_model else None

    async def get_by_name(self, db_session: Session, name: str) -> Optional[TagEntity]:
        """Retrieve a tag by its name (case-insensitive).

        Args:
            db_session (Session): Fresh SQLAlchemy database session for this operation.
            name (str): The name of the tag to retrieve.

        Returns:
            Optional[TagEntity]: The tag entity if found, None otherwise.
        """
        tag_model = (
            db_session.query(TagORM).filter(TagORM.name.ilike(name.strip())).first()
        )
        return self._model_to_entity(tag_model) if tag_model else None

    async def save(self, db_session: Session, tag: TagEntity) -> TagEntity:
        """Save a tag entity to the database.

        For new tags (id is None), this will create a new record.
        For existing tags, this will update the existing record.

        Args:
            db_session (Session): Fresh SQLAlchemy database session for this operation.
            tag (TagEntity): The tag entity to save.

        Returns:
            TagEntity: The saved tag entity with populated ID.
        """
        if tag.is_new():
            # Create new tag
            tag_model = TagORM(name=tag.name)
            db_session.add(tag_model)
            db_session.flush()  # Flush to get the generated ID
            return self._model_to_entity(tag_model)
        else:
            # Update existing tag
            tag_model = db_session.query(TagORM).filter(TagORM.id == tag.id).first()
            if tag_model:
                tag_model.name = tag.name
                db_session.flush()
                return self._model_to_entity(tag_model)
            else:
                # Tag doesn't exist, create it with the specified ID
                tag_model = TagORM(id=tag.id, name=tag.name)
                db_session.add(tag_model)
                db_session.flush()
                return self._model_to_entity(tag_model)

    async def delete(self, db_session: Session, tag_id: UUID) -> bool:
        """Delete a tag from the database.

        Args:
            db_session (Session): Fresh SQLAlchemy database session for this operation.
            tag_id (UUID): The unique identifier of the tag to delete.

        Returns:
            bool: True if the tag was deleted, False if not found.
        """
        tag_model = db_session.query(TagORM).filter(TagORM.id == tag_id).first()
        if tag_model:
            db_session.delete(tag_model)
            db_session.flush()
            return True
        return False

    def _model_to_entity(self, tag_model: TagORM) -> TagEntity:
        """Convert SQLAlchemy model to domain entity.

        Args:
            tag_model (TagORM): SQLAlchemy tag model instance.

        Returns:
            TagEntity: Corresponding domain entity.
        """
        return TagEntity(id=tag_model.id, name=tag_model.name)

    def _entity_to_model(self, tag_entity: TagEntity) -> TagORM:
        """Convert domain entity to SQLAlchemy model.

        Args:
            tag_entity (TagEntity): Domain tag entity.

        Returns:
            TagORM: Corresponding SQLAlchemy model.
        """
        return TagORM(id=tag_entity.id, name=tag_entity.name)
