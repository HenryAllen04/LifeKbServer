# LifeKB Backend Database
# Purpose: Supabase connection, queries, and database operations for journal entries

import os
import asyncio
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for Supabase operations"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing required Supabase environment variables")
        
        # Create Supabase client with service role key for server-side operations
        self.client: Client = create_client(
            self.supabase_url, 
            self.supabase_key,
            options=ClientOptions(
                postgrest_client_timeout=10,
                storage_client_timeout=10
            )
        )
    
    async def create_journal_entry(
        self, 
        user_id: UUID, 
        text: str, 
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Create a new journal entry"""
        try:
            entry_data = {
                "user_id": str(user_id),
                "text": text,
                "embedding_status": "completed" if embedding else "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if embedding:
                entry_data["embedding"] = embedding
            
            result = self.client.table("journal_entries").insert(entry_data).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("Failed to create journal entry")
                
        except Exception as e:
            logger.error(f"Error creating journal entry: {str(e)}")
            raise
    
    async def get_journal_entries(
        self, 
        user_id: UUID, 
        page: int = 1, 
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get paginated journal entries for a user"""
        try:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Get entries with pagination
            result = self.client.table("journal_entries")\
                .select("*")\
                .eq("user_id", str(user_id))\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            # Get total count
            count_result = self.client.table("journal_entries")\
                .select("id", count="exact")\
                .eq("user_id", str(user_id))\
                .execute()
            
            total_count = count_result.count if count_result.count else 0
            total_pages = (total_count + limit - 1) // limit
            
            return {
                "items": result.data,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }
            
        except Exception as e:
            logger.error(f"Error getting journal entries: {str(e)}")
            raise
    
    async def get_journal_entry(self, entry_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get a specific journal entry"""
        try:
            result = self.client.table("journal_entries")\
                .select("*")\
                .eq("id", str(entry_id))\
                .eq("user_id", str(user_id))\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting journal entry: {str(e)}")
            raise
    
    async def update_journal_entry(
        self, 
        entry_id: UUID, 
        user_id: UUID, 
        text: str,
        embedding: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a journal entry"""
        try:
            update_data = {
                "text": text,
                "updated_at": datetime.utcnow().isoformat(),
                "embedding_status": "completed" if embedding else "pending"
            }
            
            if embedding:
                update_data["embedding"] = embedding
            
            result = self.client.table("journal_entries")\
                .update(update_data)\
                .eq("id", str(entry_id))\
                .eq("user_id", str(user_id))\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error updating journal entry: {str(e)}")
            raise
    
    async def delete_journal_entry(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete a journal entry"""
        try:
            result = self.client.table("journal_entries")\
                .delete()\
                .eq("id", str(entry_id))\
                .eq("user_id", str(user_id))\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error deleting journal entry: {str(e)}")
            raise
    
    async def search_entries(
        self, 
        user_id: UUID, 
        query_embedding: List[float],
        similarity_threshold: float = 0.1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform semantic search on journal entries"""
        try:
            # Call the search function defined in the database
            result = self.client.rpc(
                "search_entries",
                {
                    "query_embedding": query_embedding,
                    "target_user_id": str(user_id),
                    "similarity_threshold": similarity_threshold,
                    "limit_count": limit
                }
            ).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            raise
    
    async def get_embedding_status(self, user_id: UUID) -> Dict[str, Any]:
        """Get embedding generation status for a user"""
        try:
            result = self.client.table("journal_entries")\
                .select("embedding_status")\
                .eq("user_id", str(user_id))\
                .execute()
            
            if not result.data:
                return {
                    "total_entries": 0,
                    "pending_embeddings": 0,
                    "completed_embeddings": 0,
                    "failed_embeddings": 0
                }
            
            status_counts = {}
            for entry in result.data:
                status = entry["embedding_status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_entries": len(result.data),
                "pending_embeddings": status_counts.get("pending", 0),
                "completed_embeddings": status_counts.get("completed", 0),
                "failed_embeddings": status_counts.get("failed", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding status: {str(e)}")
            raise
    
    async def update_embedding(
        self, 
        entry_id: UUID, 
        embedding: List[float], 
        status: str = "completed"
    ) -> bool:
        """Update an entry's embedding"""
        try:
            result = self.client.table("journal_entries")\
                .update({
                    "embedding": embedding,
                    "embedding_status": status,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("id", str(entry_id))\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error updating embedding: {str(e)}")
            raise
    
    async def get_entries_without_embeddings(self, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get entries that need embeddings generated"""
        try:
            result = self.client.table("journal_entries")\
                .select("id", "text")\
                .eq("user_id", str(user_id))\
                .eq("embedding_status", "pending")\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting entries without embeddings: {str(e)}")
            raise


# Global database manager instance
db_manager = DatabaseManager()

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Initialize and return Supabase client with environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    
    return create_client(url, key)

# Global client instance
supabase: Client = get_supabase_client()

class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass

def handle_supabase_error(response) -> None:
    """Handle Supabase API errors and raise appropriate exceptions."""
    if hasattr(response, 'error') and response.error:
        error_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
        raise DatabaseError(f"Database error: {error_msg}")

async def test_connection() -> Dict[str, Any]:
    """Test database connection and return basic info."""
    try:
        # Simple query to test connection
        response = supabase.table('journal_entries').select('count', count='exact').execute()
        handle_supabase_error(response)
        
        return {
            "status": "connected",
            "url": os.environ.get("SUPABASE_URL"),
            "table_exists": True
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": os.environ.get("SUPABASE_URL")
        } 