# LifeKB Backend Entries API - Vercel Serverless Function
# Purpose: Complete journal entry CRUD operations (list, create, get, update, delete)

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import sys
import asyncio
from datetime import datetime
from uuid import uuid4, UUID

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Supabase imports
from supabase import create_client, Client

# Import embeddings functionality
try:
    from app.embeddings import auto_generate_embedding
except ImportError:
    auto_generate_embedding = None

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

# Initialize Supabase client
def get_supabase_client():
    """Initialize and return Supabase client with environment variables."""
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

def extract_user_from_token(authorization_header):
    """Extract user ID from JWT token in Authorization header."""
    if not authorization_header:
        raise AuthError("Authorization header required")
    
    if not authorization_header.startswith('Bearer '):
        raise AuthError("Invalid authorization header format")
    
    token = authorization_header[7:]  # Remove 'Bearer ' prefix
    
    # For development, we'll decode without verification
    # In production, this should verify the JWT signature
    import jwt
    try:
        if os.environ.get("ENVIRONMENT") == "development":
            decoded = jwt.decode(token, options={"verify_signature": False})
        else:
            jwt_secret = os.environ.get("JWT_SECRET_KEY")
            if not jwt_secret:
                raise AuthError("JWT_SECRET_KEY not configured")
            decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        
        user_id = decoded.get('sub')
        if not user_id:
            raise AuthError("Invalid token: missing user ID")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
    except Exception as e:
        raise AuthError(f"Token validation error: {str(e)}")

async def create_journal_entry(user_id: str, text: str):
    """Create a new journal entry for the user."""
    try:
        supabase = get_supabase_client()
        
        entry_id = str(uuid4())
        entry_data = {
            "id": entry_id,
            "user_id": user_id,
            "text": text,
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
                print(f"Warning: Failed to auto-generate embedding for entry {entry_id}: {str(e)}")
        
        return created_entry
        
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")

async def get_journal_entries(user_id: str, page: int = 1, limit: int = 20):
    """Get paginated journal entries for the user."""
    try:
        supabase = get_supabase_client()
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get entries with pagination
        response = supabase.table("journal_entries")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Get total count
        count_response = supabase.table("journal_entries")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .execute()
        
        total_count = count_response.count if count_response.count else 0
        total_pages = (total_count + limit - 1) // limit
        
        return {
            "items": serialize_data(response.data),
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
        
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")

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
        raise Exception(f"Database error: {str(e)}")

async def update_journal_entry(user_id: str, entry_id: str, text: str):
    """Update a journal entry for the user."""
    try:
        supabase = get_supabase_client()
        
        update_data = {
            "text": text,
            "updated_at": datetime.utcnow().isoformat(),
            "embedding_status": "pending"  # Mark for re-embedding
        }
        
        response = supabase.table("journal_entries")\
            .update(update_data)\
            .eq("id", entry_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not response.data:
            return None
        
        return serialize_data(response.data[0])
        
    except Exception as e:
        raise Exception(f"Database error: {str(e)}")

async def delete_journal_entry(user_id: str, entry_id: str):
    """Delete a journal entry for the user."""
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("journal_entries")\
            .delete()\
            .eq("id", entry_id)\
            .eq("user_id", user_id)\
            .execute()
        
        return bool(response.data)
        
    except Exception as e:
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
            return {}

    def get_user_id(self) -> str:
        """Extract and validate user ID from authorization header."""
        auth_header = self.headers.get('Authorization')
        return extract_user_from_token(auth_header)

    def parse_path(self) -> tuple:
        """Parse URL path to determine operation type and entry ID."""
        parsed_url = urllib.parse.urlparse(self.path)
        path_parts = [part for part in parsed_url.path.strip('/').split('/') if part]
        
        # Expected patterns:
        # /api/entries -> list entries
        # /api/entries?id=<entry_id> -> get/update/delete specific entry
        
        query = urllib.parse.parse_qs(parsed_url.query)
        entry_id = query.get('id', [None])[0]
        
        return entry_id, query

    def do_GET(self):
        """Handle GET requests - list entries or get specific entry."""
        try:
            user_id = self.get_user_id()
            entry_id, query = self.parse_path()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if entry_id:
                # Get specific entry
                entry = loop.run_until_complete(get_journal_entry(user_id, entry_id))
                loop.close()
                
                if not entry:
                    self.send_json_response(404, {'error': 'Entry not found'})
                    return
                
                self.send_json_response(200, {
                    'success': True,
                    'entry': entry
                })
            else:
                # List entries with pagination
                page = int(query.get('page', [1])[0])
                limit = min(int(query.get('limit', [20])[0]), 100)  # Max 100 per page
                
                result = loop.run_until_complete(get_journal_entries(user_id, page, limit))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'entries': result
                })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
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
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            entry = loop.run_until_complete(create_journal_entry(user_id, text))
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
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_PUT(self):
        """Handle PUT requests - update specific entry."""
        try:
            user_id = self.get_user_id()
            entry_id, _ = self.parse_path()
            
            if not entry_id:
                raise ValidationError('Entry ID is required in query parameter (?id=entry_id)')
            
            body = self.get_request_body()
            text = body.get('text', '').strip()
            if not text:
                raise ValidationError('Entry text is required')
            
            if len(text) > 10000:  # 10k character limit
                raise ValidationError('Entry text too long (max 10,000 characters)')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            entry = loop.run_until_complete(update_journal_entry(user_id, entry_id, text))
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
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_DELETE(self):
        """Handle DELETE requests - delete specific entry."""
        try:
            user_id = self.get_user_id()
            entry_id, _ = self.parse_path()
            
            if not entry_id:
                raise ValidationError('Entry ID is required in query parameter (?id=entry_id)')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            deleted = loop.run_until_complete(delete_journal_entry(user_id, entry_id))
            loop.close()
            
            if not deleted:
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
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 