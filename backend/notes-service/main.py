from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table, func, or_, distinct
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, outerjoin
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os
import redis
import logging
import httpx
import json
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@localhost:5432/sharednotes")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Keycloak configuration for user lookup
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sharednotes")
KEYCLOAK_ADMIN_CLIENT_ID = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli")
KEYCLOAK_ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
KEYCLOAK_ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Redis configuration  
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# FastAPI app
app = FastAPI(
    title="SharedNotes Notes Service",
    description="Notes management service for SharedNotes",
    version="1.0.0"
)

# Association table for many-to-many relationship
note_tags = Table('note_tags', Base.metadata,
    Column('note_id', UUID(as_uuid=True), ForeignKey('notes.id'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'), primary_key=True)
)

# Models
class Note(Base):
    __tablename__ = "notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    owner_id = Column(String(255), nullable=False)  # Keycloak UUID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    search_vector = Column(Text)  # tsvector for full-text search
    
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")

class NoteShare(Base):
    __tablename__ = "note_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    note_id = Column(UUID(as_uuid=True), ForeignKey('notes.id'), nullable=False)
    shared_by_user_id = Column(String(255), nullable=False)
    shared_with_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    note = relationship("Note", backref="shares")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    notes = relationship("Note", secondary=note_tags, back_populates="tags")

# Pydantic models
class TagCreate(BaseModel):
    name: str

class TagResponse(BaseModel):
    id: str  # UUID as string
    name: str

class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []  # UUID strings
    share_emails: Optional[List[str]] = []  # Emails to share with during creation

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None  # UUID strings

class NoteResponse(BaseModel):
    id: str  # UUID as string
    title: str
    content: str
    owner_id: str  # Keycloak UUID
    created_at: datetime
    updated_at: datetime
    tags: List[TagResponse]

class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    total_notes: int
    notes_per_page: int
    has_next: bool
    has_previous: bool

class NotesListResponse(BaseModel):
    notes: List[NoteResponse]
    pagination: PaginationInfo

# Share models
class ShareRequest(BaseModel):
    note_id: str  # UUID string
    emails: List[str]  # List of email addresses to share with

class ShareResponse(BaseModel):
    id: str  # UUID string
    note_id: str  # UUID string
    shared_by_user_id: str
    shared_with_user_id: str
    shared_with_email: str  # We'll fetch this from Keycloak when returning
    created_at: datetime

class NoteSharesResponse(BaseModel):
    note_id: str  # UUID string
    shares: List[ShareResponse]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user_id(request: Request) -> str:
    """Extract user ID from request headers"""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in headers")
    return user_id

# Helper functions for UUID conversion
def convert_note_to_response(note) -> NoteResponse:
    """Convert Note model to NoteResponse with proper UUID handling"""
    tags = [TagResponse(id=str(tag.id), name=tag.name) for tag in note.tags]
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        owner_id=note.owner_id,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=tags
    )

def convert_tag_to_response(tag) -> TagResponse:
    """Convert Tag model to TagResponse with proper UUID handling"""
    return TagResponse(id=str(tag.id), name=tag.name)

# Keycloak integration functions
async def get_keycloak_admin_token():
    """Get admin token from Keycloak for API access"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
                data={
                    "grant_type": "password",
                    "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
                    "username": KEYCLOAK_ADMIN_USERNAME,
                    "password": KEYCLOAK_ADMIN_PASSWORD
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                logger.error(f"Failed to get Keycloak admin token: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error getting Keycloak admin token: {e}")
        return None

async def get_user_id_by_email(email: str) -> Optional[str]:
    """Get Keycloak user ID by email address"""
    try:
        admin_token = await get_keycloak_admin_token()
        if not admin_token:
            return None
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
                params={"email": email, "exact": "true"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if response.status_code == 200:
                users = response.json()
                if users and len(users) > 0:
                    return users[0]["id"]  # Return the user ID
                else:
                    logger.info(f"No user found with email: {email}")
                    return None
            else:
                logger.error(f"Failed to search users: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error searching user by email {email}: {e}")
        return None

async def get_user_email_by_id(user_id: str) -> Optional[str]:
    """Get user email by Keycloak user ID"""
    try:
        admin_token = await get_keycloak_admin_token()
        if not admin_token:
            return None
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data.get("email")
            else:
                logger.error(f"Failed to get user data: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Error getting user email for ID {user_id}: {e}")
        return None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notes-service"}

@app.get("/notes", response_model=NotesListResponse)
async def get_notes(
    request: Request, 
    page: int = 1, 
    limit: int = 10, 
    db: Session = Depends(get_db)
):
    """Get all notes for the current user with pagination"""
    user_id = get_current_user_id(request)
    logger.info(f"Getting notes for user_id: {user_id}, page: {page}, limit: {limit}")
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get total count
    total_notes = db.query(Note).filter(
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).count()
    
    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    # Get notes for current page
    notes = db.query(Note).filter(
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).order_by(Note.updated_at.desc()).offset(offset).limit(limit).all()
    
    logger.info(f"Found {len(notes)} notes for user {user_id} on page {page}")
    
    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))
    
    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous
    )
    
    logger.info(f"Returning {len(notes_list)} notes with pagination: {pagination}")
    return NotesListResponse(notes=notes_list, pagination=pagination)

@app.get("/search", response_model=NotesListResponse)
async def search_notes(
    request: Request,
    q: str = "",
    tags: Optional[str] = None,  # Comma-separated tag IDs
    section: str = "my-notes",  # Section to search: my-notes, shared-by-me, shared-with-me
    page: int = 1,
    limit: int = 15,
    db: Session = Depends(get_db)
):
    """Search notes using PostgreSQL full-text search and/or tag filtering in specific section"""
    user_id = get_current_user_id(request)
    
    # Parse tag IDs from query parameter
    tag_ids = []
    if tags:
        try:
            tag_ids = [uuid.UUID(tag_id.strip()) for tag_id in tags.split(',') if tag_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format for tag IDs")
    
    # If neither text search nor tag filter, return error
    if not q.strip() and not tag_ids:
        raise HTTPException(status_code=400, detail="Search query or tags must be provided")
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Start building the query based on section
    if section == "my-notes":
        # Get note IDs that are shared (to exclude them)
        shared_note_ids_subquery = db.query(NoteShare.note_id).filter(NoteShare.shared_by_user_id == user_id).subquery()
        
        # Base query for user's own notes that are NOT shared
        base_query = db.query(Note).filter(
            Note.owner_id == user_id,
            ~Note.is_deleted,
            ~Note.id.in_(db.query(shared_note_ids_subquery.c.note_id))
        )
    elif section == "shared-by-me":
        # Get notes that are owned by user AND shared (present in note_shares)
        shared_note_ids_subquery = db.query(NoteShare.note_id).filter(NoteShare.shared_by_user_id == user_id).subquery()
        
        base_query = db.query(Note).filter(
            Note.owner_id == user_id,
            ~Note.is_deleted,
            Note.id.in_(db.query(shared_note_ids_subquery.c.note_id))
        )
    elif section == "shared-with-me":
        # Get notes shared with user (not owned by user)
        shared_note_ids_subquery = db.query(NoteShare.note_id).filter(NoteShare.shared_with_user_id == user_id).subquery()
        
        base_query = db.query(Note).filter(
            ~Note.is_deleted,
            Note.id.in_(db.query(shared_note_ids_subquery.c.note_id))
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid section. Must be one of: my-notes, shared-by-me, shared-with-me")
    
    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        # Join with note_tags and group by note to ensure the note has ALL selected tags
        base_query = base_query.join(note_tags).filter(note_tags.c.tag_id.in_(tag_ids)).group_by(Note.id).having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
    
    # Add text search if provided
    if q.strip():
        search_query = q.strip()
        search_pattern = f"%{search_query}%"
        
        # Full-text search condition
        fulltext_condition = Note.search_vector.op('@@')(func.plainto_tsquery('simple', search_query))
        
        # Substring search condition (case-insensitive)
        substring_condition = or_(
            Note.title.ilike(search_pattern),
            Note.content.ilike(search_pattern)
        )
        
        # Combine both conditions with OR
        search_condition = or_(fulltext_condition, substring_condition)
        base_query = base_query.filter(search_condition)
    
    # Get total count for pagination
    total_notes = base_query.count()
    
    # Get notes with ordering
    notes = base_query.order_by(
        Note.updated_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1
    
    logger.info(f"Found {len(notes)} notes for search '{q}' with tags {tag_ids} in section '{section}' for user {user_id} on page {page}")
    
    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))
    
    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous
    )
    
    logger.info(f"Returning {len(notes_list)} search results with pagination: {pagination}")
    return NotesListResponse(notes=notes_list, pagination=pagination)

@app.get("/notes/my-notes", response_model=NotesListResponse)
async def get_my_notes(
    request: Request, 
    page: int = 1, 
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db)
):
    """Get paginated list of user's own notes that are NOT shared with others"""
    user_id = get_current_user_id(request)
    
    # Parse tag IDs from query parameter
    tag_ids = []
    if tags:
        try:
            tag_ids = [uuid.UUID(tag_id.strip()) for tag_id in tags.split(',') if tag_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format for tag IDs")
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get note IDs that are shared (to exclude them)
    shared_note_ids_subquery = db.query(NoteShare.note_id).filter(NoteShare.shared_by_user_id == user_id).subquery()
    
    # Base query for user's own notes that are NOT shared
    base_query = db.query(Note).filter(
        Note.owner_id == user_id,
        ~Note.is_deleted,
        ~Note.id.in_(db.query(shared_note_ids_subquery.c.note_id))
    )
    
    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = base_query.join(note_tags).filter(note_tags.c.tag_id.in_(tag_ids)).group_by(Note.id).having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
    
    # Get total count
    total_notes = base_query.count()
    
    # Get notes for current page
    notes = base_query.order_by(Note.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1
    
    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))
    
    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous
    )
    
    logger.info(f"Returning {len(notes_list)} my notes for user {user_id} on page {page}")
    return NotesListResponse(notes=notes_list, pagination=pagination)

