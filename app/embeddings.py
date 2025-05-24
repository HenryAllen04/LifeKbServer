# LifeKB Backend Embeddings
# Purpose: OpenAI integration for generating text embeddings for semantic search

import os
import asyncio
import time
from typing import List, Optional
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manager for OpenAI embeddings generation"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing OPENAI_API_KEY environment variable")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            # Clean and truncate text if necessary
            cleaned_text = self._clean_text(text)
            
            # Generate embedding
            response = await self.client.embeddings.create(
                model=self.model,
                input=cleaned_text,
                dimensions=self.dimensions
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        try:
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Generate embeddings in batch
            response = await self.client.embeddings.create(
                model=self.model,
                input=cleaned_texts,
                dimensions=self.dimensions
            )
            
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding generation"""
        # Remove excessive whitespace
        cleaned = ' '.join(text.split())
        
        # Truncate if too long (OpenAI has token limits)
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = 8000 * 4  # Conservative limit for 8k tokens
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars]
            logger.warning(f"Text truncated to {max_chars} characters")
        
        return cleaned
    
    async def search_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query"""
        return await self.generate_embedding(query)


class EmbeddingProcessor:
    """Processor for handling embedding generation with rate limiting and retries"""
    
    def __init__(self, embedding_manager: EmbeddingManager):
        self.embedding_manager = embedding_manager
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.batch_size = 10
    
    async def process_entry(self, text: str, max_retries: Optional[int] = None) -> Optional[List[float]]:
        """Process a single entry with retry logic"""
        retries = max_retries or self.max_retries
        
        for attempt in range(retries):
            try:
                return await self.embedding_manager.generate_embedding(text)
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Embedding generation failed, retrying in {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Embedding generation failed after {retries} attempts: {str(e)}")
                    return None
    
    async def process_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Process multiple entries in batch with error handling"""
        try:
            embeddings = await self.embedding_manager.generate_embeddings_batch(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding generation failed, falling back to individual processing: {str(e)}")
            
            # Fallback to individual processing
            results = []
            for text in texts:
                embedding = await self.process_entry(text)
                results.append(embedding)
            
            return results
    
    async def process_entries_chunked(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Process entries in chunks to respect rate limits"""
        all_results = []
        
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            
            # Add delay between chunks to respect rate limits
            if i > 0:
                await asyncio.sleep(0.5)
            
            chunk_results = await self.process_batch(chunk)
            all_results.extend(chunk_results)
        
        return all_results


# Global embedding manager and processor instances
embedding_manager = EmbeddingManager()
embedding_processor = EmbeddingProcessor(embedding_manager) 