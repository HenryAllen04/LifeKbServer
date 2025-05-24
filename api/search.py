# LifeKB Backend Search API
# Purpose: Semantic search endpoint for AI-powered journal entry search

from fastapi import FastAPI, HTTPException, status, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uuid import UUID
from typing import List, Optional
import os
import json
import logging
import time

# Import our app modules
import sys
sys.path.append('/var/task')
from app.models import SearchRequest, SearchResponse, SearchResult, APIError
from app.database import db_manager
from app.embeddings import embedding_manager
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
    title="LifeKB Search API",
    description="Semantic search endpoints for the privacy-first journaling app",
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


@app.post("/", response_model=SearchResponse)
async def semantic_search(
    search_request: SearchRequest,
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Perform semantic search across user's journal entries
    
    Args:
        search_request: Search query and parameters
        current_user_id: Authenticated user ID
    
    Returns:
        SearchResponse: Search results with similarity scores and metadata
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    search_start_time = time.time()
    
    try:
        logger.info(f"Semantic search for user {current_user_id}: '{search_request.query}'")
        
        # Generate embedding for search query
        with TimingContext("query_embedding") as embedding_timer:
            query_embedding = await embedding_manager.search_embedding(search_request.query)
        
        logger.info(f"Query embedding generated in {embedding_timer.duration_ms:.1f}ms")
        
        # Perform semantic search in database
        with TimingContext("database_search") as search_timer:
            search_results = await db_manager.search_entries(
                user_id=current_user_id,
                query_embedding=query_embedding,
                similarity_threshold=search_request.similarity_threshold,
                limit=search_request.limit
            )
        
        logger.info(f"Database search completed in {search_timer.duration_ms:.1f}ms")
        
        # Convert to response models
        results = []
        for result in search_results:
            search_result = SearchResult(
                id=UUID(result["id"]),
                text=result["text"],
                created_at=result["created_at"],
                similarity=result["similarity"]
            )
            results.append(search_result)
        
        # Calculate total search time
        search_time_ms = (time.time() - search_start_time) * 1000
        
        response = SearchResponse(
            results=results,
            total_count=len(results),
            query=search_request.query,
            search_time_ms=search_time_ms
        )
        
        logger.info(f"Search completed: {len(results)} results in {search_time_ms:.1f}ms")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing semantic search: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search service unavailable"
        )


@app.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1, max_length=100, description="Partial search query"),
    limit: int = Query(5, ge=1, le=10, description="Number of suggestions"),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Get search suggestions based on user's journal content
    
    Args:
        query: Partial search query
        limit: Maximum number of suggestions
        current_user_id: Authenticated user ID
    
    Returns:
        dict: List of search suggestions
        
    Raises:
        HTTPException: 500 for server errors
    """
    try:
        logger.info(f"Search suggestions for user {current_user_id}: '{query}'")
        
        # For now, return a simple keyword-based suggestion
        # In a more advanced implementation, this could use:
        # - Common keywords from user's entries
        # - Recent search history
        # - AI-generated query suggestions
        
        suggestions = []
        
        # Simple keyword-based suggestions (this is a placeholder)
        query_lower = query.lower()
        common_topics = [
            "feelings", "work", "family", "goals", "thoughts", "dreams",
            "memories", "plans", "emotions", "relationships", "creativity",
            "challenges", "achievements", "reflections", "insights"
        ]
        
        for topic in common_topics:
            if query_lower in topic or topic.startswith(query_lower):
                suggestions.append(topic)
                if len(suggestions) >= limit:
                    break
        
        # If no topic matches, suggest completing the query
        if not suggestions and len(query) > 2:
            suggestions.append(query + " feelings")
            suggestions.append(query + " thoughts")
            suggestions.append(query + " experience")
        
        return create_success_response({
            "suggestions": suggestions[:limit],
            "query": query
        })
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Suggestions service unavailable"
        )


@app.get("/similar/{entry_id}")
async def find_similar_entries(
    entry_id: UUID,
    limit: int = Query(5, ge=1, le=20, description="Number of similar entries"),
    similarity_threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score"),
    current_user_id: UUID = Depends(get_current_user_id)
):
    """
    Find entries similar to a specific entry
    
    Args:
        entry_id: Reference entry UUID
        limit: Maximum number of similar entries
        similarity_threshold: Minimum similarity score
        current_user_id: Authenticated user ID
    
    Returns:
        dict: List of similar entries
        
    Raises:
        HTTPException: 404 if entry not found, 500 for server errors
    """
    try:
        logger.info(f"Finding similar entries to {entry_id} for user {current_user_id}")
        
        # Get the reference entry
        reference_entry = await db_manager.get_journal_entry(entry_id, current_user_id)
        if not reference_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reference entry not found"
            )
        
        # Check if entry has embedding
        if not reference_entry.get("embedding"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference entry does not have embedding generated yet"
            )
        
        # Search for similar entries using the reference entry's embedding
        with TimingContext("similarity_search") as timer:
            similar_results = await db_manager.search_entries(
                user_id=current_user_id,
                query_embedding=reference_entry["embedding"],
                similarity_threshold=similarity_threshold,
                limit=limit + 1  # +1 to exclude the reference entry itself
            )
        
        # Filter out the reference entry itself
        filtered_results = [
            result for result in similar_results 
            if result["id"] != str(entry_id)
        ][:limit]
        
        # Convert to response format
        similar_entries = []
        for result in filtered_results:
            similar_entry = SearchResult(
                id=UUID(result["id"]),
                text=result["text"],
                created_at=result["created_at"],
                similarity=result["similarity"]
            )
            similar_entries.append(similar_entry)
        
        logger.info(f"Found {len(similar_entries)} similar entries in {timer.duration_ms:.1f}ms")
        
        return create_success_response({
            "similar_entries": [entry.dict() for entry in similar_entries],
            "reference_entry_id": str(entry_id),
            "count": len(similar_entries)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Similar entries service unavailable"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "search",
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