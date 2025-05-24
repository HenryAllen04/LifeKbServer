# LifeKB Backend Models
# Purpose: Pydantic request/response models for API validation and serialization

from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


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


class JournalEntryBase(BaseModel):
    """Base journal entry model"""
    text: str = Field(..., min_length=1, max_length=10000, description="Journal entry content")


class JournalEntryCreate(JournalEntryBase):
    """Journal entry creation model"""
    pass


class JournalEntryUpdate(BaseModel):
    """Journal entry update model"""
    text: Optional[str] = Field(None, min_length=1, max_length=10000)


class JournalEntryResponse(JournalEntryBase):
    """Journal entry response model"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    embedding_status: str = Field(default="pending", description="Status of embedding generation")
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: Optional[int] = Field(default=10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: Optional[float] = Field(default=0.1, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    """Individual search result model"""
    id: UUID
    text: str
    created_at: datetime
    similarity: float = Field(..., description="Similarity score between 0 and 1")


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[SearchResult]
    total_count: int
    query: str
    search_time_ms: float


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
    last_updated: Optional[datetime] = None


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