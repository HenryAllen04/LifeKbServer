# LifeKB Backend Embeddings API - Vercel Serverless Function
# Purpose: Embedding generation and management operations

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import sys
import asyncio
from datetime import datetime
from uuid import UUID

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from app modules
try:
    from app.embeddings import embeddings_manager, EmbeddingsError
except ImportError:
    embeddings_manager = None
    EmbeddingsError = Exception

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

async def process_embeddings(user_id: str, limit: int = 10):
    """Process pending embeddings for a user."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available - check OPENAI_API_KEY")
        
        user_uuid = UUID(user_id)
        result = await embeddings_manager.process_pending_embeddings(user_uuid, limit)
        
        return serialize_data(result)
        
    except EmbeddingsError as e:
        raise Exception(f"Embedding processing error: {str(e)}")
    except Exception as e:
        raise Exception(f"Processing failed: {str(e)}")

async def get_status(user_id: str):
    """Get embedding status for a user."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available - check OPENAI_API_KEY")
        
        user_uuid = UUID(user_id)
        status = await embeddings_manager.get_embedding_status(user_uuid)
        
        return serialize_data(status)
        
    except EmbeddingsError as e:
        raise Exception(f"Status error: {str(e)}")
    except Exception as e:
        raise Exception(f"Status check failed: {str(e)}")

async def generate_single_embedding(user_id: str, entry_id: str):
    """Generate embedding for a specific entry."""
    try:
        if not embeddings_manager:
            raise Exception("Embeddings manager not available - check OPENAI_API_KEY")
        
        # Get the entry text first (would need to implement this)
        # For now, this is a placeholder
        raise Exception("Single entry embedding generation not yet implemented")
        
    except EmbeddingsError as e:
        raise Exception(f"Embedding generation error: {str(e)}")
    except Exception as e:
        raise Exception(f"Generation failed: {str(e)}")

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
            return {}

    def get_user_id(self) -> str:
        """Extract and validate user ID from authorization header."""
        auth_header = self.headers.get('Authorization')
        return extract_user_from_token(auth_header)

    def do_GET(self):
        """Handle GET requests - status and info."""
        try:
            user_id = self.get_user_id()
            
            parsed_url = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_url.query)
            
            action = query.get('action', [None])[0]
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if action == 'status':
                # Get embedding status
                result = loop.run_until_complete(get_status(user_id))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'status': result
                })
            else:
                # Default API info
                loop.close()
                self.send_json_response(200, {
                    'message': 'LifeKB Embeddings API',
                    'version': '1.0.0',
                    'endpoints': {
                        'GET': ['?action=status - Get embedding status'],
                        'POST': [
                            'action=process - Process pending embeddings',
                            'action=generate - Generate specific embedding'
                        ]
                    },
                    'status': 'running',
                    'openai_configured': os.getenv("OPENAI_API_KEY") is not None
                })
            
        except AuthError as e:
            self.send_json_response(401, {'error': str(e)})
        except Exception as e:
            self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})

    def do_POST(self):
        """Handle POST requests - process embeddings."""
        try:
            user_id = self.get_user_id()
            body = self.get_request_body()
            
            action = body.get('action', 'process')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if action == 'process':
                # Process pending embeddings
                limit = min(int(body.get('limit', 10)), 20)  # Max 20 at once
                result = loop.run_until_complete(process_embeddings(user_id, limit))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'action': 'process',
                    'result': result
                })
                
            elif action == 'generate':
                # Generate specific embedding
                entry_id = body.get('entry_id')
                if not entry_id:
                    raise ValidationError('entry_id is required for generate action')
                
                result = loop.run_until_complete(generate_single_embedding(user_id, entry_id))
                loop.close()
                
                self.send_json_response(200, {
                    'success': True,
                    'action': 'generate',
                    'entry_id': entry_id,
                    'result': result
                })
                
            else:
                loop.close()
                raise ValidationError(f'Invalid action: {action}. Valid actions: process, generate')
            
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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 