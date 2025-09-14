"""Tag domain entity.

This module contains the Tag domain entity that represents
a tag in the business domain with its rules and behaviors.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TagEntity:
    """Domain entity representing a tag.

    This is an immutable domain object that represents a tag
    with its business rules and constraints.

    Attributes:
        id (Optional[UUID]): Unique identifier for the tag. None for new tags.
        name (str): The display name of the tag.

    Example:
        >>> tag = TagEntity(id=None, name="work")
        >>> print(tag.name)
        "work"

    Business Rules:
        - Tag name must be non-empty and stripped of whitespace
        - Tag names should be unique (enforced at repository level)
        - Tags are immutable once created (value object characteristics)
    """

    id: Optional[UUID]
    name: str

    def __post_init__(self) -> None:
        """Validate tag entity after initialization.

        Raises:
            ValueError: If tag name is empty or contains only whitespace.
        """
        if not self.name or not self.name.strip():
            raise ValueError("Tag name cannot be empty or whitespace")

        # Normalize the name by stripping whitespace
        object.__setattr__(self, "name", self.name.strip())

    def is_new(self) -> bool:
        """Check if this is a new tag (not yet persisted).

        Returns:
            bool: True if the tag has no ID (new), False otherwise.

        Example:
            >>> new_tag = TagEntity(id=None, name="work")
            >>> existing_tag = TagEntity(id=UUID('123e4567-e89b-12d3-a456-426614174000'), name="work")
            >>> print(new_tag.is_new())
            True
            >>> print(existing_tag.is_new())
            False
        """
        return self.id is None

    def with_id(self, tag_id: UUID) -> "TagEntity":
        """Create a new TagEntity with the specified ID.

        This is useful when persisting a new tag and getting back the generated ID.

        Args:
            tag_id (UUID): The unique identifier to assign to the tag.

        Returns:
            TagEntity: A new TagEntity instance with the specified ID.

        Example:
            >>> new_tag = TagEntity(id=None, name="work")
            >>> persisted_tag = new_tag.with_id(UUID('123e4567-e89b-12d3-a456-426614174000'))
            >>> print(persisted_tag.id)
            UUID('123e4567-e89b-12d3-a456-426614174000')
        """
        return TagEntity(id=tag_id, name=self.name)
