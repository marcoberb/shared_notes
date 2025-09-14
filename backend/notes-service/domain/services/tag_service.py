"""Tag domain service.

This module contains the TagService that implements business logic
for tag operations, orchestrating between entities and repositories.
"""

from typing import List
from uuid import UUID

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

    async def get_tag_by_id(self, db_session: Session, tag_id: UUID) -> TagEntity:
        """Retrieve a tag by its unique identifier.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag_id (UUID): The unique identifier of the tag to retrieve.

        Returns:
            TagEntity: The requested tag entity.

        Raises:
            TagNotFoundError: If the tag with the specified ID does not exist.

        Example:
            >>> with get_db_session() as db:
            ...     tag = await service.get_tag_by_id(db, UUID('123e4567-e89b-12d3-a456-426614174000'))
            ...     print(tag.name)
            "work"
        """
        tag = await self._tag_repository.get_by_id(db_session, tag_id)
        if not tag:
            raise TagNotFoundError(f"Tag with ID {tag_id} not found")
        return tag

    async def create_tag(self, db_session: Session, name: str) -> TagEntity:
        """Create a new tag with the specified name.

        This method implements business rules for tag creation,
        including validation and duplicate checking.

        Args:
            db_session (Session): Fresh database session for this operation.
            name (str): The name for the new tag.

        Returns:
            TagEntity: The created tag entity with assigned ID.

        Raises:
            TagAlreadyExistsError: If a tag with the same name already exists.
            ValueError: If the tag name is invalid.

        Example:
            >>> with get_db_session() as db:
            ...     tag = await service.create_tag(db, "urgent")
            ...     print(tag.id)
            UUID('123e4567-e89b-12d3-a456-426614174000')
        """
        # Business rule: Tag names must be unique (case-insensitive)
        existing_tag = await self._tag_repository.get_by_name(db_session, name.strip())
        if existing_tag:
            raise TagAlreadyExistsError(f"Tag with name '{name}' already exists")

        # Create new tag entity (validation happens in constructor)
        new_tag = TagEntity(id=None, name=name)

        # Persist the tag
        return await self._tag_repository.save(db_session, new_tag)

    async def update_tag(
        self, db_session: Session, tag_id: UUID, new_name: str
    ) -> TagEntity:
        """Update an existing tag's name.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag_id (UUID): The unique identifier of the tag to update.
            new_name (str): The new name for the tag.

        Returns:
            TagEntity: The updated tag entity.

        Raises:
            TagNotFoundError: If the tag with the specified ID does not exist.
            TagAlreadyExistsError: If another tag with the new name already exists.
            ValueError: If the new tag name is invalid.

        Example:
            >>> with get_db_session() as db:
            ...     updated_tag = await service.update_tag(db, tag_id, "important")
            ...     print(updated_tag.name)
            "important"
        """
        # Check if tag exists
        existing_tag = await self.get_tag_by_id(db_session, tag_id)

        # Business rule: Don't allow duplicate names (case-insensitive)
        if existing_tag.name.lower() != new_name.strip().lower():
            duplicate_tag = await self._tag_repository.get_by_name(
                db_session, new_name.strip()
            )
            if duplicate_tag and duplicate_tag.id != tag_id:
                raise TagAlreadyExistsError(
                    f"Tag with name '{new_name}' already exists"
                )

        # Create updated tag entity
        updated_tag = TagEntity(id=tag_id, name=new_name)

        # Persist the changes
        return await self._tag_repository.save(db_session, updated_tag)

    async def delete_tag(self, db_session: Session, tag_id: UUID) -> bool:
        """Delete a tag by its unique identifier.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag_id (UUID): The unique identifier of the tag to delete.

        Returns:
            bool: True if the tag was deleted, False if not found.

        Example:
            >>> with get_db_session() as db:
            ...     deleted = await service.delete_tag(db, UUID('123e4567-e89b-12d3-a456-426614174000'))
            ...     print(deleted)
            True
        """
        return await self._tag_repository.delete(db_session, tag_id)


class TagNotFoundError(Exception):
    """Exception raised when a requested tag is not found."""

    pass


class TagAlreadyExistsError(Exception):
    """Exception raised when trying to create a tag that already exists."""

    pass
