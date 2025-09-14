"""Search repository interface for the shared notes application.

This module defines the repository interface for search operations
following Domain-Driven Design principles.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Tuple

from domain.entities.note import Note
from domain.entities.search import SearchCriteria

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SearchRepository(ABC):
    """Abstract repository interface for search operations.

    This interface defines the contract for search repositories,
    allowing different implementations (e.g., SQLAlchemy, MongoDB, etc.)
    while keeping the domain layer independent of infrastructure concerns.
    """

    @abstractmethod
    async def search_notes(
        self, db_session: "Session", criteria: SearchCriteria
    ) -> Tuple[List[Note], int]:
        """Search for notes based on the provided criteria.

        Args:
            db_session: SQLAlchemy database session for this operation
            criteria: The search criteria containing all search parameters

        Returns:
            Tuple[List[Note], int]: A tuple containing:
                - List of notes matching the criteria (paginated)
                - Total count of notes matching the criteria (for pagination)

        Raises:
            RepositoryError: If search operation fails at the data layer
        """
        pass
