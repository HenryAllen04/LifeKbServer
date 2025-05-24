# LifeKB Backend Embeddings
# Purpose: OpenAI integration for generating text embeddings and semantic search

import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
import openai
from .database import db_manager

logger = logging.getLogger(__name__)

class EmbeddingsError(Exception):
    """Custom exception for embedding generation errors."""
    pass

class EmbeddingsManager:
    """Manager for OpenAI embeddings generation and processing"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment")
        
        # Initialize OpenAI client
        openai.api_key = self.api_key
        
        # Embedding model configuration
        self.model = "text-embedding-ada-002"  # OpenAI's latest embedding model
        self.max_tokens = 8000  # Token limit for the model
        self.embedding_dimension = 1536  # Ada-002 produces 1536-dimensional embeddings
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text using OpenAI API."""
        try:
            if not text or not text.strip():
                raise EmbeddingsError("Text cannot be empty")
            
            # Truncate text if too long (rough estimate: 1 token ≈ 4 characters)
            if len(text) > self.max_tokens * 4:
                text = text[:self.max_tokens * 4]
                logger.warning(f"Text truncated to {len(text)} characters for embedding")
            
            # Generate embedding using OpenAI API
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: openai.Embedding.create(
                    input=text,
                    model=self.model
                )
            )
            
            if not response.data or len(response.data) == 0:
                raise EmbeddingsError("No embedding data received from OpenAI")
            
            embedding = response.data[0].embedding
            
            # Validate embedding dimension
            if len(embedding) != self.embedding_dimension:
                raise EmbeddingsError(f"Unexpected embedding dimension: {len(embedding)}")
            
            return embedding
            
        except openai.error.RateLimitError:
            raise EmbeddingsError("OpenAI rate limit exceeded")
        except openai.error.AuthenticationError:
            raise EmbeddingsError("OpenAI authentication failed")
        except openai.error.APIError as e:
            raise EmbeddingsError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise EmbeddingsError(f"Embedding generation failed: {str(e)}")
    
    async def generate_and_store_embedding(self, entry_id: UUID, text: str) -> bool:
        """Generate embedding for text and store it in the database."""
        try:
            # Generate embedding
            embedding = await self.generate_embedding(text)
            
            # Store in database
            success = await db_manager.update_embedding(entry_id, embedding, "completed")
            
            if success:
                logger.info(f"Embedding generated and stored for entry {entry_id}")
            else:
                logger.error(f"Failed to store embedding for entry {entry_id}")
            
            return success
            
        except EmbeddingsError:
            # Mark as failed in database
            await db_manager.update_embedding(entry_id, [], "failed")
            raise
        except Exception as e:
            logger.error(f"Error in generate_and_store_embedding: {str(e)}")
            await db_manager.update_embedding(entry_id, [], "failed")
            raise EmbeddingsError(f"Failed to generate and store embedding: {str(e)}")
    
    async def process_pending_embeddings(self, user_id: UUID, limit: int = 5) -> Dict[str, Any]:
        """Process pending embeddings for a user (batch processing)."""
        try:
            # Get entries without embeddings
            pending_entries = await db_manager.get_entries_without_embeddings(user_id, limit)
            
            if not pending_entries:
                return {
                    "processed": 0,
                    "total_pending": 0,
                    "message": "No pending embeddings"
                }
            
            processed_count = 0
            failed_count = 0
            
            for entry in pending_entries:
                try:
                    entry_id = UUID(entry["id"])
                    text = entry["text"]
                    
                    success = await self.generate_and_store_embedding(entry_id, text)
                    if success:
                        processed_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process embedding for entry {entry.get('id')}: {str(e)}")
                    failed_count += 1
            
            return {
                "processed": processed_count,
                "failed": failed_count,
                "total_pending": len(pending_entries),
                "message": f"Processed {processed_count} embeddings, {failed_count} failed"
            }
            
        except Exception as e:
            logger.error(f"Error processing pending embeddings: {str(e)}")
            raise EmbeddingsError(f"Batch processing failed: {str(e)}")
    
    async def search_similar_entries(
        self, 
        user_id: UUID, 
        query_text: str, 
        limit: int = 10,
        similarity_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Search for similar entries using semantic search."""
        try:
            # Generate embedding for search query
            query_embedding = await self.generate_embedding(query_text)
            
            # Perform similarity search
            results = await db_manager.search_entries(
                user_id, 
                query_embedding, 
                similarity_threshold, 
                limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            raise EmbeddingsError(f"Semantic search failed: {str(e)}")
    
    async def get_embedding_status(self, user_id: UUID) -> Dict[str, Any]:
        """Get embedding generation status for a user."""
        try:
            status = await db_manager.get_embedding_status(user_id)
            
            # Calculate completion percentage
            total = status["total_entries"]
            completed = status["completed_embeddings"]
            
            completion_percentage = (completed / total * 100) if total > 0 else 100
            
            return {
                **status,
                "completion_percentage": round(completion_percentage, 1),
                "needs_processing": status["pending_embeddings"] > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding status: {str(e)}")
            raise EmbeddingsError(f"Failed to get embedding status: {str(e)}")


# Global embeddings manager instance
embeddings_manager = EmbeddingsManager()


async def auto_generate_embedding(entry_id: UUID, text: str) -> bool:
    """Automatically generate embedding for a new entry (called after entry creation)."""
    try:
        return await embeddings_manager.generate_and_store_embedding(entry_id, text)
    except Exception as e:
        logger.error(f"Auto-embedding generation failed for entry {entry_id}: {str(e)}")
        return False 