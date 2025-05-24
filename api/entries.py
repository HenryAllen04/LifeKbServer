# LifeKB Backend Entries API
# Purpose: Journal entry CRUD endpoints with AI embedding generation

from fastapi import FastAPI, HTTPException, status, Request, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uuid import UUID
from typing import Optional
import os
import json
import logging
import asyncio

# Import our app modules
import sys
sys.path.append('/var/task')
from app.models import (
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, 
    PaginatedResponse, PaginationParams, APIError
)
from app.database import db_manager
from app.embeddings import embedding_processor
from app.auth import get_current_user_id
from app.utils import (
    create_error_response, create_success_response, setup_logging, 
    get_client_ip, rate_limiter, TimingContext, sanitize_text
)

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LifeKB Entries API",
    description="Journal entry management endpoints for the privacy-first journaling app",
    version="1.0.0"
)

# CORS middleware
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = get_client_ip(request)
    
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    response = await call_next(request)
    return response


async def generate_embedding_background(entry_id: UUID, text: str):
    """Generate embedding for entry in background"""
    try:
        with TimingContext("embedding_generation") as timer:
            embedding = await embedding_processor.process_entry(text)
        
        if embedding:
            await db_manager.update_embedding(entry_id, embedding, "completed")
            logger.info(f"Embedding generated for entry {entry_id} in {timer.duration_ms:.1f}ms")
        else:
            await db_manager.update_embedding(entry_id, [], "failed")
            logger.error(f"Failed to generate embedding for entry {entry_id}")
            
    except Exception as e:
        logger.error(f"Background embedding generation failed for entry {entry_id}: {str(e)}")
        try:
            await db_manager.update_embedding(entry_id, [], "failed")
        except Exception:
            pass  # Ignore secondary failures


@app.post("/", response_model=JournalEntryResponse)
async def create_entry(
    entry: JournalEntryCreate,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Create a new journal entry
    
    Args:
        entry: Journal entry content
        background_tasks: Background task manager for embedding generation
        current_user_id: Authenticated user ID
    
    Returns:
        JournalEntryResponse: Created entry with metadata
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        logger.info(f"Creating journal entry for user {current_user_id}")
        
        # Sanitize text input
        cleaned_text = sanitize_text(entry.text)
        if not cleaned_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Entry text cannot be empty"
            )
        
        # Create entry in database
        with TimingContext("database_create") as timer:
            entry_data = await db_manager.create_journal_entry(
                user_id=current_user_id,
                text=cleaned_text
            )
        
        logger.info(f"Entry created in {timer.duration_ms:.1f}ms")
        
        # Schedule embedding generation in background
        entry_id = UUID(entry_data["id"])
        background_tasks.add_task(generate_embedding_background, entry_id, cleaned_text)
        
        # Convert to response model
        response = JournalEntryResponse(**entry_data)
        
        logger.info(f"Successfully created entry {entry_id} for user {current_user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating journal entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journal entry"
        )


@app.get("/", response_model=PaginatedResponse)
async def get_entries(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get paginated journal entries for the authenticated user
    
    Args:
        page: Page number (1-based)
        limit: Number of entries per page
        current_user_id: Authenticated user ID
    
    Returns:
        PaginatedResponse: Paginated list of journal entries
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Fetching entries for user {current_user_id}, page {page}")
        
        with TimingContext("database_fetch") as timer:
            result = await db_manager.get_journal_entries(
                user_id=current_user_id,
                page=page,
                limit=limit
            )
        
        logger.info(f"Fetched {len(result['items'])} entries in {timer.duration_ms:.1f}ms")
        
        # Convert to response models
        entries = [JournalEntryResponse(**item) for item in result["items"]]
        
        response = PaginatedResponse(
            items=entries,
            total_count=result["total_count"],
            page=result["page"],
            limit=result["limit"],
            total_pages=result["total_pages"]
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching journal entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch journal entries"
        )


@app.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry(
    entry_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get a specific journal entry
    
    Args:
        entry_id: Entry UUID
        current_user_id: Authenticated user ID
    
    Returns:
        JournalEntryResponse: Journal entry data
        
    Raises:
        HTTPException: 404 if entry not found, 500 for server errors
    """
    try:
        logger.info(f"Fetching entry {entry_id} for user {current_user_id}")
        
        entry_data = await db_manager.get_journal_entry(entry_id, current_user_id)
        
        if not entry_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        response = JournalEntryResponse(**entry_data)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching journal entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch journal entry"
        )


@app.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(
    entry_id: UUID,
    entry_update: JournalEntryUpdate,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Update a journal entry
    
    Args:
        entry_id: Entry UUID
        entry_update: Updated entry data
        background_tasks: Background task manager for embedding generation
        current_user_id: Authenticated user ID
    
    Returns:
        JournalEntryResponse: Updated entry data
        
    Raises:
        HTTPException: 404 if entry not found, 400 for validation errors
    """
    try:
        logger.info(f"Updating entry {entry_id} for user {current_user_id}")
        
        # Sanitize text input
        if entry_update.text is not None:
            cleaned_text = sanitize_text(entry_update.text)
            if not cleaned_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entry text cannot be empty"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )
        
        # Update entry in database
        with TimingContext("database_update") as timer:
            updated_data = await db_manager.update_journal_entry(
                entry_id=entry_id,
                user_id=current_user_id,
                text=cleaned_text
            )
        
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        logger.info(f"Entry updated in {timer.duration_ms:.1f}ms")
        
        # Schedule embedding regeneration in background
        background_tasks.add_task(generate_embedding_background, entry_id, cleaned_text)
        
        response = JournalEntryResponse(**updated_data)
        
        logger.info(f"Successfully updated entry {entry_id} for user {current_user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating journal entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update journal entry"
        )


@app.delete("/{entry_id}")
async def delete_entry(
    entry_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Delete a journal entry
    
    Args:
        entry_id: Entry UUID
        current_user_id: Authenticated user ID
    
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: 404 if entry not found, 500 for server errors
    """
    try:
        logger.info(f"Deleting entry {entry_id} for user {current_user_id}")
        
        with TimingContext("database_delete") as timer:
            deleted = await db_manager.delete_journal_entry(entry_id, current_user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )
        
        logger.info(f"Entry deleted in {timer.duration_ms:.1f}ms")
        
        return create_success_response(
            {"deleted": True, "entry_id": str(entry_id)},
            "Journal entry deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting journal entry: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete journal entry"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "entries",
        "version": "1.0.0"
    }


# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=create_error_response(
            "validation_error",
            "Invalid request data",
            {"errors": exc.errors()}
        )
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return HTTPException(
        status_code=exc.status_code,
        detail=create_error_response(
            "http_error",
            exc.detail,
            {"status_code": exc.status_code}
        )
    )


# Main handler for Vercel
def handler(event, context):
    """Vercel serverless function handler"""
    import uvicorn
    return uvicorn.run(app, host="0.0.0.0", port=8000) 