@app.get("/notes/shared-by-me", response_model=NotesListResponse)
async def get_notes_shared_by_me(
    request: Request, 
    page: int = 1, 
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db)
):
    """Get notes owned by user that ARE shared with others"""
    user_id = get_current_user_id(request)
    logger.info(f"Getting notes shared by me for user_id: {user_id}, page: {page}, limit: {limit}")
    
    # Parse tag IDs from query parameter
    tag_ids = []
    if tags:
        try:
            tag_ids = [uuid.UUID(tag_id.strip()) for tag_id in tags.split(',') if tag_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format for tag IDs")
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get notes that are owned by user AND shared (present in note_shares)
    subquery = db.query(NoteShare.note_id).filter(NoteShare.shared_by_user_id == user_id).subquery()
    
    # Base query
    base_query = db.query(Note).filter(
        Note.owner_id == user_id,
        ~Note.is_deleted,
        Note.id.in_(db.query(subquery.c.note_id))
    )
    
    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = base_query.join(note_tags).filter(note_tags.c.tag_id.in_(tag_ids)).group_by(Note.id).having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
    
    # Get total count
    total_notes = base_query.count()
    
    # Get notes for current page
    notes = base_query.order_by(Note.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1
    
    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))
    
    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous
    )
    
    logger.info(f"Returning {len(notes_list)} notes shared by me")
    return NotesListResponse(notes=notes_list, pagination=pagination)

