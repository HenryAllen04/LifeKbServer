# LifeKB Backend Models
# Purpose: Pydantic request/response models for API validation and serialization

from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class UserBase(BaseModel):
    """Base user model"""
    email: str
    

class UserCreate(UserBase):
    """User creation model"""
    password: str


class UserResponse(UserBase):
    """User response model"""
    id: UUID
    created_at: datetime


class EntryCategory(str, Enum):
    """Predefined journal entry categories"""
    PERSONAL = "personal"
    WORK = "work"
    TRAVEL = "travel"
    HEALTH = "health"
    RELATIONSHIPS = "relationships"
    GOALS = "goals"
    GRATITUDE = "gratitude"
    REFLECTION = "reflection"
    LEARNING = "learning"
    CREATIVITY = "creativity"
    OTHER = "other"


class JournalEntryBase(BaseModel):
    """Base journal entry model"""
    text: str = Field(..., min_length=1, max_length=10000, description="Journal entry content")
    tags: Optional[List[str]] = Field(default=None, max_items=20, description="Entry tags")
    category: Optional[EntryCategory] = Field(default=None, description="Entry category")
    mood: Optional[int] = Field(default=None, ge=1, le=10, description="Mood rating from 1-10")
    location: Optional[str] = Field(default=None, max_length=255, description="Location where entry was written")
    weather: Optional[str] = Field(default=None, max_length=50, description="Weather conditions")


class JournalEntryCreate(JournalEntryBase):
    """Journal entry creation model"""
    pass


class JournalEntryUpdate(BaseModel):
    """Journal entry update model"""
    text: Optional[str] = Field(None, min_length=1, max_length=10000)
    tags: Optional[List[str]] = Field(default=None, max_items=20, description="Entry tags")
    category: Optional[EntryCategory] = Field(default=None, description="Entry category")
    mood: Optional[int] = Field(default=None, ge=1, le=10, description="Mood rating from 1-10")
    location: Optional[str] = Field(default=None, max_length=255, description="Location where entry was written")
    weather: Optional[str] = Field(default=None, max_length=50, description="Weather conditions")


class JournalEntryResponse(JournalEntryBase):
    """Journal entry response model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    embedding_status: str = Field(default="pending", description="Status of embedding generation")
    created_at: datetime
    updated_at: datetime


class MetadataFilterRequest(BaseModel):
    """Metadata filtering for search and entries"""
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    category: Optional[EntryCategory] = Field(default=None, description="Filter by category")
    min_mood: Optional[int] = Field(default=None, ge=1, le=10, description="Minimum mood rating")
    max_mood: Optional[int] = Field(default=None, ge=1, le=10, description="Maximum mood rating")
    location: Optional[str] = Field(default=None, description="Filter by location")
    weather: Optional[str] = Field(default=None, description="Filter by weather")


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: Optional[int] = Field(default=10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: Optional[float] = Field(default=0.1, ge=0.0, le=1.0, description="Minimum similarity score")
    filters: Optional[MetadataFilterRequest] = Field(default=None, description="Metadata filters")


class SearchResult(BaseModel):
    """Individual search result model"""
    id: UUID
    text: str
    tags: Optional[List[str]] = None
    category: Optional[EntryCategory] = None
    mood: Optional[int] = None
    location: Optional[str] = None
    weather: Optional[str] = None
    created_at: datetime
    similarity: float = Field(..., description="Similarity score between 0 and 1")


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[SearchResult]
    total_count: int
    query: str
    search_time_ms: float
    filters_applied: Optional[MetadataFilterRequest] = None


class AuthTokens(BaseModel):
    """Authentication tokens model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request model"""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


class EmbeddingStatus(BaseModel):
    """Embedding generation status model"""
    total_entries: int
    pending_embeddings: int
    completed_embeddings: int
    failed_embeddings: int
    entries_with_tags: Optional[int] = 0
    entries_with_category: Optional[int] = 0
    entries_with_mood: Optional[int] = 0
    average_mood: Optional[float] = None
    last_updated: Optional[datetime] = None


class UserMetadataStats(BaseModel):
    """User metadata statistics model"""
    popular_tags: List[dict] = Field(default=[], description="Popular tags with usage counts")
    popular_categories: List[dict] = Field(default=[], description="Popular categories with usage counts")
    mood_trend: Optional[float] = Field(default=None, description="Average mood rating")
    total_tagged_entries: int = Field(default=0, description="Number of entries with tags")
    total_categorized_entries: int = Field(default=0, description="Number of entries with categories")


class APIError(BaseModel):
    """API error response model"""
    error: str
    message: str
    details: Optional[dict] = None


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Union[JournalEntryResponse]]
    total_count: int
    page: int
    limit: int
    total_pages: int 