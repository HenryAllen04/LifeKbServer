# LifeKB Backend Embeddings API
# Purpose: Embedding management endpoints for status monitoring and regeneration

from fastapi import FastAPI, HTTPException, status, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uuid import UUID
from typing import List, Dict, Any
import os
import json
import logging
import asyncio

# Import our app modules
import sys
sys.path.append('/var/task')
from app.models import EmbeddingStatus, APIError
from app.database import db_manager
from app.embeddings import embedding_processor
from app.auth import get_current_user_id
from app.utils import (
    create_error_response, create_success_response, setup_logging, 
    get_client_ip, rate_limiter, TimingContext
)

# Setup logging
setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LifeKB Embeddings API",
    description="Embedding management endpoints for the privacy-first journaling app",
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


async def process_embeddings_background(user_id: UUID, entry_ids: List[str]):
    """Process embeddings for entries in background"""
    try:
        logger.info(f"Starting background embedding processing for {len(entry_ids)} entries")
        
        for entry_id in entry_ids:
            try:
                # Get entry data
                entry_data = await db_manager.get_journal_entry(UUID(entry_id), user_id)
                if not entry_data:
                    logger.warning(f"Entry {entry_id} not found, skipping")
                    continue
                
                # Generate embedding
                with TimingContext(f"embedding_generation_{entry_id}") as timer:
                    embedding = await embedding_processor.process_entry(entry_data["text"])
                
                # Update database
                if embedding:
                    await db_manager.update_embedding(UUID(entry_id), embedding, "completed")
                    logger.info(f"Embedding generated for entry {entry_id} in {timer.duration_ms:.1f}ms")
                else:
                    await db_manager.update_embedding(UUID(entry_id), [], "failed")
                    logger.error(f"Failed to generate embedding for entry {entry_id}")
                
                # Add delay between requests to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing embedding for entry {entry_id}: {str(e)}")
                try:
                    await db_manager.update_embedding(UUID(entry_id), [], "failed")
                except Exception:
                    pass  # Ignore secondary failures
        
        logger.info(f"Background embedding processing completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Background embedding processing failed for user {user_id}: {str(e)}")


@app.get("/status", response_model=EmbeddingStatus)
async def get_embedding_status(
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get embedding generation status for the authenticated user
    
    Args:
        current_user_id: Authenticated user ID
    
    Returns:
        EmbeddingStatus: Summary of embedding generation status
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Getting embedding status for user {current_user_id}")
        
        with TimingContext("embedding_status") as timer:
            status_data = await db_manager.get_embedding_status(current_user_id)
        
        response = EmbeddingStatus(
            total_entries=status_data["total_entries"],
            pending_embeddings=status_data["pending_embeddings"],
            completed_embeddings=status_data["completed_embeddings"],
            failed_embeddings=status_data["failed_embeddings"]
        )
        
        logger.info(f"Embedding status retrieved in {timer.duration_ms:.1f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Error getting embedding status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get embedding status"
        )


@app.post("/regenerate")
async def regenerate_embeddings(
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Regenerate embeddings for all user's journal entries
    
    Args:
        background_tasks: Background task manager
        current_user_id: Authenticated user ID
    
    Returns:
        dict: Status message and task information
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Starting embedding regeneration for user {current_user_id}")
        
        # Get all entries for the user
        with TimingContext("fetch_entries") as timer:
            entries_result = await db_manager.get_journal_entries(
                user_id=current_user_id,
                page=1,
                limit=1000  # Get a large number to cover most users
            )
        
        entry_ids = [entry["id"] for entry in entries_result["items"]]
        total_entries = len(entry_ids)
        
        logger.info(f"Found {total_entries} entries to process in {timer.duration_ms:.1f}ms")
        
        if total_entries == 0:
            return create_success_response(
                {"message": "No entries found to process"},
                "No embeddings to regenerate"
            )
        
        # Mark all entries as pending
        for entry_id in entry_ids:
            try:
                await db_manager.update_embedding(UUID(entry_id), [], "pending")
            except Exception as e:
                logger.warning(f"Failed to mark entry {entry_id} as pending: {str(e)}")
        
        # Schedule background processing
        background_tasks.add_task(process_embeddings_background, current_user_id, entry_ids)
        
        return create_success_response(
            {
                "total_entries": total_entries,
                "status": "processing",
                "message": f"Regenerating embeddings for {total_entries} entries"
            },
            "Embedding regeneration started"
        )
        
    except Exception as e:
        logger.error(f"Error starting embedding regeneration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start embedding regeneration"
        )


@app.post("/process-pending")
async def process_pending_embeddings(
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Process pending embeddings for the authenticated user
    
    Args:
        background_tasks: Background task manager
        current_user_id: Authenticated user ID
    
    Returns:
        dict: Status message and task information
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Processing pending embeddings for user {current_user_id}")
        
        # Get entries without embeddings
        with TimingContext("fetch_pending") as timer:
            pending_entries = await db_manager.get_entries_without_embeddings(
                user_id=current_user_id,
                limit=50  # Process up to 50 entries at a time
            )
        
        entry_ids = [entry["id"] for entry in pending_entries]
        pending_count = len(entry_ids)
        
        logger.info(f"Found {pending_count} pending entries in {timer.duration_ms:.1f}ms")
        
        if pending_count == 0:
            return create_success_response(
                {"message": "No pending embeddings found"},
                "All embeddings are up to date"
            )
        
        # Schedule background processing
        background_tasks.add_task(process_embeddings_background, current_user_id, entry_ids)
        
        return create_success_response(
            {
                "pending_count": pending_count,
                "status": "processing",
                "message": f"Processing {pending_count} pending embeddings"
            },
            "Pending embeddings processing started"
        )
        
    except Exception as e:
        logger.error(f"Error processing pending embeddings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process pending embeddings"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "embeddings",
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