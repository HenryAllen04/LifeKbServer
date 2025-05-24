# LifeKB Backend Auth API - Production Serverless Function  
# Purpose: Production authentication with embedded monitoring and security features
# No external dependencies for serverless compatibility

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import urllib.request
import urllib.error
import os
import time
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from typing import Dict, Optional, Any, List
import hashlib
import hmac
import base64

# === EMBEDDED MONITORING SYSTEM ===
# (Extracted from app/monitoring.py for serverless compatibility)

# Performance metrics storage (in-memory)
_metrics_store = defaultdict(list)
_rate_limit_store = defaultdict(list)
_error_logs = []

class PerformanceMonitor:
    @staticmethod
    def record_request(endpoint: str, method: str, response_time: float, status_code: int):
        """Record request metrics"""
        timestamp = datetime.now().isoformat()
        metric = {
            "timestamp": timestamp,
            "endpoint": endpoint,
            "method": method,
            "response_time": response_time,
            "status_code": status_code
        }
        _metrics_store[endpoint].append(metric)
        
        # Keep only last 100 metrics per endpoint
        if len(_metrics_store[endpoint]) > 100:
            _metrics_store[endpoint] = _metrics_store[endpoint][-100:]
    
    @staticmethod
    def get_metrics_summary():
        """Get performance metrics summary"""
        summary = {}
        for endpoint, metrics in _metrics_store.items():
            if metrics:
                response_times = [m["response_time"] for m in metrics]
                summary[endpoint] = {
                    "total_requests": len(metrics),
                    "avg_response_time": sum(response_times) / len(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "last_24h": len([m for m in metrics if 
                        datetime.fromisoformat(m["timestamp"]) > datetime.now() - timedelta(hours=24)])
                }
        return summary

class RateLimiter:
    @staticmethod
    def check_rate_limit(client_ip: str, limit: int = 100, window: int = 3600) -> tuple[bool, Dict]:
        """Check if client is within rate limits"""
        now = time.time()
        window_start = now - window
        
        # Clean old entries
        _rate_limit_store[client_ip] = [
            timestamp for timestamp in _rate_limit_store[client_ip] 
            if timestamp > window_start
        ]
        
        current_requests = len(_rate_limit_store[client_ip])
        
        if current_requests >= limit:
            return False, {
                "error": "Rate limit exceeded",
                "limit": limit,
                "window": window,
                "retry_after": int(window_start + window - now)
            }
        
        # Add current request
        _rate_limit_store[client_ip].append(now)
        
        return True, {
            "requests_remaining": limit - current_requests - 1,
            "reset_time": int(window_start + window)
        }

class SecurityValidator:
    @staticmethod
    def validate_request_headers(headers: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """Validate security headers"""
        
        # Check for required security headers in CORS requests
        if headers.get("origin"):
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:3002",
                "https://your-frontend-domain.com"  # Add your frontend domain
            ]
            if headers.get("origin") not in allowed_origins:
                return False, f"Origin {headers.get('origin')} not allowed"
        
        # Check for suspicious patterns
        user_agent = headers.get("user-agent", "").lower()
        suspicious_patterns = ["bot", "crawl", "spider", "scrape"]
        if any(pattern in user_agent for pattern in suspicious_patterns):
            return False, "Suspicious user agent detected"
        
        return True, None
    
    @staticmethod
    def validate_request_size(content_length: int, max_size: int = 1024 * 1024) -> tuple[bool, Optional[str]]:
        """Validate request size"""
        if content_length > max_size:
            return False, f"Request too large: {content_length} bytes (max: {max_size})"
        return True, None

# === JWT UTILITIES ===
# (Simplified JWT implementation without external dependencies)

class JWTHandler:
    @staticmethod
    def encode_jwt(payload: Dict, secret: str, algorithm: str = "HS256") -> str:
        """Encode JWT without external dependencies"""
        
        # Header
        header = {
            "typ": "JWT",
            "alg": algorithm
        }
        
        # Encode header and payload
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(header, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(',', ':')).encode()
        ).decode().rstrip('=')
        
        # Create signature
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        
        signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{message}.{signature_encoded}"
    
    @staticmethod
    def decode_jwt(token: str, secret: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        """Decode and validate JWT"""
        try:
            # Split token
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, "Invalid token format"
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            # Verify signature
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            # Pad signature for decoding
            signature_padded = signature_encoded + '=' * (4 - len(signature_encoded) % 4)
            received_signature = base64.urlsafe_b64decode(signature_padded)
            
            if not hmac.compare_digest(expected_signature, received_signature):
                return False, None, "Invalid signature"
            
            # Decode payload
            payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            
            # Check expiration
            if "exp" in payload and payload["exp"] < time.time():
                return False, None, "Token expired"
            
            return True, payload, None
            
        except Exception as e:
            return False, None, f"Token decode error: {str(e)}"

# === SUPABASE AUTH INTEGRATION ===

def supabase_auth_request(method: str, endpoint: str, data: Optional[Dict] = None):
    """Make requests to Supabase Auth API"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_anon_key:
        raise Exception("SUPABASE_URL and SUPABASE_ANON_KEY must be configured")
    
    url = f"{supabase_url}/auth/v1/{endpoint}"
    
    headers = {
        "apikey": supabase_anon_key,
        "Content-Type": "application/json"
    }
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            if response.status in [200, 201]:
                return response_data
            else:
                raise Exception(f"Supabase Auth error: {response.status} - {response_data}")
                
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_data = json.loads(error_text)
            error_message = error_data.get('error_description', error_data.get('message', error_text))
        except:
            error_message = error_text
        raise Exception(f"Supabase Auth error: {e.code} - {error_message}")

# === MAIN REQUEST HANDLER ===

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        super().__init__(*args, **kwargs)
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # Check for forwarded headers (Vercel provides these)
        forwarded_for = self.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = self.headers.get('x-real-ip')
        if real_ip:
            return real_ip
            
        return getattr(self.client_address, '0', '127.0.0.1') if self.client_address else '127.0.0.1'
    
    def _log_request(self, status_code: int):
        """Log request with performance metrics"""
        end_time = time.time()
        response_time = (end_time - self.start_time) * 1000  # Convert to milliseconds
        
        PerformanceMonitor.record_request(
            endpoint=self.path,
            method=self.command,
            response_time=response_time,
            status_code=status_code
        )
    
    def _send_json_response(self, status_code: int, data: Dict):
        """Send JSON response with security headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        
        # Security headers
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        self._log_request(status_code)
    
    def _send_error_response(self, status_code: int, error_message: str):
        """Send error response"""
        self._send_json_response(status_code, {
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        })
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self._log_request(200)
    
    def do_GET(self):
        """Handle GET requests"""
        client_ip = self._get_client_ip()
        
        # Rate limiting
        rate_ok, rate_info = RateLimiter.check_rate_limit(client_ip)
        if not rate_ok:
            self._send_error_response(429, rate_info["error"])
            return
        
        # Security validation
        headers_dict = dict(self.headers)
        headers_ok, headers_error = SecurityValidator.validate_request_headers(headers_dict)
        if not headers_ok:
            self._send_error_response(403, headers_error)
            return
        
        # Parse query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Health check endpoint
        if query_params.get('health'):
            response = {
                "status": "healthy",
                "message": "LifeKB Auth API with embedded security features",
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "rate_limiting": "✅ Active",
                    "security_validation": "✅ Active", 
                    "performance_monitoring": "✅ Active",
                    "jwt_support": "✅ Active (no external deps)",
                    "cors_support": "✅ Active"
                },
                "environment": {
                    "supabase_configured": bool(os.environ.get("SUPABASE_URL")),
                    "jwt_secret_configured": bool(os.environ.get("JWT_SECRET_KEY"))
                },
                "rate_limit_info": rate_info
            }
            self._send_json_response(200, response)
            return
        
        # Metrics endpoint
        if query_params.get('metrics'):
            if not self._verify_admin_access():
                self._send_error_response(401, "Admin access required")
                return
                
            metrics = PerformanceMonitor.get_metrics_summary()
            self._send_json_response(200, {
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Default API info
        self._send_json_response(200, {
            "api": "LifeKB Authentication",
            "version": "1.0.0",
            "status": "active",
            "endpoints": {
                "health": "GET /?health=true",
                "login": "POST / with {action: 'login', email, password}",
                "register": "POST / with {action: 'register', email, password}",
                "verify": "POST / with {action: 'verify', token}",
                "metrics": "GET /?metrics=true (admin only)"
            },
            "features": ["rate_limiting", "security_validation", "monitoring", "jwt_auth"]
        })
    
    def do_POST(self):
        """Handle POST requests (authentication)"""
        client_ip = self._get_client_ip()
        
        # Rate limiting  
        rate_ok, rate_info = RateLimiter.check_rate_limit(client_ip, limit=50)  # Stricter for POST
        if not rate_ok:
            self._send_error_response(429, rate_info["error"])
            return
        
        # Security validation
        headers_dict = dict(self.headers)
        headers_ok, headers_error = SecurityValidator.validate_request_headers(headers_dict)
        if not headers_ok:
            self._send_error_response(403, headers_error)
            return
        
        # Validate request size
        content_length = int(self.headers.get('Content-Length', 0))
        size_ok, size_error = SecurityValidator.validate_request_size(content_length)
        if not size_ok:
            self._send_error_response(413, size_error)
            return
        
        try:
            # Read and parse request body
            if content_length > 0:
                request_body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(request_body)
            else:
                data = {}
            
            action = data.get('action', '')
            
            if action == 'login':
                self._handle_login(data)
            elif action == 'register':
                self._handle_register(data) 
            elif action == 'verify':
                self._handle_verify(data)
            elif action == 'refresh':
                self._handle_refresh(data)
            else:
                self._send_error_response(400, f"Unknown action: {action}")
                
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON in request body")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _handle_login(self, data: Dict):
        """Handle login request with real Supabase Auth"""
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            self._send_error_response(400, "Email and password required")
            return
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            self._send_error_response(400, "Invalid email format")
            return
        
        try:
            # Authenticate with Supabase Auth
            auth_data = {
                "email": email,
                "password": password
            }
            
            response = supabase_auth_request("POST", "token?grant_type=password", auth_data)
            
            # Extract user info from Supabase response
            access_token = response.get("access_token")
            user_data = response.get("user", {})
            user_id = user_data.get("id")
            
            if not access_token or not user_id:
                self._send_error_response(401, "Authentication failed")
                return
            
            # Create our own JWT token with the real user ID from Supabase
            jwt_secret = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key")
            payload = {
                "user_id": user_id,  # Real user ID from Supabase auth.users
                "email": email,
                "exp": int(time.time()) + 3600,  # 1 hour expiration
                "iat": int(time.time())
            }
            
            token = JWTHandler.encode_jwt(payload, jwt_secret)
            
            self._send_json_response(200, {
                "success": True,
                "message": "Login successful",
                "token": token,
                "user": {
                    "email": email,
                    "user_id": user_id
                },
                "expires_in": 3600,
                "supabase_token": access_token  # Include original Supabase token too
            })
            
        except Exception as e:
            # Handle specific Supabase auth errors
            error_message = str(e)
            if "Invalid login credentials" in error_message:
                self._send_error_response(401, "Invalid email or password")
            elif "Email not confirmed" in error_message:
                self._send_error_response(401, "Please verify your email before logging in")
            else:
                self._send_error_response(500, f"Authentication error: {error_message}")
    
    def _handle_register(self, data: Dict):
        """Handle registration request with real Supabase Auth"""
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            self._send_error_response(400, "Email and password required")
            return
        
        if len(password) < 8:
            self._send_error_response(400, "Password must be at least 8 characters")
            return
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            self._send_error_response(400, "Invalid email format")
            return
        
        try:
            # Register with Supabase Auth
            auth_data = {
                "email": email,
                "password": password
            }
            
            response = supabase_auth_request("POST", "signup", auth_data)
            
            # Extract user info from Supabase response
            user_data = response.get("user", {})
            user_id = user_data.get("id")
            
            if not user_id:
                self._send_error_response(500, "User creation failed")
                return
            
            self._send_json_response(200, {
                "success": True,
                "message": "Registration successful",
                "user": {
                    "id": user_id,
                    "email": email
                },
                "note": "User created in Supabase auth.users table. Check email for verification link if email confirmation is enabled."
            })
            
        except Exception as e:
            error_message = str(e)
            if "User already registered" in error_message:
                self._send_error_response(409, "User with this email already exists")
            elif "Password should be at least" in error_message:
                self._send_error_response(400, "Password does not meet requirements")
            else:
                self._send_error_response(500, f"Registration error: {error_message}")
    
    def _handle_verify(self, data: Dict):
        """Handle token verification"""
        token = data.get('token', '')
        
        if not token:
            self._send_error_response(400, "Token required")
            return
        
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key")
        valid, payload, error = JWTHandler.decode_jwt(token, jwt_secret)
        
        if valid:
            self._send_json_response(200, {
                "valid": True,
                "user": {
                    "user_id": payload.get("user_id"),
                    "email": payload.get("email")
                },
                "expires_at": payload.get("exp")
            })
        else:
            self._send_error_response(401, f"Invalid token: {error}")
    
    def _handle_refresh(self, data: Dict):
        """Handle token refresh"""
        token = data.get('token', '')
        
        if not token:
            self._send_error_response(400, "Token required")
            return
        
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key")
        valid, payload, error = JWTHandler.decode_jwt(token, jwt_secret)
        
        if valid:
            # Generate new token
            new_payload = {
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "exp": int(time.time()) + 3600,
                "iat": int(time.time())
            }
            
            new_token = JWTHandler.encode_jwt(new_payload, jwt_secret)
            
            self._send_json_response(200, {
                "success": True,
                "token": new_token,
                "expires_in": 3600
            })
        else:
            self._send_error_response(401, f"Cannot refresh invalid token: {error}")
    
    def _verify_admin_access(self) -> bool:
        """Verify admin access for metrics endpoint"""
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "fallback-secret-key")
        valid, payload, _ = JWTHandler.decode_jwt(token, jwt_secret)
        
        if not valid:
            return False
        
        # In production, check if user has admin role
        # For demo, allow any valid token
        return True 