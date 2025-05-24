# LifeKB Backend Auth API - Vercel Serverless Function
# Purpose: Real authentication endpoints using Supabase Auth with monitoring and security

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import os
import sys
import asyncio
from datetime import datetime

# Supabase imports
from supabase import create_client, Client

# Enhanced monitoring and security
from app.monitoring import (
    performance_monitor, rate_limiter, security_monitor, 
    create_logger
)

logger = create_logger("auth_api")

def serialize_datetime(obj):
    """Convert datetime objects to ISO format strings for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, 'isoformat'):  # Handle other datetime-like objects
        return obj.isoformat()
    return obj

def serialize_user_data(data):
    """Recursively serialize datetime objects in user data."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            try:
                result[key] = serialize_user_data(value)
            except Exception as e:
                # Convert problematic values to strings
                result[key] = str(value)
        return result
    elif isinstance(data, list):
        return [serialize_user_data(item) for item in data]
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

@rate_limiter.limit_requests(max_requests=5, window_minutes=1)  # 5 login attempts per minute
@performance_monitor.track_request("/api/auth", "POST")
async def authenticate_user(email: str, password: str, ip_address: str = "unknown"):
    """Authenticate user with Supabase Auth."""
    logger.info("Authentication attempt started", email=email, ip_address=ip_address)
    
    try:
        # Input validation and security checks
        security_monitor.validate_input_size("email", email, 254)  # RFC 5321 limit
        security_monitor.validate_input_size("password", password, 128)  # Reasonable password limit
        
        if not security_monitor.check_content_safety(email):
            raise AuthError("Invalid email format")
        
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            # Log failed authentication
            security_monitor.log_auth_attempt(email, False, ip_address)
            raise AuthError("Invalid credentials")
        
        # Log successful authentication
        security_monitor.log_auth_attempt(email, True, ip_address)
        
        result = {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            }
        }
        
        logger.info("Authentication successful", email=email, user_id=response.user.id)
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        logger.error("Authentication failed", email=email, error=str(e))
        security_monitor.log_auth_attempt(email, False, ip_address)
        
        if "Invalid login credentials" in str(e):
            raise AuthError("Invalid email or password")
        raise AuthError(f"Authentication failed: {str(e)}")

@rate_limiter.limit_requests(max_requests=3, window_minutes=5)  # 3 registrations per 5 minutes
@performance_monitor.track_request("/api/auth", "POST")
async def register_user(email: str, password: str, ip_address: str = "unknown"):
    """Register new user with Supabase Auth."""
    logger.info("User registration attempt started", email=email, ip_address=ip_address)
    
    try:
        # Enhanced input validation
        security_monitor.validate_input_size("email", email, 254)
        security_monitor.validate_input_size("password", password, 128)
        
        if not security_monitor.check_content_safety(email):
            raise AuthError("Invalid email format")
        
        # Basic password strength check
        if len(password) < 8:
            raise AuthError("Password must be at least 8 characters long")
        
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise AuthError("Failed to create user account")
        
        result = {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
                "email_confirmed": response.user.email_confirmed_at is not None
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None
            } if response.session else None
        }
        
        logger.info("User registration successful", email=email, user_id=response.user.id)
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        logger.error("User registration failed", email=email, error=str(e))
        
        if "already registered" in str(e).lower():
            raise AuthError("User with this email already exists")
        raise AuthError(f"Registration failed: {str(e)}")

@rate_limiter.limit_requests(max_requests=10, window_minutes=5)  # 10 refresh attempts per 5 minutes
@performance_monitor.track_request("/api/auth", "POST")
async def refresh_token(refresh_token: str):
    """Refresh user session using refresh token."""
    logger.info("Token refresh attempt started")
    
    try:
        # Input validation
        security_monitor.validate_input_size("refresh_token", refresh_token, 1024)  # JWT tokens are typically < 1KB
        
        supabase = get_supabase_client()
        response = supabase.auth.refresh_session(refresh_token)
        
        if not response.session:
            logger.warn("Token refresh failed - invalid token")
            raise AuthError("Invalid refresh token")
        
        result = {
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at
            },
            "user": {
                "id": response.user.id,
                "email": response.user.email
            } if response.user else None
        }
        
        logger.info("Token refresh successful", user_id=response.user.id if response.user else "unknown")
        
        # Serialize datetime objects
        return serialize_user_data(result)
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise AuthError(f"Token refresh failed: {str(e)}")

