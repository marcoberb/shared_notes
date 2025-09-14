"""Tag domain service.

This module contains the TagService that implements business logic
for tag operations, orchestrating between entities and repositories.
"""

from typing import List

from domain.entities.tag import TagEntity
from domain.repositories.tag_repository import TagRepository
from sqlalchemy.orm import Session


class TagService:
    """Domain service for tag business operations.

    This service contains the business logic for tag operations,
    coordinating between domain entities and repository interfaces.
    It encapsulates business rules and workflows that involve tags.

    Attributes:
        _tag_repository (TagRepositoryInterface): Repository for tag data access.

    Example:
        >>> service = TagService(tag_repository)
        >>> with get_db_session() as db:
        ...     tags = await service.get_all_tags(db)
        ...     print(len(tags))
        5
    """

    def __init__(self, tag_repository: TagRepository) -> None:
        """Initialize the tag service with required dependencies.

        Args:
            tag_repository (TagRepositoryInterface): Repository implementation for tag data access.
        """
        self._tag_repository = tag_repository

    async def get_all_tags(self, db_session: Session) -> List[TagEntity]:
        """Retrieve all available tags.

        This method implements the business logic for retrieving all tags,
        potentially applying business rules for filtering or ordering.

        Args:
            db_session (Session): Fresh database session for this operation.

        Returns:
            List[TagEntity]: List of all available tag entities sorted by name.

        Example:
            >>> with get_db_session() as db:
            ...     tags = await service.get_all_tags(db)
            ...     print([tag.name for tag in tags])
            ['personal', 'work']
        """
        tags = await self._tag_repository.get_all(db_session)

        # Business rule: Return tags sorted by name for consistent ordering
        return sorted(tags, key=lambda tag: tag.name.lower())
