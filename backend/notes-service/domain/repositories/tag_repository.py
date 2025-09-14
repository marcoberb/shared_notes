"""Tag repository interface.

This module defines the abstract interface for tag data access
operations, following the Repository pattern from DDD.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..entities.tag import TagEntity


class TagRepositoryInterface(ABC):
    """Abstract interface for tag repository operations.

    This interface defines the contract for tag data access
    without coupling to specific database implementations.

    Following the Repository pattern from Domain-Driven Design,
    this interface allows the domain layer to remain independent
    of infrastructure concerns.

    NOTE: All methods receive a fresh database session to ensure
    proper transaction management and avoid session leaks.
    """

    @abstractmethod
    async def get_all(self, db_session: Session) -> List[TagEntity]:
        """Retrieve all tags from the repository.

        Args:
            db_session (Session): Fresh database session for this operation.

        Returns:
            List[TagEntity]: List of all available tag entities.

        Example:
            >>> with get_db_session() as db:
            ...     tags = await repository.get_all(db)
            ...     print(len(tags))
            5
        """
        pass

    @abstractmethod
    async def get_by_id(self, db_session: Session, tag_id: UUID) -> Optional[TagEntity]:
        """Retrieve a tag by its unique identifier.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag_id (UUID): The unique identifier of the tag to retrieve.

        Returns:
            Optional[TagEntity]: The tag entity if found, None otherwise.

        Example:
            >>> with get_db_session() as db:
            ...     tag = await repository.get_by_id(db, UUID('123e4567-e89b-12d3-a456-426614174000'))
            ...     print(tag.name if tag else "Not found")
            "work"
        """
        pass

    @abstractmethod
    async def get_by_name(self, db_session: Session, name: str) -> Optional[TagEntity]:
        """Retrieve a tag by its name.

        Args:
            db_session (Session): Fresh database session for this operation.
            name (str): The name of the tag to retrieve.

        Returns:
            Optional[TagEntity]: The tag entity if found, None otherwise.

        Example:
            >>> with get_db_session() as db:
            ...     tag = await repository.get_by_name(db, "work")
            ...     print(tag.id if tag else "Not found")
            UUID('123e4567-e89b-12d3-a456-426614174000')
        """
        pass

    @abstractmethod
    async def save(self, db_session: Session, tag: TagEntity) -> TagEntity:
        """Save a tag entity to the repository.

        For new tags (id is None), this will create a new record.
        For existing tags, this will update the existing record.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag (TagEntity): The tag entity to save.

        Returns:
            TagEntity: The saved tag entity with populated ID.

        Example:
            >>> new_tag = TagEntity(id=None, name="work")
            >>> with get_db_session() as db:
            ...     saved_tag = await repository.save(db, new_tag)
            ...     print(saved_tag.id)
            UUID('123e4567-e89b-12d3-a456-426614174000')
        """
        pass

    @abstractmethod
    async def delete(self, db_session: Session, tag_id: UUID) -> bool:
        """Delete a tag from the repository.

        Args:
            db_session (Session): Fresh database session for this operation.
            tag_id (UUID): The unique identifier of the tag to delete.

        Returns:
            bool: True if the tag was deleted, False if not found.

        Example:
            >>> with get_db_session() as db:
            ...     deleted = await repository.delete(db, UUID('123e4567-e89b-12d3-a456-426614174000'))
            ...     print(deleted)
            True
        """
        pass