@performance_monitor.track_request("/api/auth", "GET")
async def test_connection():
    """Test database connection and return basic info."""
    logger.info("Database connection test requested")
    
    try:
        supabase = get_supabase_client()
        # Simple query to test connection
        response = supabase.table('journal_entries').select('count', count='exact').execute()
        
        result = {
            "status": "connected",
            "url": os.environ.get("SUPABASE_URL"),
            "table_exists": True
        }
        
        logger.info("Database connection test successful")
        return result
        
    except Exception as e:
        logger.error("Database connection test failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
            "url": os.environ.get("SUPABASE_URL")
        }

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

    def get_client_ip(self) -> str:
        """Extract client IP address for security monitoring."""
        # Check headers for real IP (from proxies/load balancers)
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = self.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return self.client_address[0] if self.client_address else "unknown"

    def do_GET(self):
        """Handle GET requests - health check and API info."""
        logger.info("GET request received", path=self.path, ip=self.get_client_ip())
        
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # Health check endpoint
        if 'health' in query:
            try:
                # Test database connection
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                db_status = loop.run_until_complete(test_connection())
                
                self.send_json_response(200, {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "database": db_status,
                    "environment": os.environ.get("ENVIRONMENT", "development")
                })
                
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                self.send_json_response(500, {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        else:
            # Default API info
            self.send_json_response(200, {
                "service": "LifeKB Authentication API",
                "version": "1.0.0",
                "endpoints": {
                    "POST": {
                        "login": "Login with email/password",
                        "signup": "Register new user",
                        "refresh": "Refresh access token"
                    },
                    "GET": {
                        "health": "Health check"
                    }
                },
                "documentation": "https://github.com/yourusername/lifekb-api"
            })

    def do_POST(self):
        """Handle POST requests - authentication actions."""
        try:
            body = self.get_request_body()
            action = body.get('action')
            
            if not action:
                self.send_json_response(400, {
                    'error': 'Missing action parameter',
                    'required': 'action must be one of: login, signup, refresh'
                })
                return
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if action == 'login':
                    result = loop.run_until_complete(self.handle_login(body))
                elif action == 'signup':
                    result = loop.run_until_complete(self.handle_signup(body))
                elif action == 'refresh':
                    result = loop.run_until_complete(self.handle_refresh(body))
                else:
                    self.send_json_response(400, {
                        'error': f'Invalid action: {action}',
                        'valid_actions': ['login', 'signup', 'refresh']
                    })
                    return
                
                self.send_json_response(200, result)
                
            except AuthError as e:
                self.send_json_response(401, {'error': str(e)})
            except Exception as e:
                self.send_json_response(500, {'error': f'Internal server error: {str(e)}'})
            finally:
                loop.close()
                
        except Exception as e:
            self.send_json_response(500, {'error': f'Request processing error: {str(e)}'})

    async def handle_login(self, body: dict) -> dict:
        """Handle user login."""
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            raise AuthError('Email and password are required')
        
        ip_address = self.get_client_ip()
        result = await authenticate_user(email, password, ip_address)
        return {
            'action': 'login',
            'success': True,
            'message': 'Login successful',
            'user': result['user'],
            'session': result['session']
        }

    async def handle_signup(self, body: dict) -> dict:
        """Handle user registration."""
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            raise AuthError('Email and password are required')
        
        ip_address = self.get_client_ip()
        result = await register_user(email, password, ip_address)
        return {
            'action': 'signup',
            'success': True,
            'message': 'Registration successful',
            'user': result['user'],
            'session': result['session'],
            'note': 'Please check your email to confirm your account' if not result['user']['email_confirmed'] else None
        }

    async def handle_refresh(self, body: dict) -> dict:
        """Handle token refresh."""
        refresh_token_value = body.get('refresh_token')
        
        if not refresh_token_value:
            raise AuthError('Refresh token is required')
        
        ip_address = self.get_client_ip()
        result = await refresh_token(refresh_token_value)
        return {
            'action': 'refresh',
            'success': True,
            'message': 'Token refreshed successfully',
            'session': result['session'],
            'user': result['user']
        }

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers() 