"""Tag converters for transforming between Pydantic schemas and domain entities.

This module contains converter functions for transforming tag objects
between the API layer (Pydantic) and the domain layer (entities).
"""

from typing import List
from uuid import UUID

from domain.entities.tag import TagEntity

from application.rest.schemas.input.tag_input import TagCreate, TagUpdate
from application.rest.schemas.output.tag_output import TagResponse


class TagConverter:
    """Converter class for tag transformations between layers.

    This class provides static methods to convert between:
    - Pydantic input schemas -> Domain entities
    - Domain entities -> Pydantic output schemas

    Example:
        >>> tag_entity = TagConverter.create_input_to_entity(TagCreate(name="work"))
        >>> tag_response = TagConverter.entity_to_response(tag_entity)
    """

    @staticmethod
    def create_input_to_entity(tag_create: TagCreate) -> TagEntity:
        """Convert TagCreate Pydantic schema to TagEntity domain object.

        Args:
            tag_create (TagCreate): Pydantic schema containing tag creation data.

        Returns:
            TagEntity: Domain entity representing a new tag (id=None).

        Example:
            >>> tag_input = TagCreate(name="work")
            >>> tag_entity = TagConverter.create_input_to_entity(tag_input)
            >>> print(tag_entity.name)
            "work"
            >>> print(tag_entity.is_new())
            True
        """
        return TagEntity(
            id=None,  # New tag, no ID yet
            name=tag_create.name,
        )

    @staticmethod
    def update_input_to_entity(tag_id: str, tag_update: TagUpdate) -> TagEntity:
        """Convert TagUpdate Pydantic schema to TagEntity domain object.

        Args:
            tag_id (str): String representation of the tag UUID.
            tag_update (TagUpdate): Pydantic schema containing tag update data.

        Returns:
            TagEntity: Domain entity representing an existing tag.

        Example:
            >>> tag_update = TagUpdate(name="important")
            >>> tag_entity = TagConverter.update_input_to_entity("123e4567-e89b-12d3-a456-426614174000", tag_update)
            >>> print(tag_entity.name)
            "important"
            >>> print(tag_entity.is_new())
            False
        """
        return TagEntity(id=UUID(tag_id), name=tag_update.name)

    @staticmethod
    def entity_to_response(tag_entity: TagEntity) -> TagResponse:
        """Convert TagEntity domain object to TagResponse Pydantic schema.

        Args:
            tag_entity (TagEntity): Domain entity representing a tag.

        Returns:
            TagResponse: Pydantic schema for API response.

        Raises:
            ValueError: If the tag entity has no ID (not persisted).

        Example:
            >>> tag_entity = TagEntity(id=UUID("123e4567-e89b-12d3-a456-426614174000"), name="work")
            >>> tag_response = TagConverter.entity_to_response(tag_entity)
            >>> print(tag_response.id)
            "123e4567-e89b-12d3-a456-426614174000"
            >>> print(tag_response.name)
            "work"
        """
        if tag_entity.is_new():
            raise ValueError("Cannot convert new tag entity to response (no ID)")

        return TagResponse(id=str(tag_entity.id), name=tag_entity.name)

    @staticmethod
    def entities_to_responses(tag_entities: List[TagEntity]) -> List[TagResponse]:
        """Convert list of TagEntity domain objects to list of TagResponse schemas.

        Args:
            tag_entities (List[TagEntity]): List of domain entities.

        Returns:
            List[TagResponse]: List of Pydantic schemas for API response.

        Example:
            >>> entities = [TagEntity(id=UUID("123..."), name="work")]
            >>> responses = TagConverter.entities_to_responses(entities)
            >>> print(len(responses))
            1
        """
        return [TagConverter.entity_to_response(entity) for entity in tag_entities]
