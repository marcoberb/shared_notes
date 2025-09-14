"""Search domain service for the shared notes application.

This module contains the SearchService that orchestrates search operations
following Domain-Driven Design principles.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from domain.entities.search import PaginationMetadata, SearchCriteria, SearchResult
from domain.repositories.search_repository import SearchRepository

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SearchService:
    """Domain service for handling search operations.

    This service encapsulates the business logic for searching notes
    across different sections (my-notes, shared-by-me, shared-with-me).
    It coordinates between the search criteria and the repository layer.
    """

    def __init__(self, search_repository: SearchRepository):
        """Initialize the search service with dependencies.

        Args:
            search_repository (SearchRepository): Repository for performing search operations.
        """
        self._search_repository = search_repository

    async def search_notes(
        self, db_session: "Session", criteria: SearchCriteria
    ) -> SearchResult:
        """Search for notes based on the provided criteria.

        This method orchestrates the search operation by:
        1. Validating the search criteria
        2. Delegating to the repository for data retrieval
        3. Calculating pagination metadata
        4. Creating and returning the search result

        Args:
            db_session (Session): SQLAlchemy database session for this operation.
            criteria (SearchCriteria): The search criteria containing all search parameters.

        Returns:
            SearchResult: The search results with notes and pagination info.

        Raises:
            ValueError: If search criteria are invalid.
            SearchError: If search operation fails.
        """
        logger.info(
            f"Performing search for user {criteria.user_id} with query '{criteria.query}' "
            f"and {len(criteria.tag_ids) if criteria.tag_ids else 0} tags in section {criteria.section.value}"
        )

        # Get notes and total count from repository
        notes, total_count = await self._search_repository.search_notes(
            db_session, criteria
        )

        # Calculate pagination metadata
        pagination = PaginationMetadata.calculate(
            current_page=criteria.page,
            total_notes=total_count,
            notes_per_page=criteria.limit,
        )

        # Create and return search result
        search_result = SearchResult(
            notes=notes,
            pagination=pagination,
            criteria=criteria,
            search_timestamp=datetime.utcnow(),
        )

        logger.info(
            f"Search completed: found {len(notes)} notes out of {total_count} total "
            f"for user {criteria.user_id} on page {criteria.page}"
        )

        return search_result

    def validate_search_criteria(self, criteria: SearchCriteria) -> None:
        """Validate search criteria according to business rules.

        This method ensures the search criteria meet all business requirements
        before proceeding with the search operation.

        Args:
            criteria (SearchCriteria): The search criteria to validate.

        Raises:
            ValueError: If criteria are invalid according to business rules.
        """
        # Validation is already handled in SearchCriteria.__post_init__
        # but we can add additional business rules here if needed

        if criteria.has_text_search() and len(criteria.query.strip()) < 2:
            raise ValueError("Search query must be at least 2 characters long")

        if criteria.has_tag_filter() and len(criteria.tag_ids) > 10:
            raise ValueError("Cannot filter by more than 10 tags at once")

        logger.debug(
            f"Search criteria validated successfully for user {criteria.user_id}"
        )


class SearchError(Exception):
    """Exception raised when search operations fail."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """Initialize search error.

        Args:
            message (str): Human-readable error message.
            original_error (Optional[Exception]): Original exception that caused this error.
        """
        super().__init__(message)
        self.original_error = original_error