@app.get("/notes/shared-with-me", response_model=NotesListResponse)
async def get_notes_shared_with_me(
    request: Request, 
    page: int = 1, 
    limit: int = 15,
    tags: Optional[str] = None,  # Comma-separated tag IDs for filtering
    db: Session = Depends(get_db)
):
    """Get notes shared with the current user by others"""
    user_id = get_current_user_id(request)
    logger.info(f"Getting notes shared with me for user_id: {user_id}, page: {page}, limit: {limit}")
    
    # Parse tag IDs from query parameter
    tag_ids = []
    if tags:
        try:
            tag_ids = [uuid.UUID(tag_id.strip()) for tag_id in tags.split(',') if tag_id.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UUID format for tag IDs")
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Base query - notes shared with current user
    base_query = db.query(Note).join(
        NoteShare, Note.id == NoteShare.note_id
    ).filter(
        NoteShare.shared_with_user_id == user_id,
        ~Note.is_deleted
    )
    
    # Add tag filtering if provided (AND logic - note must have ALL selected tags)
    if tag_ids:
        base_query = base_query.join(note_tags).filter(note_tags.c.tag_id.in_(tag_ids)).group_by(Note.id).having(func.count(distinct(note_tags.c.tag_id)) == len(tag_ids))
    
    # Get total count
    total_notes = base_query.count()
    
    # Get notes for current page
    notes = base_query.order_by(Note.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Calculate pagination info
    total_pages = (total_notes + limit - 1) // limit
    has_next = page < total_pages
    has_previous = page > 1
    
    notes_list = []
    for note in notes:
        notes_list.append(convert_note_to_response(note))
    
    pagination = PaginationInfo(
        current_page=page,
        total_pages=total_pages,
        total_notes=total_notes,
        notes_per_page=limit,
        has_next=has_next,
        has_previous=has_previous
    )
    
    logger.info(f"Returning {len(notes_list)} notes shared with me")
    return NotesListResponse(notes=notes_list, pagination=pagination)

@app.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, request: Request, db: Session = Depends(get_db)):
    """Get a specific note"""
    user_id = get_current_user_id(request)
    
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return convert_note_to_response(note)

@app.post("/notes", response_model=NoteResponse)
async def create_note(note: NoteCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new note"""
    user_id = get_current_user_id(request)
    
    # Create note
    db_note = Note(
        title=note.title,
        content=note.content,
        owner_id=user_id
    )
    
    # Handle tags (now by ID)
    if note.tags:
        for tag_id in note.tags:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                db_note.tags.append(tag)
    
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    
    # Handle sharing during creation
    if note.share_emails:
        for email in note.share_emails:
            # Resolve email to Keycloak user ID
            shared_with_user_id = await get_user_id_by_email(email)
            
            if not shared_with_user_id:
                # Rollback the note creation
                db.delete(db_note)
                db.commit()
                raise HTTPException(status_code=400, detail=f"Utente non trovato per l'email: {email}")
            
            # Check if already shared with this user (shouldn't happen during creation, but safety check)
            existing_share = db.query(NoteShare).filter(
                NoteShare.note_id == db_note.id,
                NoteShare.shared_with_user_id == shared_with_user_id
            ).first()
            
            if not existing_share:
                db_share = NoteShare(
                    note_id=db_note.id,
                    shared_by_user_id=user_id,
                    shared_with_user_id=shared_with_user_id
                )
                db.add(db_share)
        
        db.commit()

    return convert_note_to_response(db_note)

@app.put("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str, 
    note_update: NoteUpdate, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Update a note"""
    user_id = get_current_user_id(request)
    
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Update fields
    if note_update.title is not None:
        db_note.title = note_update.title
    if note_update.content is not None:
        db_note.content = note_update.content
    
    # Update tags
    if note_update.tags is not None:
        db_note.tags.clear()
        for tag_id in note_update.tags:
            tag = db.query(Tag).filter(Tag.id == tag_id).first()
            if tag:
                db_note.tags.append(tag)
    
    db_note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_note)
    
    return convert_note_to_response(db_note)

@app.delete("/notes/{note_id}")
async def delete_note(note_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a note (soft delete)"""
    user_id = get_current_user_id(request)
    
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db_note.is_deleted = True
    db_note.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Note deleted successfully"}

# Share endpoints
@app.post("/notes/{note_id}/share", response_model=NoteSharesResponse)
async def share_note(note_id: str, share_request: ShareRequest, request: Request, db: Session = Depends(get_db)):
    """Share a note with one or more users by email"""
    user_id = get_current_user_id(request)
    
    # Verify that the note exists and is owned by the current user
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Validate that note_id in request matches URL parameter
    if share_request.note_id != note_id:
        raise HTTPException(status_code=400, detail="Note ID mismatch")
    
    created_shares = []
    
    # First validate all emails exist in Keycloak before creating any shares
    for email in share_request.emails:
        shared_with_user_id = await get_user_id_by_email(email)
        if not shared_with_user_id:
            raise HTTPException(status_code=400, detail=f"Utente non trovato per l'email: {email}")
    
    # If all emails are valid, proceed with sharing
    for email in share_request.emails:
        # Resolve email to Keycloak user ID (we know it exists now)
        shared_with_user_id = await get_user_id_by_email(email)
        
        # Check if already shared with this user
        existing_share = db.query(NoteShare).filter(
            NoteShare.note_id == note_id,
            NoteShare.shared_with_user_id == shared_with_user_id
        ).first()
        
        if existing_share:
            continue  # Skip if already shared
        
        # Create new share
        db_share = NoteShare(
            note_id=note_id,
            shared_by_user_id=user_id,
            shared_with_user_id=shared_with_user_id
        )
        
        db.add(db_share)
        created_shares.append(db_share)
    
    db.commit()
    
    # Return all shares for this note with emails
    all_shares = db.query(NoteShare).filter(NoteShare.note_id == note_id).all()
    shares_response = []
    
    for share in all_shares:
        # Get email for each shared user
        shared_email = await get_user_email_by_id(share.shared_with_user_id)
        shares_response.append(ShareResponse(
            id=str(share.id),
            note_id=str(share.note_id),
            shared_by_user_id=share.shared_by_user_id,
            shared_with_user_id=share.shared_with_user_id,
            shared_with_email=shared_email or "Email not found",
            created_at=share.created_at
        ))
    
    return NoteSharesResponse(note_id=str(note_id), shares=shares_response)

@app.get("/notes/{note_id}/shares", response_model=NoteSharesResponse)
async def get_note_shares(note_id: str, request: Request, db: Session = Depends(get_db)):
    """Get all shares for a specific note"""
    user_id = get_current_user_id(request)
    
    # Verify that the note exists and is owned by the current user
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Get all shares for this note
    shares = db.query(NoteShare).filter(NoteShare.note_id == note_id).all()
    shares_response = []
    
    for share in shares:
        # Get email for each shared user
        shared_email = await get_user_email_by_id(share.shared_with_user_id)
        shares_response.append(ShareResponse(
            id=str(share.id),
            note_id=str(share.note_id),
            shared_by_user_id=share.shared_by_user_id,
            shared_with_user_id=share.shared_with_user_id,
            shared_with_email=shared_email or "Email not found",
            created_at=share.created_at
        ))
    
    return NoteSharesResponse(note_id=str(note_id), shares=shares_response)

@app.delete("/notes/{note_id}/shares/{share_id}")
async def remove_note_share(note_id: str, share_id: str, request: Request, db: Session = Depends(get_db)):
    """Remove a specific share from a note"""
    user_id = get_current_user_id(request)
    
    # Verify that the note exists and is owned by the current user
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Find and delete the share
    db_share = db.query(NoteShare).filter(
        NoteShare.id == share_id,
        NoteShare.note_id == note_id
    ).first()
    
    if not db_share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    db.delete(db_share)
    db.commit()
    
    return {"message": "Share removed successfully"}

@app.delete("/notes/{note_id}/shares/by-email/{email}")
async def remove_note_share_by_email(note_id: str, email: str, request: Request, db: Session = Depends(get_db)):
    """Remove a share by email address"""
    user_id = get_current_user_id(request)
    
    # Verify that the note exists and is owned by the current user
    db_note = db.query(Note).filter(
        Note.id == note_id,
        Note.owner_id == user_id,
        ~Note.is_deleted
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Resolve email to user ID
    shared_with_user_id = await get_user_id_by_email(email)
    if not shared_with_user_id:
        raise HTTPException(status_code=404, detail=f"Utente non trovato per l'email: {email}")
    
    # Find and delete the share by user ID
    db_share = db.query(NoteShare).filter(
        NoteShare.note_id == note_id,
        NoteShare.shared_with_user_id == shared_with_user_id
    ).first()
    
    if not db_share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    db.delete(db_share)
    db.commit()
    
    return {"message": "Share removed successfully"}

@app.get("/tags", response_model=List[TagResponse])
async def get_tags(db: Session = Depends(get_db)):
    """Get all available tags"""
    tags = db.query(Tag).all()
    return [TagResponse(id=str(tag.id), name=tag.name) for tag in tags]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
