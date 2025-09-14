"""Tag repository interface.

This module defines the abstract interface for tag data access
operations, following the Repository pattern from DDD.
"""

from abc import ABC, abstractmethod
from typing import List

from domain.entities.tag import TagEntity
from sqlalchemy.orm import Session


class TagRepository(ABC):
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
