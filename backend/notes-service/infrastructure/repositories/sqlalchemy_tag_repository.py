"""SQLAlchemy implementation of the tag repository.

This module contains the concrete implementation of TagRepositoryInterface
using SQLAlchemy for database operations and entity mapping.
"""

from typing import List

from domain.entities.tag import TagEntity
from domain.repositories.tag_repository import TagRepository
from infrastructure.models.tag_orm import TagORM
from sqlalchemy.orm import Session


class SqlAlchemyTagRepository(TagRepository):
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

    def _model_to_entity(self, tag_model: TagORM) -> TagEntity:
        """Convert SQLAlchemy model to domain entity.

        Args:
            tag_model (TagORM): SQLAlchemy tag model instance.

        Returns:
            TagEntity: Corresponding domain entity.
        """
        return TagEntity(id=tag_model.id, name=tag_model.name)
