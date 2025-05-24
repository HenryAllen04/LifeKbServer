# LifeKB Backend Monitoring API - Vercel Serverless Function
# Purpose: System health checks, performance metrics, and API status monitoring

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import urllib.request
import urllib.error
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any
import hashlib
import hmac
import base64

# === EMBEDDED JWT HANDLER ===

class JWTHandler:
    @staticmethod
    def decode_jwt(token: str, secret: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, None, "Invalid token format"
            
            header_encoded, payload_encoded, signature_encoded = parts
            
            message = f"{header_encoded}.{payload_encoded}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            
            signature_padded = signature_encoded + '=' * (4 - len(signature_encoded) % 4)
            received_signature = base64.urlsafe_b64decode(signature_padded)
            
            if not hmac.compare_digest(expected_signature, received_signature):
                return False, None, "Invalid signature"
            
            payload_padded = payload_encoded + '=' * (4 - len(payload_encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            
            if "exp" in payload and payload["exp"] < time.time():
                return False, None, "Token expired"
            
            return True, payload, None
            
        except Exception as e:
            return False, None, f"Token decode error: {str(e)}"

# === SUPABASE REQUEST FUNCTION ===

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None):
    """Make direct HTTP requests to Supabase REST API"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")
    
    url = f"{supabase_url}/rest/v1/{endpoint}"
    if params:
        query_string = urllib.parse.urlencode(params)
        url += f"?{query_string}"
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status not in [200, 201, 204]:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Supabase error: {response.status} - {error_text}")
            
            if response.status == 204:
                return {}
            
            return json.loads(response.read().decode('utf-8'))
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8') if e.fp else str(e)
        raise Exception(f"Supabase error: {e.code} - {error_text}")

# === MONITORING FUNCTIONS ===

def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "environment": os.getenv("VERCEL_ENV", "development"),
        "components": {}
    }
    
    # Test database connection
    try:
        start_time = time.time()
        # Simple query to test connection
        result = supabase_request("GET", "journal_entries", params={"limit": "1"})
        db_response_time = round((time.time() - start_time) * 1000, 2)
        
        health_status["components"]["database"] = {
            "status": "healthy",
            "response_time_ms": db_response_time,
            "connection": "successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "connection": "failed"
        }
    
    # Test OpenAI API availability (just check if key is configured)
    openai_key = os.environ.get("OPENAI_API_KEY")
    health_status["components"]["openai"] = {
        "status": "configured" if openai_key else "not_configured",
        "key_present": bool(openai_key)
    }
    
    # Test environment variables
    required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "JWT_SECRET_KEY"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    health_status["components"]["environment"] = {
        "status": "healthy" if not missing_vars else "unhealthy",
        "missing_variables": missing_vars,
        "configured_variables": len(required_env_vars) - len(missing_vars)
    }
    
    return health_status

def get_system_metrics() -> Dict[str, Any]:
    """Get basic system metrics and statistics"""
    try:
        # Get total users count
        users_result = supabase_request("GET", "journal_entries", params={
            "select": "user_id",
            "limit": "1000"  # Reasonable limit for counting
        })
        
        unique_users = len(set(entry["user_id"] for entry in users_result)) if users_result else 0
        
        # Get total entries count
        entries_count = len(users_result) if users_result else 0
        
        # Get embedding statistics
        embeddings_result = supabase_request("GET", "journal_entries", params={
            "select": "embedding_status",
            "limit": "1000"
        })
        
        embedding_stats = {"pending": 0, "completed": 0, "failed": 0}
        if embeddings_result:
            for entry in embeddings_result:
                status = entry.get("embedding_status", "pending")
                embedding_stats[status] = embedding_stats.get(status, 0) + 1
        
        completion_rate = 0
        if entries_count > 0:
            completion_rate = round((embedding_stats["completed"] / entries_count) * 100, 1)
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database_metrics": {
                "total_users": unique_users,
                "total_entries": entries_count,
                "entries_per_user": round(entries_count / unique_users, 1) if unique_users > 0 else 0
            },
            "embedding_metrics": {
                "total_embeddings": embedding_stats["completed"],
                "pending_embeddings": embedding_stats["pending"],
                "failed_embeddings": embedding_stats["failed"],
                "completion_rate_percent": completion_rate
            },
            "system_info": {
                "python_version": "3.9+",
                "deployment_platform": "Vercel Serverless",
                "database_provider": "Supabase PostgreSQL"
            }
        }
        
    except Exception as e:
        return {
            "error": f"Failed to retrieve metrics: {str(e)}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

def test_api_endpoints() -> Dict[str, Any]:
    """Test availability of other API endpoints"""
    base_url = os.environ.get("VERCEL_URL", "localhost:3000")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    
    endpoints = {
        "auth": f"{base_url}/api/auth",
        "entries": f"{base_url}/api/entries", 
        "search": f"{base_url}/api/search",
        "embeddings": f"{base_url}/api/embeddings"
    }
    
    results = {}
    
    for name, url in endpoints.items():
        try:
            start_time = time.time()
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'LifeKB-Monitor/1.0')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                response_time = round((time.time() - start_time) * 1000, 2)
                results[name] = {
                    "status": "healthy",
                    "response_code": response.status,
                    "response_time_ms": response_time
                }
        except Exception as e:
            results[name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    return results

# === MAIN REQUEST HANDLER ===

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        super().__init__(*args, **kwargs)
    
    def _send_json_response(self, status_code: int, data: Dict):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, status_code: int, error_message: str):
        self._send_json_response(status_code, {
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        })
    
    def _verify_auth(self) -> Optional[str]:
        """Verify JWT token and return user_id (optional for monitoring)"""
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]
        # Get JWT secret (no fallback for security)
        jwt_secret = os.environ.get("JWT_SECRET_KEY")
        if not jwt_secret:
            self._send_error_response(500, "Server configuration error")
            return None
        
        valid, payload, _ = JWTHandler.decode_jwt(token, jwt_secret)
        
        if not valid:
            return None
        
        return payload.get("user_id")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests - monitoring data"""
        try:
            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            check_type = query_params.get('type', ['health'])[0]
            
            if check_type == 'health':
                # Public health check (no auth required)
                health_data = get_system_health()
                self._send_json_response(200, health_data)
                
            elif check_type == 'metrics':
                # Basic metrics (no auth required, but limited info)
                metrics_data = get_system_metrics()
                self._send_json_response(200, {
                    "success": True,
                    "metrics": metrics_data
                })
                
            elif check_type == 'endpoints':
                # Test other API endpoints
                endpoint_status = test_api_endpoints()
                self._send_json_response(200, {
                    "success": True,
                    "endpoints": endpoint_status,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                
            elif check_type == 'full':
                # Full monitoring report (authentication recommended but not required)
                user_id = self._verify_auth()
                
                health_data = get_system_health()
                metrics_data = get_system_metrics()
                endpoint_status = test_api_endpoints()
                
                self._send_json_response(200, {
                    "success": True,
                    "authenticated": bool(user_id),
                    "health": health_data,
                    "metrics": metrics_data,
                    "endpoints": endpoint_status,
                    "generated_at": datetime.utcnow().isoformat() + "Z"
                })
                
            else:
                # Default: API info
                self._send_json_response(200, {
                    "api": "LifeKB Monitoring",
                    "version": "1.0.0", 
                    "status": "active",
                    "endpoints": {
                        "GET ?type=health": "System health check",
                        "GET ?type=metrics": "Basic system metrics",
                        "GET ?type=endpoints": "API endpoint status",
                        "GET ?type=full": "Complete monitoring report"
                    },
                    "features": [
                        "health_monitoring",
                        "database_status",
                        "api_endpoint_testing",
                        "system_metrics",
                        "environment_validation"
                    ]
                })
                
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}") 