# LifeKB Backend Search API - Vercel Serverless Function
# Purpose: Semantic search operations using OpenAI embeddings with metadata filtering

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import sys
import asyncio
from datetime import datetime
from uuid import UUID
from typing import List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from app modules
try:
    from app.embeddings import embeddings_manager, EmbeddingsError
except ImportError:
    embeddings_manager = None
    EmbeddingsError = Exception

# Import monitoring and security
from app.monitoring import performance_monitor, rate_limiter, create_logger

# Supabase imports
from supabase import create_client, Client

logger = create_logger("search_api")

def get_supabase_client():
    """Initialize and return Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    
    return create_client(url, key)

def serialize_datetime(obj):
    """Convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):  # Handle other datetime-like objects
        return obj.isoformat()
    return obj

def serialize_data(data):
    """Recursively serialize datetime objects in data."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            try:
                result[key] = serialize_data(value)
            except Exception as e:
                # Convert problematic values to strings
                result[key] = str(value)
        return result
    elif isinstance(data, list):
        return [serialize_data(item) for item in data]
    else:
        return serialize_datetime(data)

class AuthError(Exception):
    """Custom exception for authentication errors."""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

def get_user_from_token(token: str):
    """Get user data from JWT token."""
    try:
        supabase = get_supabase_client()
        response = supabase.auth.get_user(token)
        
        if not response.user:
            raise AuthError("Invalid token")
        
        return response.user
    except Exception as e:
        raise AuthError(f"Authentication failed: {str(e)}")

@rate_limiter.limit_requests(max_requests=50, window_minutes=1)  # 50 searches per minute
@performance_monitor.track_request("/api/search", "POST")
async def perform_semantic_search_with_metadata(
    user_id: str, 
    query: str, 
    limit: int = 10, 
    similarity_threshold: float = 0.1,
    filter_tags: Optional[List[str]] = None,
    filter_category: Optional[str] = None,
    min_mood: Optional[int] = None,
    max_mood: Optional[int] = None
):
    """Perform semantic search with metadata filtering."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available")
        
        # First generate query embedding
        query_embedding = await embeddings_manager.generate_embedding(query)
        
        # Use the metadata search function directly
        supabase = get_supabase_client()
        
        # Call the search_entries_with_metadata function
        result = supabase.rpc('search_entries_with_metadata', {
            'query_embedding': query_embedding,
            'target_user_id': user_id,
            'similarity_threshold': similarity_threshold,
            'limit_count': limit,
            'filter_tags': filter_tags,
            'filter_category': filter_category,
            'min_mood': min_mood,
            'max_mood': max_mood
        }).execute()
        
        # Format results
        search_results = []
        if result.data:
            for row in result.data:
                search_results.append({
                    "id": row["id"],
                    "text": row["text"],
                    "tags": row["tags"],
                    "category": row["category"],
                    "mood": row["mood"],
                    "location": row["location"],
                    "weather": row["weather"],
                    "created_at": row["created_at"],
                    "similarity": float(row["similarity"])
                })
        
        logger.info("Semantic search with metadata completed", 
                   user_id=user_id, query_length=len(query), 
                   results_count=len(search_results), 
                   has_filters=bool(filter_tags or filter_category or min_mood or max_mood))
        
        return serialize_data(search_results)
        
    except Exception as e:
        logger.error("Search with metadata failed", user_id=user_id, error=str(e))
        raise Exception(f"Search failed: {str(e)}")

async def perform_semantic_search(user_id: str, query: str, limit: int = 10, similarity_threshold: float = 0.1):
    """Perform basic semantic search (backward compatibility)."""
    return await perform_semantic_search_with_metadata(
        user_id, query, limit, similarity_threshold
    )

@rate_limiter.limit_requests(max_requests=10, window_minutes=1)  # 10 processing requests per minute
@performance_monitor.track_request("/api/search", "GET")
async def process_pending_embeddings(user_id: str, limit: int = 5):
    """Process pending embeddings for a user."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available")
        
        user_uuid = UUID(user_id)
        result = await embeddings_manager.process_pending_embeddings(user_uuid, limit)
        
        logger.info("Pending embeddings processed", user_id=user_id, processed_count=limit)
        
        return serialize_data(result)
        
    except EmbeddingsError as e:
        logger.error("Embedding processing failed", user_id=user_id, error=str(e))
        raise Exception(f"Embedding processing error: {str(e)}")
    except Exception as e:
        logger.error("Processing failed", user_id=user_id, error=str(e))
        raise Exception(f"Processing failed: {str(e)}")

@performance_monitor.track_request("/api/search", "GET")
async def get_embedding_status(user_id: str):
    """Get embedding generation status for a user."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available")
        
        user_uuid = UUID(user_id)
        status = await embeddings_manager.get_embedding_status(user_uuid)
        
        return serialize_data(status)
        
    except EmbeddingsError as e:
        logger.error("Status check failed", user_id=user_id, error=str(e))
        raise Exception(f"Status error: {str(e)}")
    except Exception as e:
        logger.error("Status check failed", user_id=user_id, error=str(e))
        raise Exception(f"Status check failed: {str(e)}")

