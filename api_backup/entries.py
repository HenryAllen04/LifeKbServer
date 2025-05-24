# LifeKB Backend Entries API - Vercel Serverless Function
# Purpose: Complete journal entry CRUD operations (list, create, get, update, delete) with metadata support

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import sys
import asyncio
from datetime import datetime
from uuid import uuid4, UUID
from typing import List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Supabase imports
from supabase import create_client, Client

# Import monitoring and security
from app.monitoring import performance_monitor, rate_limiter, security_monitor, create_logger

# Import embeddings functionality
try:
    from app.embeddings import auto_generate_embedding
except ImportError:
    auto_generate_embedding = None

logger = create_logger("entries_api")

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

def get_supabase_client():
    """Initialize and return Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment")
    
    return create_client(url, key)

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

@rate_limiter.limit_requests(max_requests=100, window_minutes=1)  # 100 requests per minute
@performance_monitor.track_request("/api/entries", "POST")
async def create_journal_entry(
    user_id: str, 
    text: str, 
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    mood: Optional[int] = None,
    location: Optional[str] = None,
    weather: Optional[str] = None
):
    """Create a new journal entry with metadata for the user."""
    try:
        # Input validation
        security_monitor.validate_input_size("text", text, 10000)
        if tags:
            for tag in tags:
                security_monitor.validate_input_size("tag", tag, 50)
        if location:
            security_monitor.validate_input_size("location", location, 255)
        if weather:
            security_monitor.validate_input_size("weather", weather, 50)
        
        supabase = get_supabase_client()
        
        entry_id = str(uuid4())
        entry_data = {
            "id": entry_id,
            "user_id": user_id,
            "text": text,
            "tags": tags or [],
            "category": category,
            "mood": mood,
            "location": location,
            "weather": weather,
            "embedding_status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase.table("journal_entries").insert(entry_data).execute()
        
        if not response.data:
            raise Exception("Failed to create journal entry")
        
        created_entry = serialize_data(response.data[0])
        
        # Automatically generate embedding in background if available
        if auto_generate_embedding:
            try:
                await auto_generate_embedding(UUID(entry_id), text)
            except Exception as e:
                # Log error but don't fail entry creation
                logger.warn(f"Failed to auto-generate embedding for entry {entry_id}", error=str(e))
        
        logger.info("Journal entry created successfully", 
                   entry_id=entry_id, user_id=user_id, 
                   has_tags=bool(tags), has_category=bool(category), has_mood=bool(mood))
        
        return created_entry
        
    except Exception as e:
        logger.error("Failed to create journal entry", user_id=user_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

@rate_limiter.limit_requests(max_requests=200, window_minutes=1)  # 200 requests per minute
@performance_monitor.track_request("/api/entries", "GET")
async def get_journal_entries(
    user_id: str, 
    page: int = 1, 
    limit: int = 20,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    min_mood: Optional[int] = None,
    max_mood: Optional[int] = None
):
    """Get paginated journal entries for the user with metadata filtering."""
    try:
        supabase = get_supabase_client()
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build query with metadata filters
        query = supabase.table("journal_entries").select("*").eq("user_id", user_id)
        
        # Apply filters
        if category:
            query = query.eq("category", category)
        if min_mood is not None:
            query = query.gte("mood", min_mood)
        if max_mood is not None:
            query = query.lte("mood", max_mood)
        if tags:
            # PostgreSQL array overlap operator
            query = query.overlaps("tags", tags)
        
        # Get entries with pagination and ordering
        response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Get total count with same filters
        count_query = supabase.table("journal_entries").select("id", count="exact").eq("user_id", user_id)
        
        if category:
            count_query = count_query.eq("category", category)
        if min_mood is not None:
            count_query = count_query.gte("mood", min_mood)
        if max_mood is not None:
            count_query = count_query.lte("mood", max_mood)
        if tags:
            count_query = count_query.overlaps("tags", tags)
        
        count_response = count_query.execute()
        
        total_count = count_response.count if count_response.count else 0
        total_pages = (total_count + limit - 1) // limit
        
        return {
            "items": serialize_data(response.data),
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "filters_applied": {
                "category": category,
                "tags": tags,
                "min_mood": min_mood,
                "max_mood": max_mood
            }
        }
        
    except Exception as e:
        logger.error("Failed to get journal entries", user_id=user_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

@performance_monitor.track_request("/api/entries", "GET")
async def get_journal_entry(user_id: str, entry_id: str):
    """Get a specific journal entry for the user."""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("journal_entries")\
            .select("*")\
            .eq("id", entry_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not response.data:
            return None
        
        return serialize_data(response.data[0])
        
    except Exception as e:
        logger.error("Failed to get journal entry", user_id=user_id, entry_id=entry_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

@rate_limiter.limit_requests(max_requests=50, window_minutes=1)  # 50 updates per minute
@performance_monitor.track_request("/api/entries", "PUT")
async def update_journal_entry(
    user_id: str, 
    entry_id: str, 
    text: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    mood: Optional[int] = None,
    location: Optional[str] = None,
    weather: Optional[str] = None
):
    """Update a journal entry with metadata for the user."""
    try:
        # Input validation
        if text:
            security_monitor.validate_input_size("text", text, 10000)
        if tags:
            for tag in tags:
                security_monitor.validate_input_size("tag", tag, 50)
        if location:
            security_monitor.validate_input_size("location", location, 255)
        if weather:
            security_monitor.validate_input_size("weather", weather, 50)
        
        supabase = get_supabase_client()
        
        update_data = {
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Only update fields that are provided
        if text is not None:
            update_data["text"] = text
            update_data["embedding_status"] = "pending"  # Mark for re-embedding
        if tags is not None:
            update_data["tags"] = tags
        if category is not None:
            update_data["category"] = category
        if mood is not None:
            update_data["mood"] = mood
        if location is not None:
            update_data["location"] = location
        if weather is not None:
            update_data["weather"] = weather
        
        response = supabase.table("journal_entries")\
            .update(update_data)\
            .eq("id", entry_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not response.data:
            return None
        
        logger.info("Journal entry updated successfully", 
                   entry_id=entry_id, user_id=user_id, updated_fields=list(update_data.keys()))
        
        return serialize_data(response.data[0])
        
    except Exception as e:
        logger.error("Failed to update journal entry", user_id=user_id, entry_id=entry_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

@rate_limiter.limit_requests(max_requests=30, window_minutes=1)  # 30 deletes per minute
@performance_monitor.track_request("/api/entries", "DELETE")
async def delete_journal_entry(user_id: str, entry_id: str):
    """Delete a journal entry for the user."""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("journal_entries")\
            .delete()\
            .eq("id", entry_id)\
            .eq("user_id", user_id)\
            .execute()
        
        success = bool(response.data)
        if success:
            logger.info("Journal entry deleted successfully", entry_id=entry_id, user_id=user_id)
        
        return success
        
    except Exception as e:
        logger.error("Failed to delete journal entry", user_id=user_id, entry_id=entry_id, error=str(e))
        raise Exception(f"Database error: {str(e)}")

class handler(BaseHTTPRequestHandler):
    def send_json_response(self, status_code: int, data: dict):
        """Helper to send JSON responses with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
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
        """Handle GET requests - list entries or get specific entry."""
        try:
            user_id = self.get_user_id()
            
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Get specific entry
            if 'id' in query_params:
                entry_id = query_params['id'][0]
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                entry = loop.run_until_complete(get_journal_entry(user_id, entry_id))
                loop.close()
                
                if not entry:
                    self.send_json_response(404, {'error': 'Entry not found'})
                    return
                
                self.send_json_response(200, {
                    'success': True,
                    'entry': entry
                })
                return
            
            # List entries with optional filters
            page = int(query_params.get('page', [1])[0])
            limit = min(int(query_params.get('limit', [20])[0]), 100)
            category = query_params.get('category', [None])[0]
            tags = query_params.get('tags', [])
            min_mood = int(query_params['min_mood'][0]) if 'min_mood' in query_params else None
            max_mood = int(query_params['max_mood'][0]) if 'max_mood' in query_params else None
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            entries = loop.run_until_complete(get_journal_entries(
                user_id, page, limit, category, tags, min_mood, max_mood
            ))
            loop.close()
            
            self.send_json_response(200, {
                'success': True,
                **entries
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
            logger.error("GET request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_POST(self):
        """Handle POST requests - create new entry."""
        try:
            user_id = self.get_user_id()
            body = self.get_request_body()
            
            text = body.get('text', '').strip()
            if not text:
                raise ValidationError('Entry text is required')
            
            if len(text) > 10000:  # 10k character limit
                raise ValidationError('Entry text too long (max 10,000 characters)')
            
            # Extract metadata
            tags = body.get('tags')
            category = body.get('category')
            mood = body.get('mood')
            location = body.get('location')
            weather = body.get('weather')
            
            # Validate metadata
            if tags and len(tags) > 20:
                raise ValidationError('Too many tags (max 20)')
            if mood and (mood < 1 or mood > 10):
                raise ValidationError('Mood must be between 1 and 10')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            entry = loop.run_until_complete(create_journal_entry(
                user_id, text, tags, category, mood, location, weather
            ))
            loop.close()
            
            self.send_json_response(201, {
                'success': True,
                'message': 'Entry created successfully',
                'entry': entry
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except ValidationError as e:
            self.send_json_response(400, {'error': str(e)})
        except Exception as e:
            logger.error("POST request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_PUT(self):
        """Handle PUT requests - update specific entry."""
        try:
            user_id = self.get_user_id()
            
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'id' not in query_params:
                raise ValidationError('Entry ID is required')
            
            entry_id = query_params['id'][0]
            body = self.get_request_body()
            
            # Extract optional fields for update
            text = body.get('text')
            tags = body.get('tags')
            category = body.get('category')
            mood = body.get('mood')
            location = body.get('location')
            weather = body.get('weather')
            
            # Validate if provided
            if text and len(text) > 10000:
                raise ValidationError('Entry text too long (max 10,000 characters)')
            if tags and len(tags) > 20:
                raise ValidationError('Too many tags (max 20)')
            if mood and (mood < 1 or mood > 10):
                raise ValidationError('Mood must be between 1 and 10')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            entry = loop.run_until_complete(update_journal_entry(
                user_id, entry_id, text, tags, category, mood, location, weather
            ))
            loop.close()
            
            if not entry:
                self.send_json_response(404, {'error': 'Entry not found'})
                return
            
            self.send_json_response(200, {
                'success': True,
                'message': 'Entry updated successfully',
                'entry': entry
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except ValidationError as e:
            self.send_json_response(400, {'error': str(e)})
        except Exception as e:
            logger.error("PUT request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_DELETE(self):
        """Handle DELETE requests - delete specific entry."""
        try:
            user_id = self.get_user_id()
            
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            if 'id' not in query_params:
                raise ValidationError('Entry ID is required')
            
            entry_id = query_params['id'][0]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(delete_journal_entry(user_id, entry_id))
            loop.close()
            
            if not success:
                self.send_json_response(404, {'error': 'Entry not found'})
                return
            
            self.send_json_response(200, {
                'success': True,
                'message': 'Entry deleted successfully'
            })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except ValidationError as e:
            self.send_json_response(400, {'error': str(e)})
        except Exception as e:
            logger.error("DELETE request failed", error=str(e))
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 