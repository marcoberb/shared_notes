from application.rest.schemas.output.note_output import NoteResponse
from application.rest.schemas.output.share_output import ShareResponse
from infrastructure.models.note_orm import NoteORM
from infrastructure.models.note_share_orm import NoteShareORM


def convert_note_to_response(note: NoteORM) -> NoteResponse:
    """Convert Note model to NoteResponse with proper UUID handling.

    Args:
        note: SQLAlchemy Note model instance with tags relationship loaded.

    Returns:
        NoteResponse: Pydantic model with string UUIDs and formatted data.

    Example:
        >>> note = db.query(Note).first()
        >>> response = convert_note_to_response(note)
        >>> print(response.id)
        "uuid-string"
    """
    tags = [{"id": str(tag.id), "name": tag.name} for tag in note.tags]
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        owner_id=note.owner_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=tags,
    )


def convert_share_to_response(
    share: NoteShareORM, shared_with_email: str
) -> ShareResponse:
    """Convert NoteShare model to ShareResponse with proper UUID handling.

    Args:
        share: SQLAlchemy NoteShare model instance.
        shared_with_email (str): Email address of the user the note is shared with.

    Returns:
        ShareResponse: Pydantic model with string UUIDs and share data.

    Example:
        >>> share = db.query(NoteShare).first()
        >>> response = convert_share_to_response(share, "user@email.com")
        >>> print(response.shared_with_email)
        "user@email.com"
    """
    return ShareResponse(
        id=str(share.id),
        note_id=str(share.note_id),
        shared_by_user_id=share.shared_by_user_id,
        shared_with_user_id=share.shared_with_user_id,
        shared_with_email=shared_with_email,
        created_at=share.created_at,
    )