class handler(BaseHTTPRequestHandler):
    def send_json_response(self, status_code: int, data: dict):
        """Helper to send JSON responses with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def get_request_body(self) -> dict:
        """Parse JSON request body."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            
            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))
        except (json.JSONDecodeError, ValueError):
            logger.warn("Failed to parse request body")
            return {}

    def get_user_id(self) -> str:
        """Extract and validate user ID from JWT token."""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise AuthError('Missing or invalid Authorization header')
        
        token = auth_header.replace('Bearer ', '')
        user = get_user_from_token(token)
        
        return str(user.id)

    def do_GET(self):
        """Handle GET requests - embedding status and processing."""
        try:
            user_id = self.get_user_id()
            
            parsed_url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_url.query)
            
            # Check for specific actions
            action = query.get('action', [None])[0]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if action == 'status':
                # Get embedding status
                result = loop.run_until_complete(get_embedding_status(user_id))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'status': result
                })
            elif action == 'process':
                # Process pending embeddings
                limit = int(query.get('limit', [5])[0])
                result = loop.run_until_complete(process_pending_embeddings(user_id, limit))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'processing_result': result
                })
            else:
                # Default API info
                loop.close()
                self.send_json_response(200, {
                    'message': 'LifeKB Search API with Metadata Filtering',
                    'version': '2.0.0',
                    'endpoints': {
                        'GET': [
                            '?action=status - Get embedding status',
                            '?action=process - Process pending embeddings'
                        ],
                        'POST': [
                            'Search entries with semantic similarity and metadata filters',
                            'Supports: tags, category, mood range filtering'
                        ]
                    },
                    'features': [
                        'Semantic search with OpenAI embeddings',
                        'Tag-based filtering',
                        'Category filtering',
                        'Mood range filtering',
                        'Location and weather filtering',
                        'Real-time processing status'
                    ],
                    'status': 'running'
                })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
            logger.error("GET request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_POST(self):
        """Handle POST requests - semantic search with metadata filtering."""
        try:
            user_id = self.get_user_id()
            body = self.get_request_body()
            
            query = body.get('query', '').strip()
            if not query:
                raise ValidationError('Search query is required')
            
            # Basic search parameters
            limit = min(int(body.get('limit', 10)), 50)  # Max 50 results
            similarity_threshold = float(body.get('similarity_threshold', 0.1))
            
            # Validate similarity threshold
            if not 0.0 <= similarity_threshold <= 1.0:
                raise ValidationError('Similarity threshold must be between 0.0 and 1.0')
            
            # Extract metadata filters
            filters = body.get('filters', {})
            filter_tags = filters.get('tags') if filters else None
            filter_category = filters.get('category') if filters else None
            min_mood = filters.get('min_mood') if filters else None
            max_mood = filters.get('max_mood') if filters else None
            
            # Validate filters
            if min_mood is not None and (min_mood < 1 or min_mood > 10):
                raise ValidationError('min_mood must be between 1 and 10')
            if max_mood is not None and (max_mood < 1 or max_mood > 10):
                raise ValidationError('max_mood must be between 1 and 10')
            if min_mood is not None and max_mood is not None and min_mood > max_mood:
                raise ValidationError('min_mood cannot be greater than max_mood')
            
            start_time = datetime.utcnow()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(
                perform_semantic_search_with_metadata(
                    user_id, query, limit, similarity_threshold,
                    filter_tags, filter_category, min_mood, max_mood
                )
            )
            loop.close()
            
            search_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.send_json_response(200, {
                'success': True,
                'query': query,
                'results': results,
                'total_count': len(results),
                'similarity_threshold': similarity_threshold,
                'filters_applied': {
                    'tags': filter_tags,
                    'category': filter_category,
                    'min_mood': min_mood,
                    'max_mood': max_mood
                },
                'search_time_ms': round(search_time_ms, 2)
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except ValidationError as e:
            self.send_json_response(400, {'error': str(e)})
        except Exception as e:
            logger.error("POST request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 